"""Samostatná analýza osevního plánu s dělením na menší pole.

Spuštění z kořene repozitáře:
    python osevni_plan_pole/spust_pole.py
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "osevni_plan"
sys.path.insert(0, str(PLAN))

import numpy as np
import pandas as pd
import scipy
import statsmodels

import backtest as bt  # type: ignore[reportMissingImports]
import data as dt  # type: ignore[reportMissingImports]
import modely as md  # type: ignore[reportMissingImports]
import optimalizace as op  # type: ignore[reportMissingImports]
import spust as pu  # type: ignore[reportMissingImports]
import optimalizace_pole as opp
from optimalizace_pole import optimalizuj

OUT = Path(__file__).resolve().parent / "vystupy_pole"
DET = OUT / "detaily"
OUT.mkdir(parents=True, exist_ok=True)
DET.mkdir(parents=True, exist_ok=True)


def over_vysledek(x, pole, om, max_plocha, mez):
    """Ověří, že agregovaný plán odpovídá rozpisu polí a splňuje omezení."""
    plocha_podle_plodiny = pole.groupby("kod")["ha"].sum().reindex(dt.KODY, fill_value=0).to_numpy()
    if not np.allclose(x, plocha_podle_plodiny, atol=1e-5):
        raise RuntimeError("Rozpis polí nesouhlasí s agregovanou plochou plodin.")
    if x.sum() + mez * len(pole) > op.ROZLOHA + 1e-5:
        raise RuntimeError("Fyzická plocha včetně mezí překračuje rozlohu farmy.")
    if x[om.zelenina].sum() > op.MAX_ZELENINA + 1e-5 or np.any(x > om.horni + 1e-5):
        raise RuntimeError("Plán porušuje limit zeleniny nebo maximální plochu plodiny.")
    if not pole.empty and (pole["ha"].max() > max_plocha + 1e-5 or not pole["pole"].is_unique):
        raise RuntimeError("Rozpis obsahuje neplatnou plochu nebo duplicitní pole.")


def main():
    data = dt.nacti()
    kontext = md.Kontext.z_dat(data)
    btc = bt.predikce_backtest(kontext, md.MODELY_CEN, "cena")
    bty = bt.predikce_backtest(kontext, md.MODELY_VYNOSU, "vynos")
    model_cen = bt.vyber_modelu(btc, dt.POSLEDNI_ROK)
    model_vynosu = bt.vyber_modelu(bty, dt.POSLEDNI_ROK)
    mc, my = bt.vyhodnot(btc), bt.vyhodnot(bty)
    bt.souhrn(mc, "naivni").round(4).to_csv(DET / "backtest_ceny_souhrn.csv")
    bt.souhrn(my, "naivni").round(4).to_csv(DET / "backtest_vynosy_souhrn.csv")
    dm = {
        "vynosy_kombinace_vs_naivni_crps": bt.diebold_mariano(my, "kombinace", "naivni"),
        "vynosy_kombinace_vs_prumer3_crps": bt.diebold_mariano(my, "kombinace", "prumer3"),
        "vynosy_kombinace_vs_prumer3_mae": bt.diebold_mariano(my, "kombinace", "prumer3", "abs_chyba"),
        "vynosy_arima_vs_naivni_crps": bt.diebold_mariano(my, "arima", "naivni"),
    }
    (DET / "testy_diebold_mariano.json").write_text(
        json.dumps(dm, ensure_ascii=False, indent=2), encoding="utf-8")
    chyby_cen = bt.matice_chyb(btc, model_cen)
    chyby_vynosu = bt.matice_chyb(bty, model_vynosu)
    pd.DataFrame({
        "kod": dt.KODY,
        "plodina": [dt.NAZVY[kod] for kod in dt.KODY],
        "korelace_chyb_cena_vynos": [chyby_cen[kod].corr(chyby_vynosu[kod]) for kod in dt.KODY],
    }).to_csv(DET / "vztah_chyb_cena_vynos.csv", index=False)
    bod_lp, bod_ly, ec, ey = pu.podklady_2025(kontext, btc, bty, model_cen, model_vynosu)
    inflace = float(data.makro.loc[dt.POSLEDNI_ROK, "inflace"])
    naklady = data.naklady_2024 * (1 + inflace / 100)
    m_opt = pu.scenare_marzi(bod_lp, bod_ly, ec, ey, naklady, np.random.default_rng(pu.SEED))[2]
    m_test = pu.scenare_marzi(bod_lp, bod_ly, ec, ey, naklady, np.random.default_rng(pu.SEED + 1))[2]

    om = op.omezeni(data.zelenina)
    plany, rizika, detaily = {}, {}, []
    for lam in pu.LAMBDY:
        x, pole = optimalizuj(m_opt, om, lam=lam)
        over_vysledek(x, pole, om, opp.MAX_PLOCHA_POLE, opp.MEZ_POLE)
        plany[lam] = x
        rizika[lam] = op.rizikove_ukazatele(m_test @ x)
        pole.insert(0, "lambda", lam)
        detaily.append(pole)

    lam_test = op.LAMBDA
    citlivost = []
    rozpis_citlivosti = []
    for max_plocha, mez in ((20.0, 2.0), (30.0, 1.0), (30.0, 2.0), (40.0, 2.0)):
        if (max_plocha, mez) == (opp.MAX_PLOCHA_POLE, opp.MEZ_POLE):
            x = plany[lam_test]
            pole = next(tab.drop(columns="lambda") for tab in detaily if (tab["lambda"] == lam_test).any())
        else:
            x, pole = optimalizuj(
                m_opt, om, lam=lam_test, max_plocha_pole=max_plocha, mez_pole=mez)
        over_vysledek(x, pole, om, max_plocha, mez)
        riziko = op.rizikove_ukazatele(m_test @ x)
        citlivost.append({
            "max_ha_pole": max_plocha,
            "mez_ha_pole": mez,
            "pocet_poli": len(pole),
            "produkce_ha": float(x.sum()),
            "fyzicka_plocha_ha": float(x.sum() + mez * len(pole)),
            **riziko,
        })
        rozpis = pd.DataFrame({"kod": dt.KODY, "plodina": [dt.NAZVY[kod] for kod in dt.KODY], "ha": x})
        rozpis.insert(0, "mez_ha_pole", mez)
        rozpis.insert(0, "max_ha_pole", max_plocha)
        rozpis_citlivosti.append(rozpis)

    plan = pd.DataFrame(plany, index=pd.Index([dt.NAZVY[kod] for kod in dt.KODY], name="plodina"))
    plan.columns = [f"lambda_{lam}" for lam in pu.LAMBDY]
    plan.round(1).to_csv(OUT / "plan_pole_2025.csv")
    pd.concat(detaily, ignore_index=True).round(2).to_csv(DET / "plan_pole_2025_detail.csv", index=False)
    pd.DataFrame(rizika).T.to_csv(DET / "riziko_pole_2025.csv")
    pd.DataFrame(citlivost).round(3).to_csv(DET / "citlivost_predpokladu_pole.csv", index=False)
    pd.concat(rozpis_citlivosti, ignore_index=True).round(2).to_csv(
        DET / "citlivost_plodiny_pole.csv", index=False)
    manifest = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "statsmodels": statsmodels.__version__,
        "posledni_rok_dat": int(dt.POSLEDNI_ROK),
        "model_cen": model_cen,
        "model_vynosu": model_vynosu,
        "pocet_scenaru_optimalizace": int(pu.N_SCENARU),
        "pocet_scenaru_testu": int(pu.N_SCENARU),
        "seed_optimalizace": int(pu.SEED),
        "seed_testu": int(pu.SEED + 1),
        "lambda": [float(lam) for lam in pu.LAMBDY],
        "zakladni_max_ha_pole": opp.MAX_PLOCHA_POLE,
        "zakladni_mez_ha_pole": opp.MEZ_POLE,
        "citlivost_scenare": [[20, 2], [30, 1], [30, 2], [40, 2]],
    }
    (OUT / "metodika_behu.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(plan.round(1))
    print(pd.DataFrame(rizika).T.round(0))
if __name__ == "__main__":
    main()
