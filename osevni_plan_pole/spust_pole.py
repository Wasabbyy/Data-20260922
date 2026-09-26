"""Samostatná analýza osevního plánu s dělením na menší pole.

Spuštění z kořene repozitáře:
    python osevni_plan_pole/spust_pole.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "osevni_plan"
sys.path.insert(0, str(PLAN))

import numpy as np
import pandas as pd

import backtest as bt
import data as dt
import modely as md
import optimalizace as op
import spust as pu
from optimalizace_pole import optimalizuj

OUT = Path(__file__).resolve().parent / "vystupy_pole"
DET = OUT / "detaily"
OUT.mkdir(parents=True, exist_ok=True)
DET.mkdir(parents=True, exist_ok=True)


def main():
    data = dt.nacti()
    kontext = md.Kontext.z_dat(data)
    btc = bt.predikce_backtest(kontext, md.MODELY_CEN, "cena")
    bty = bt.predikce_backtest(kontext, md.MODELY_VYNOSU, "vynos")
    model_cen = bt.vyber_modelu(btc, dt.POSLEDNI_ROK)
    model_vynosu = bt.vyber_modelu(bty, dt.POSLEDNI_ROK)
    bod_lp, bod_ly, ec, ey = pu.podklady_2025(kontext, btc, bty, model_cen, model_vynosu)
    naklady = data.naklady_2024 * (1 + data.makro.loc[dt.POSLEDNI_ROK, "inflace"] / 100)
    m_opt = pu.scenare_marzi(bod_lp, bod_ly, ec, ey, naklady, np.random.default_rng(pu.SEED))[2]
    m_test = pu.scenare_marzi(bod_lp, bod_ly, ec, ey, naklady, np.random.default_rng(pu.SEED + 1))[2]

    om = op.omezeni(data.zelenina)
    plany, rizika, detaily = {}, {}, []
    for lam in pu.LAMBDY:
        x, pole = optimalizuj(m_opt, om, lam=lam)
        plany[lam] = x
        rizika[lam] = op.rizikove_ukazatele(m_test @ x)
        pole.insert(0, "lambda", lam)
        detaily.append(pole)

    plan = pd.DataFrame(plany, index=pd.Index([dt.NAZVY[kod] for kod in dt.KODY], name="plodina"))
    plan.columns = [f"lambda_{lam}" for lam in pu.LAMBDY]
    plan.round(1).to_csv(OUT / "plan_pole_2025.csv")
    pd.concat(detaily, ignore_index=True).round(2).to_csv(DET / "plan_pole_2025_detail.csv", index=False)
    pd.DataFrame(rizika).T.to_csv(DET / "riziko_pole_2025.csv")
    print(plan.round(1))
    print(pd.DataFrame(rizika).T.round(0))


if __name__ == "__main__":
    main()
