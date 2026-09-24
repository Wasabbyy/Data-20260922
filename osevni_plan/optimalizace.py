"""Optimalizace osevního plánu: mean-CVaR lineární program.

Proměnné: x_i >= 0 hektary plodiny i.
Účel:     max (1 - lam) * E[zisk] + lam * CVaR_alfa[zisk]
          CVaR_alfa = průměrný zisk v alfa nejhorších procentech scénářů.
Omezení:  sum x = 1000 ha, zelenina <= 200 ha (obojí zadání),
          x_i <= 250 ha (maximální zastoupení jedné plodiny, zmíněné v zadání jako
          příklad realistického omezení).

CVaR jako LP (Rockafellar & Uryasev 2000):
  CVaR_alfa = max_eta  eta - 1/(alfa*K) * sum_k max(eta - zisk_k, 0)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

from data import KODY

ROZLOHA = 1000.0
MAX_ZELENINA = 0.20 * ROZLOHA
MAX_PLODINA = 0.25 * ROZLOHA
ALFA = 0.10           # CVaR přes 10 % nejhorších scénářů
LAMBDA = 0.5          # váha rizika v doporučeném plánu


@dataclass
class Omezeni:
    horni: np.ndarray     # horní mez hektarů pro každou plodinu
    zelenina: np.ndarray  # bool maska


def omezeni(zelenina: pd.Series) -> Omezeni:
    return Omezeni(horni=np.full(len(KODY), MAX_PLODINA), zelenina=zelenina.reindex(KODY).to_numpy(bool))


def optimalizuj(marze: np.ndarray, om: Omezeni, lam: float = LAMBDA, alfa: float = ALFA) -> np.ndarray:
    """marze: K x 20 scénářů marže v Kč/ha. Vrací hektary x (20,)."""
    K, n = marze.shape
    M = marze / 1e6                     # mil. Kč/ha kvůli numerice
    mu = M.mean(axis=0)
    # proměnné: [x (n), eta (1), u (K)]
    c = np.concatenate([-(1 - lam) * mu, [-lam], np.full(K, lam / (alfa * K))])
    # u_k >= eta - M_k x   <=>   -M_k x + eta - u_k <= 0
    scen = sparse.hstack([sparse.csr_matrix(-M), sparse.csr_matrix(np.ones((K, 1))), -sparse.identity(K)])
    zel = sparse.csr_matrix(np.concatenate([om.zelenina.astype(float), [0.0], np.zeros(K)])[None, :])
    A_ub = sparse.vstack([scen, zel]).tocsr()
    b_ub = np.append(np.zeros(K), MAX_ZELENINA)
    A_eq = np.concatenate([np.ones(n), [0.0], np.zeros(K)])[None, :]
    meze = [(0, h) for h in om.horni] + [(None, None)] + [(0, None)] * K
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[ROZLOHA], bounds=meze, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    x = res.x[:n]
    x[x < 1e-6] = 0.0
    return x


def rizikove_ukazatele(zisky: np.ndarray, alfa: float = ALFA) -> dict:
    """Souhrn rozdělení zisku celé farmy (Kč)."""
    q = np.quantile(zisky, alfa)
    return {
        "ocekavany_zisk": float(zisky.mean()),
        "median": float(np.median(zisky)),
        "smer_odchylka": float(zisky.std()),
        "semismer_odchylka": float(np.sqrt(np.mean(np.minimum(zisky - zisky.mean(), 0) ** 2))),
        f"VaR{int(alfa*100)}": float(q),
        f"CVaR{int(alfa*100)}": float(zisky[zisky <= q].mean()),
        "p_ztraty": float(np.mean(zisky < 0)),
    }
