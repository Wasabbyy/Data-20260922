"""Optimalizace osevního plánu: mean-CVaR lineární program.

Proměnné: x_i >= 0 hektary plodiny i.
Účel:     max (1 - lam) * E[zisk] + lam * CVaR_alfa[zisk]
          CVaR_alfa = průměrný zisk v alfa nejhorších procentech scénářů.
Omezení:  sum x = 1000 ha, zelenina <= 200 ha (obojí zadání),
          x_i <= 250 ha (maximální zastoupení jedné plodiny, zmíněné v zadání jako
          příklad realistického omezení).
Doplnění zadání: limit zeleniny je parametr (farmářův hrubý odhad) a lze přidat
          rozpočet sum naklady_i * x_i <= B. Obojí je lineární, úloha zůstává LP.

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


@dataclass
class Reseni:
    x: np.ndarray          # hektary (20,)
    hodnota: float         # (1 - lam) * E + lam * CVaR na optimalizačních scénářích, Kč
    stin_zelenina: float   # o kolik Kč vzroste hodnota, když limit zeleniny povolí o 1 ha
    stin_rozpocet: float   # o kolik Kč vzroste hodnota, když rozpočet povolí o 1 Kč


def min_rozpocet(naklady: np.ndarray, om: Omezeni, max_zelenina: float = MAX_ZELENINA) -> float:
    """Nejlevnější osetí celé rozlohy při daných mezích (Kč)."""
    res = linprog(np.asarray(naklady, float) / 1e6, A_ub=om.zelenina.astype(float)[None, :], b_ub=[max_zelenina],
                  A_eq=np.ones((1, len(om.horni))), b_eq=[ROZLOHA], bounds=[(0, h) for h in om.horni], method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    return float(res.fun) * 1e6


def vyres(marze: np.ndarray, om: Omezeni, lam: float = LAMBDA, alfa: float = ALFA,
          max_zelenina: float = MAX_ZELENINA, naklady: np.ndarray | None = None,
          rozpocet: float | None = None) -> Reseni:
    """marze: K x 20 scénářů marže v Kč/ha. naklady (Kč/ha) a rozpocet (Kč) přidají sum naklady * x <= rozpocet."""
    K, n = marze.shape
    M = marze / 1e6                     # mil. Kč/ha kvůli numerice
    mu = M.mean(axis=0)
    # proměnné: [x (n), eta (1), u (K)]
    c = np.concatenate([-(1 - lam) * mu, [-lam], np.full(K, lam / (alfa * K))])
    # u_k >= eta - M_k x   <=>   -M_k x + eta - u_k <= 0
    scen = sparse.hstack([sparse.csr_matrix(-M), sparse.csr_matrix(np.ones((K, 1))), -sparse.identity(K)])
    radky = [scen, sparse.csr_matrix(np.concatenate([om.zelenina.astype(float), [0.0], np.zeros(K)])[None, :])]
    b_ub = np.append(np.zeros(K), max_zelenina)
    if rozpocet is not None:
        if naklady is None:
            raise ValueError("Rozpočet potřebuje vektor nákladů.")
        naklady = np.asarray(naklady, float)
        minimum = min_rozpocet(naklady, om, max_zelenina)
        if rozpocet < minimum - 1e-6:
            raise ValueError(f"Rozpočet {rozpocet / 1e6:.1f} mil. Kč nestačí na osetí {ROZLOHA:.0f} ha, "
                             f"minimum je {minimum / 1e6:.1f} mil. Kč.")
        radky.append(sparse.csr_matrix(np.concatenate([naklady / 1e6, [0.0], np.zeros(K)])[None, :]))
        b_ub = np.append(b_ub, rozpocet / 1e6)
    A_eq = np.concatenate([np.ones(n), [0.0], np.zeros(K)])[None, :]
    meze = [(0, h) for h in om.horni] + [(None, None)] + [(0, None)] * K
    res = linprog(c, A_ub=sparse.vstack(radky).tocsr(), b_ub=b_ub, A_eq=A_eq, b_eq=[ROZLOHA], bounds=meze, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    x = res.x[:n]
    x[x < 1e-6] = 0.0
    stiny = -res.ineqlin.marginals[K:]   # duály jsou v mil. Kč na jednotku pravé strany
    return Reseni(x=x, hodnota=-res.fun * 1e6, stin_zelenina=float(stiny[0]) * 1e6,
                  stin_rozpocet=float(stiny[1]) if rozpocet is not None else 0.0)


def optimalizuj(marze: np.ndarray, om: Omezeni, lam: float = LAMBDA, alfa: float = ALFA, **omezeni_navic) -> np.ndarray:
    """Jako `vyres`, ale vrací jen hektary x (20,)."""
    return vyres(marze, om, lam=lam, alfa=alfa, **omezeni_navic).x


def minimax_litost(marze_scenaru: list[np.ndarray], om: Omezeni, lam: float = LAMBDA, alfa: float = ALFA,
                   max_zelenina: float = MAX_ZELENINA) -> tuple[np.ndarray, float]:
    """Plán s nejmenší největší lítostí přes několik sad marží (např. scénáře nákladů).

    Lítost ve scénáři s = hodnota plánu optimálního pro s minus hodnota plánu x, obojí
    jako (1 - lam) * E + lam * CVaR. Vrací (x, největší lítost v Kč).
    """
    S = len(marze_scenaru)
    K, n = marze_scenaru[0].shape
    optima = [vyres(M, om, lam=lam, alfa=alfa, max_zelenina=max_zelenina).hodnota / 1e6 for M in marze_scenaru]
    # proměnné: [x (n), r (1), eta (S), u (S*K)]
    N = n + 1 + S + S * K
    radky, b_ub = [], []
    for s, Ms in enumerate(marze_scenaru):
        M = Ms / 1e6
        u_od = n + 1 + S + s * K
        # u_sk >= eta_s - M_sk x
        eta_sl = sparse.csr_matrix((np.ones(K), (np.arange(K), np.full(K, n + 1 + s))), shape=(K, N))
        u_blok = sparse.csr_matrix((-np.ones(K), (np.arange(K), u_od + np.arange(K))), shape=(K, N))
        x_blok = sparse.hstack([sparse.csr_matrix(-M), sparse.csr_matrix((K, N - n))])
        radky.append(x_blok + eta_sl + u_blok)
        b_ub.extend(np.zeros(K))
        # optimum_s - hodnota_s(x) <= r
        lit = np.zeros(N)
        lit[:n] = -(1 - lam) * M.mean(axis=0)
        lit[n] = -1.0
        lit[n + 1 + s] = -lam
        lit[u_od:u_od + K] = lam / (alfa * K)
        radky.append(sparse.csr_matrix(lit[None, :]))
        b_ub.append(-optima[s])
    zel = np.zeros(N)
    zel[:n] = om.zelenina.astype(float)
    radky.append(sparse.csr_matrix(zel[None, :]))
    b_ub.append(max_zelenina)
    # Hlavní cíl je největší lítost r. Malá váha na průměrné hodnotě rozhodne mezi plány se stejným r.
    c = np.zeros(N)
    c[n] = 1.0
    for s, Ms in enumerate(marze_scenaru):
        u_od = n + 1 + S + s * K
        c[:n] -= 1e-3 / S * (1 - lam) * Ms.mean(axis=0) / 1e6
        c[n + 1 + s] -= 1e-3 / S * lam
        c[u_od:u_od + K] += 1e-3 / S * lam / (alfa * K)
    A_eq = np.zeros((1, N))
    A_eq[0, :n] = 1.0
    meze = [(0, h) for h in om.horni] + [(0, None)] + [(None, None)] * S + [(0, None)] * (S * K)
    res = linprog(c, A_ub=sparse.vstack(radky).tocsr(), b_ub=np.array(b_ub), A_eq=A_eq, b_eq=[ROZLOHA],
                  bounds=meze, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    x = res.x[:n]
    x[x < 1e-6] = 0.0
    return x, float(res.x[n]) * 1e6


def hodnota(zisky: np.ndarray, lam: float = LAMBDA, alfa: float = ALFA) -> float:
    """(1 - lam) * E + lam * CVaR pro vektor zisků farmy (Kč). Stejná míra jako účel LP."""
    return float((1 - lam) * zisky.mean() + lam * _prumer_nejhorsich(zisky, alfa))


def _prumer_nejhorsich(zisky: np.ndarray, alfa: float) -> float:
    """Průměr přesně alfa * K nejhorších scénářů (CVaR jako v LP).

    Maska `zisky <= kvantil` by při shodách na hranici přibrala různý počet scénářů podle
    zaokrouhlení. Shody vznikají v optimu LP (víc scénářů má zisk rovný eta) a u bootstrapu
    bez vyhlazení, kde se opakuje jen 22 historických ročníků.
    """
    return float(np.sort(zisky)[:max(int(round(alfa * len(zisky))), 1)].mean())


def rizikove_ukazatele(zisky: np.ndarray, alfa: float = ALFA) -> dict:
    """Souhrn rozdělení zisku celé farmy (Kč)."""
    return {
        "ocekavany_zisk": float(zisky.mean()),
        "median": float(np.median(zisky)),
        "smer_odchylka": float(zisky.std()),
        "semismer_odchylka": float(np.sqrt(np.mean(np.minimum(zisky - zisky.mean(), 0) ** 2))),
        f"VaR{int(alfa*100)}": float(np.quantile(zisky, alfa)),
        f"CVaR{int(alfa*100)}": _prumer_nejhorsich(zisky, alfa),
        "p_ztraty": float(np.mean(zisky < 0)),
    }
