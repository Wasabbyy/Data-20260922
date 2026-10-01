"""Doplnění zadání: nejisté náklady, nejistý limit zeleniny a nejistý rozpočet.

Ceny a výnosy se nemění. Pracuje se se stejnými scénáři tržeb jako hlavní plán,
takže každý rozdíl mezi plány jde jen za změněný parametr.

Náklady:  C_i(k) = náklady_2025_i * k, kde k je násobek vůči základu
          (základ = náklady 2024 * (1 + inflace 2024)). Násobek může být jiný pro
          polní plodiny a pro zeleninu.
Růst:     k_rok = (1 + inflace_rok) / (1 + inflace_2024). Náklady rostou jako
          v daném historickém roce, ceny plodin zůstávají podle modelu.
Lítost:   hodnota plánu optimálního pro daný scénář minus hodnota posuzovaného
          plánu, obojí (1 - lam) * E + lam * CVaR na testovacích scénářích.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import data as dt
import optimalizace as op

ROKY_RUSTU = [2008, 2023, 2022]                           # roky s nejvyšší inflací od roku 2000
ROK_REZERVY = 2022                                        # rozpočet s rezervou se počítá při růstu nákladů jako v tomto roce
K_CITLIVOST = [round(0.80 + 0.05 * i, 2) for i in range(13)]   # 0,80 až 1,40
K_MRIZKA = [round(0.8 + 0.1 * i, 1) for i in range(6)]         # 0,8 až 1,3
LIMITY_ZELENINY = [0, 50, 100, 150, 200, 250, 300, 350, 400]   # ha
ROZPOCTY_MIL = [25, 30, 40, 50, 60, 80, 100, 120, 140, 160, 180]
LIMITY_PRO_ROZPOCET = [100, 200, 300]
LIMITY_PRO_DOPORUCENI = [100, 150, 200, 250, 300]             # ha, limit zeleniny je odhad na obě strany


@dataclass(frozen=True)
class ScenarNakladu:
    nazev: str
    k_pole: float
    k_zelenina: float


def cz(x: float, mista: int = 1) -> str:
    return f"{x:.{mista}f}".replace(".", ",")


def nasobek_rustu(makro: pd.DataFrame, rok: int) -> float:
    """O kolik jsou náklady vyšší než v základu, když porostou jako v roce `rok`."""
    return float((1 + makro.loc[rok, "inflace"] / 100) / (1 + makro.loc[dt.POSLEDNI_ROK, "inflace"] / 100))


def scenare_rustu(makro: pd.DataFrame) -> list[ScenarNakladu]:
    zaklad = makro.loc[dt.POSLEDNI_ROK, "inflace"]
    out = [ScenarNakladu(f"základ (růst {cz(zaklad)} %)", 1.0, 1.0)]
    for rok in ROKY_RUSTU:
        k = nasobek_rustu(makro, rok)
        out.append(ScenarNakladu(f"růst jako {rok} ({cz(makro.loc[rok, 'inflace'])} %)", k, k))
    return out


def naklady_scenare(naklady: np.ndarray, zelenina: np.ndarray, sc: ScenarNakladu) -> np.ndarray:
    return naklady * np.where(zelenina, sc.k_zelenina, sc.k_pole)


def ukazatele(x: np.ndarray, trzby: np.ndarray, naklady: np.ndarray) -> dict:
    """Zisk plánu x na scénářích tržeb při daných nákladech (vše Kč)."""
    zisky = trzby @ x - naklady @ x
    r = op.rizikove_ukazatele(zisky)
    return {"E": r["ocekavany_zisk"], "CVaR": r["CVaR10"], "p_ztraty": r["p_ztraty"],
            "hodnota": op.hodnota(zisky), "naklady": float(naklady @ x)}


def spolecne_ha(x: np.ndarray, y: np.ndarray) -> float:
    """Kolik hektarů mají dva plány oseto stejnou plodinou."""
    return float(np.minimum(x, y).sum())


def tabulka_planu(plany: dict, nazvy: list[str]) -> pd.DataFrame:
    tab = pd.DataFrame(plany, index=pd.Index(nazvy, name="plodina")).round(1)
    return tab[(tab > 0.05).any(axis=1)]


# --------------------------------------------------------------------------
def bod_zvratu(trzby: np.ndarray, naklady: np.ndarray, x_zaklad: np.ndarray, nazvy: list[str]) -> pd.DataFrame:
    """Násobek nákladů, při kterém je průměrná (mediánová) marže plodiny nulová: tržba / náklady."""
    return pd.DataFrame({
        "naklady_kc_ha": naklady,
        "trzba_prumer_kc_ha": trzby.mean(axis=0),
        "k_nulova_prumerna_marze": trzby.mean(axis=0) / naklady,
        "k_nulova_medianova_marze": np.median(trzby, axis=0) / naklady,
        "ha_v_planu": x_zaklad,
    }, index=pd.Index(nazvy, name="plodina"))


def krok_doporuceni(T_opt, T_test, C, om, scenare, k_rezerva, nazvy):
    """Plán s nejmenší největší lítostí přes scénáře růstu nákladů, pro několik limitů zeleniny."""
    marze = [T_opt - naklady_scenare(C, om.zelenina, s) for s in scenare]
    C_nejhorsi = naklady_scenare(C, om.zelenina, scenare[-1])
    radky, plany = [], {}
    for limit in LIMITY_PRO_DOPORUCENI:
        x, _ = op.minimax_litost(marze, om, max_zelenina=limit)
        plany[f"{limit} ha"] = x
        u, u_n = ukazatele(x, T_test, C), ukazatele(x, T_test, C_nejhorsi)
        litosti = []
        for s, M in zip(scenare, marze):
            Ck = naklady_scenare(C, om.zelenina, s)
            x_s = op.optimalizuj(M, om, max_zelenina=limit)
            litosti.append(ukazatele(x_s, T_test, Ck)["hodnota"] - ukazatele(x, T_test, Ck)["hodnota"])
        radky.append({"limit_ha": limit, "ha_zelenina": float(x[om.zelenina].sum()),
                      "naklady_planu": u["naklady"], "naklady_s_rezervou": k_rezerva * u["naklady"],
                      "zaklad_E": u["E"], "zaklad_CVaR": u["CVaR"], "zaklad_p_ztraty": u["p_ztraty"],
                      "nejvyssi_rust_E": u_n["E"], "nejvyssi_rust_CVaR": u_n["CVaR"], "nejvyssi_rust_p_ztraty": u_n["p_ztraty"],
                      "nejvetsi_litost": max(litosti)})
    return pd.DataFrame(radky).set_index("limit_ha"), tabulka_planu(plany, nazvy), plany[f"{int(op.MAX_ZELENINA)} ha"]


def krok_scenare(T_opt, T_test, C, om, x_zaklad, x_rob, scenare, nazvy):
    """Plán přepočítaný pro každý scénář nákladů, původní plán a plán s nejmenší největší lítostí."""
    radky, plany = [], {"původní plán": x_zaklad}
    for s in scenare:
        Ck = naklady_scenare(C, om.zelenina, s)
        x_s = op.optimalizuj(T_opt - Ck, om)
        plany[s.nazev] = x_s
        u_s, u_z, u_r = (ukazatele(x, T_test, Ck) for x in (x_s, x_zaklad, x_rob))
        radky.append({
            "scenar": s.nazev, "k": s.k_pole,
            "puvodni_E": u_z["E"], "puvodni_CVaR": u_z["CVaR"], "puvodni_p_ztraty": u_z["p_ztraty"],
            "puvodni_litost": u_s["hodnota"] - u_z["hodnota"],
            "prepocitany_E": u_s["E"], "prepocitany_CVaR": u_s["CVaR"], "prepocitany_p_ztraty": u_s["p_ztraty"],
            "spolecne_ha_s_puvodnim": spolecne_ha(x_s, x_zaklad),
            "robustni_E": u_r["E"], "robustni_CVaR": u_r["CVaR"], "robustni_p_ztraty": u_r["p_ztraty"],
            "robustni_litost": u_s["hodnota"] - u_r["hodnota"],
        })
    plany["robustní (minimax lítost)"] = x_rob
    return pd.DataFrame(radky).set_index("scenar"), tabulka_planu(plany, nazvy)


def krok_citlivost(T_opt, T_test, C, om, x_zaklad, x_rob, nazvy):
    """Stejný násobek k pro všechny plodiny, od levnějších po dražší náklady."""
    radky, plany = [], {}
    for k in K_CITLIVOST:
        x = op.optimalizuj(T_opt - k * C, om)
        plany[f"k = {cz(k, 2)}"] = x
        u, u_z, u_r = (ukazatele(y, T_test, k * C) for y in (x, x_zaklad, x_rob))
        radky.append({
            "k": k, "prepocitany_E": u["E"], "prepocitany_CVaR": u["CVaR"], "prepocitany_p_ztraty": u["p_ztraty"],
            "puvodni_E": u_z["E"], "puvodni_CVaR": u_z["CVaR"], "puvodni_p_ztraty": u_z["p_ztraty"],
            "puvodni_litost": u["hodnota"] - u_z["hodnota"], "robustni_litost": u["hodnota"] - u_r["hodnota"],
            "spolecne_ha_s_puvodnim": spolecne_ha(x, x_zaklad), "ha_zelenina": float(x[om.zelenina].sum()),
        })
    return pd.DataFrame(radky).set_index("k"), tabulka_planu(plany, nazvy)


def krok_mrizka(T_opt, C, om, x_zaklad):
    """Zvlášť násobek pro polní plodiny a pro zeleninu: čí odhad nákladů plánem hýbe víc."""
    radky = []
    for kp in K_MRIZKA:
        for kz in K_MRIZKA:
            x = op.optimalizuj(T_opt - naklady_scenare(C, om.zelenina, ScenarNakladu("", kp, kz)), om)
            radky.append({"k_pole": kp, "k_zelenina": kz, "ha_zelenina": float(x[om.zelenina].sum()),
                          "spolecne_ha_s_puvodnim": spolecne_ha(x, x_zaklad)})
    return pd.DataFrame(radky)


def krok_limit_zeleniny(T_opt, T_test, C, om, x_zaklad, nazvy):
    radky, plany = [], {}
    for limit in LIMITY_ZELENINY:
        r = op.vyres(T_opt - C, om, max_zelenina=limit)
        plany[f"{limit} ha"] = r.x
        u = ukazatele(r.x, T_test, C)
        radky.append({"limit_ha": limit, "ha_zelenina": float(r.x[om.zelenina].sum()), "E": u["E"], "CVaR": u["CVaR"],
                      "p_ztraty": u["p_ztraty"], "hodnota": u["hodnota"], "naklady_planu": u["naklady"],
                      "stin_kc_za_ha": r.stin_zelenina, "spolecne_ha_s_puvodnim": spolecne_ha(r.x, x_zaklad)})
    return pd.DataFrame(radky).set_index("limit_ha"), tabulka_planu(plany, nazvy)


def krok_rozpocet(T_opt, T_test, C, om, x_zaklad, k_rezerva, nazvy):
    """Plán podle výše rozpočtu. Varianta s rezervou hlídá rozpočet při nákladech k_rezerva * C."""
    hodnota_bez = ukazatele(x_zaklad, T_test, C)["hodnota"]
    radky, plany = [], {}
    for varianta, k_b in [("základní náklady", 1.0), ("s rezervou", k_rezerva)]:
        for B in ROZPOCTY_MIL:
            radek = {"varianta": varianta, "k_rozpoctu": k_b, "rozpocet_mil": B}
            try:
                r = op.vyres(T_opt - C, om, naklady=k_b * C, rozpocet=B * 1e6)
            except ValueError:
                radky.append(radek | {"pripustne": False})
                continue
            u = ukazatele(r.x, T_test, C)
            if varianta == "základní náklady":
                plany[f"{B} mil. Kč"] = r.x
            radky.append(radek | {
                "pripustne": True, "ha_zelenina": float(r.x[om.zelenina].sum()), "E": u["E"], "CVaR": u["CVaR"],
                "p_ztraty": u["p_ztraty"], "naklady_planu": u["naklady"], "naklady_pri_k_rozpoctu": k_b * u["naklady"],
                "cena_opatrnosti": hodnota_bez - u["hodnota"], "stin_kc_za_kc": r.stin_rozpocet,
                "spolecne_ha_s_puvodnim": spolecne_ha(r.x, x_zaklad)})
    return pd.DataFrame(radky), tabulka_planu(plany, nazvy)


def krok_rozpocet_x_zelenina(T_opt, T_test, C, om, x_zaklad):
    """Oba nejisté parametry najednou: které z omezení plán skutečně drží."""
    radky = []
    for limit in LIMITY_PRO_ROZPOCET:
        for B in ROZPOCTY_MIL + [None]:
            r = op.vyres(T_opt - C, om, max_zelenina=limit, naklady=C, rozpocet=None if B is None else B * 1e6)
            u = ukazatele(r.x, T_test, C)
            radky.append({"limit_zeleniny_ha": limit, "rozpocet_mil": "bez limitu" if B is None else B,
                          "ha_zelenina": float(r.x[om.zelenina].sum()), "E": u["E"], "CVaR": u["CVaR"],
                          "p_ztraty": u["p_ztraty"], "naklady_planu": u["naklady"],
                          "stin_zelenina_kc_za_ha": r.stin_zelenina, "stin_rozpocet_kc_za_kc": r.stin_rozpocet,
                          "spolecne_ha_s_puvodnim": spolecne_ha(r.x, x_zaklad)})
    return pd.DataFrame(radky)


def jadro(rodiny: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Nejmenší plocha plodiny napříč plány v každé rodině. Kladné číslo = plodina je v plánu vždy."""
    tab = pd.DataFrame({nazev: plany.min(axis=1) for nazev, plany in rodiny.items()}).fillna(0.0)
    return tab[(tab > 0.05).any(axis=1)].round(1)


