"""Samostatná optimalizace osevního plánu s dělením farmy na menší pole."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from data import KODY
from optimalizace import ALFA, LAMBDA, MAX_ZELENINA, Omezeni, ROZLOHA

MAX_PLOCHA_POLE = 30.0
MEZ_POLE = 2.0


def optimalizuj(
    marze: np.ndarray,
    om: Omezeni,
    lam: float = LAMBDA,
    alfa: float = ALFA,
    max_plocha_pole: float = MAX_PLOCHA_POLE,
    mez_pole: float = MEZ_POLE,
):
    """Vrací agregované hektary a detail polí pro samostatnou pole-analýzu."""
    scenaru, n = marze.shape
    M = marze / 1e6
    mu = M.mean(axis=0)
    scen = sparse.hstack([
        sparse.csr_matrix(-M), sparse.csr_matrix((scenaru, n)),
        sparse.csr_matrix(np.ones((scenaru, 1))), -sparse.identity(scenaru),
    ])
    zelenina = sparse.hstack([
        sparse.csr_matrix(om.zelenina.astype(float)[None, :]),
        sparse.csr_matrix((1, n + 1 + scenaru)),
    ])
    fyzicka = sparse.hstack([
        sparse.csr_matrix(np.ones((1, n))), sparse.csr_matrix(np.full((1, n), mez_pole)),
        sparse.csr_matrix((1, 1 + scenaru)),
    ])
    vazba = sparse.hstack([
        sparse.identity(n), -max_plocha_pole * sparse.identity(n),
        sparse.csr_matrix((n, 1 + scenaru)),
    ])
    A = sparse.vstack([scen, zelenina, fyzicka, vazba]).tocsr()
    lower = np.concatenate([np.full(scenaru, -np.inf), [-np.inf, -np.inf], np.full(n, -np.inf)])
    upper = np.concatenate([np.zeros(scenaru), [MAX_ZELENINA, ROZLOHA], np.zeros(n)])

    c = np.zeros(2 * n + 1 + scenaru)
    c[:n] = -(1 - lam) * mu
    c[2 * n] = -lam
    c[2 * n + 1:] = lam / (alfa * scenaru)
    integrality = np.concatenate([np.zeros(n), np.ones(n), np.zeros(1 + scenaru)])
    lower_bounds = np.zeros(len(c))
    upper_bounds = np.concatenate([
        om.horni, np.full(n, ROZLOHA / mez_pole), [np.inf], np.full(scenaru, np.inf),
    ])
    res = milp(
        c,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(A, lower, upper),
        options={"time_limit": 120},
    )
    if not res.success:
        raise RuntimeError(res.message)

    x = res.x[:n]
    pocet_poli = np.rint(res.x[n:2 * n]).astype(int)
    x[x < 1e-6] = 0.0
    radky = []
    globalni_pole = 0
    for i, kod in enumerate(KODY):
        zbyva = x[i]
        for poradi in range(pocet_poli[i]):
            plocha = min(max_plocha_pole, zbyva)
            if plocha > 1e-6:
                globalni_pole += 1
                radky.append({
                    "pole": globalni_pole,
                    "kod": kod,
                    "poradi_plodiny": poradi + 1,
                    "ha": plocha,
                    "mez_ha": mez_pole,
                    "fyzicka_ha": plocha + mez_pole,
                })
            zbyva -= plocha
    return x, pd.DataFrame(radky)