# --------------------------------------------------------------------------
def spust(data: dt.Data, T_opt: np.ndarray, T_test: np.ndarray, naklady_2025: pd.Series, x_zaklad: np.ndarray, out: Path) -> dict:
    """Všechny kroky doplnění. Zapíše CSV do `out`, vrátí tabulky pro grafy a souhrn pro vysledky.json."""
    nazvy = [dt.NAZVY[k] for k in dt.KODY]
    om = op.omezeni(data.zelenina)
    C = naklady_2025.to_numpy(float)
    scenare = scenare_rustu(data.makro)
    k_rezerva = nasobek_rustu(data.makro, ROK_REZERVY)

    zvrat = bod_zvratu(T_opt, C, x_zaklad, nazvy)       # stejná sada scénářů jako predikce_2025.csv
    k_plan = float((T_test.mean(axis=0) @ x_zaklad) / (C @ x_zaklad))
    dop, dop_plany, x_rob = krok_doporuceni(T_opt, T_test, C, om, scenare, k_rezerva, nazvy)
    sc, sc_plany = krok_scenare(T_opt, T_test, C, om, x_zaklad, x_rob, scenare, nazvy)
    cit, cit_plany = krok_citlivost(T_opt, T_test, C, om, x_zaklad, x_rob, nazvy)
    mrizka = krok_mrizka(T_opt, C, om, x_zaklad)
    lim, lim_plany = krok_limit_zeleniny(T_opt, T_test, C, om, x_zaklad, nazvy)
    roz, roz_plany = krok_rozpocet(T_opt, T_test, C, om, x_zaklad, k_rezerva, nazvy)
    roz_zel = krok_rozpocet_x_zelenina(T_opt, T_test, C, om, x_zaklad)
    jadro_tab = jadro({
        "scenare_rustu_nakladu": sc_plany.drop(columns=["robustní (minimax lítost)"]),
        "naklady_k_0.80_az_1.40": cit_plany, "limit_zeleniny_0_az_400_ha": lim_plany,
        f"rozpocet_{ROZPOCTY_MIL[0]}_az_{ROZPOCTY_MIL[-1]}_mil": roz_plany,
    })

    dop.round(3).to_csv(out / "doporuceny_plan_podle_limitu_zeleniny.csv")
    dop_plany.to_csv(out / "doporuceny_plan_podle_limitu_zeleniny_plany.csv")
    zvrat.round(3).to_csv(out / "naklady_bod_zvratu.csv")
    sc.round(3).to_csv(out / "naklady_scenare.csv")
    sc_plany.to_csv(out / "naklady_scenare_plany.csv")
    cit.round(3).to_csv(out / "naklady_citlivost.csv")
    cit_plany.to_csv(out / "naklady_citlivost_plany.csv")
    mrizka.round(1).to_csv(out / "naklady_mrizka_pole_zelenina.csv", index=False)
    lim.round(3).to_csv(out / "limit_zeleniny.csv")
    lim_plany.to_csv(out / "limit_zeleniny_plany.csv")
    roz.round(4).to_csv(out / "rozpocet.csv", index=False)
    roz_plany.to_csv(out / "rozpocet_plany.csv")
    roz_zel.round(4).to_csv(out / "rozpocet_x_zelenina.csv", index=False)
    jadro_tab.to_csv(out / "stabilita_jadro.csv")

    zel = om.zelenina
    souhrn = {
        "nasobky_rustu": {s.nazev: round(s.k_pole, 4) for s in scenare},
        "k_nulovy_ocekavany_zisk_planu": round(k_plan, 4),
        "trzba_planu_prumer": float(T_test.mean(axis=0) @ x_zaklad),
        "naklady_planu": float(C @ x_zaklad),
        "naklady_planu_zelenina": float(C[zel] @ x_zaklad[zel]),
        "naklady_planu_pole": float(C[~zel] @ x_zaklad[~zel]),
        "min_rozpocet": op.min_rozpocet(C, om),
        "k_rezerva": round(k_rezerva, 4),
        "naklady_robustniho_planu": float(C @ x_rob),
        "doporuceny_plan": {n: round(float(h), 1) for n, h in zip(nazvy, x_rob) if h > 0.05},
        "doporuceni_podle_limitu": dop.round(3).to_dict(orient="index"),
        "scenare": sc.round(3).to_dict(orient="index"),
        "limit_zeleniny": lim.round(3).to_dict(orient="index"),
        "rozpocet": roz.round(4).to_dict(orient="records"),
    }
    tabulky = {"zvrat": zvrat, "scenare": sc, "scenare_plany": sc_plany, "citlivost": cit, "citlivost_plany": cit_plany,
               "mrizka": mrizka, "limit": lim, "limit_plany": lim_plany, "rozpocet": roz, "rozpocet_plany": roz_plany,
               "rozpocet_x_zelenina": roz_zel, "jadro": jadro_tab, "doporuceni": dop, "doporuceni_plany": dop_plany}
    return {"souhrn": souhrn, "tabulky": tabulky}
