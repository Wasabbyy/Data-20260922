"""Celý řetězec: marže 2024 -> backtest modelů -> scénáře 2025 -> osevní plán -> rozhodovací backtest.

Spuštění:  python3 osevni_plan/spust.py
Výstupy:   osevni_plan/vystupy/        hlavní tabulky a grafy
           osevni_plan/vystupy/detaily/ podpůrné tabulky
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from scipy.stats import hypergeom
from statsmodels.stats.multitest import multipletests

import backtest as bt
import data as dt
import modely as md
import optimalizace as op

warnings.simplefilter("ignore")
OUT = Path(__file__).resolve().parent / "vystupy"
DET = OUT / "detaily"
DET.mkdir(parents=True, exist_ok=True)

ALTERNATIVNI_MODEL_VYNOSU = "prumer3"   # nejlepší CRPS, kandidát pro citlivostní analýzu
N_SCENARU = 5000
SEED = 2025
LAMBDY = [0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]
KORELACE_RIZIKOVA = 0.70
KORELACE_DIVERZIFIKACE = -0.50

# Paleta (referenční kategorická, světlý režim) + neutrální šedá pro kontext
MODRA, ORANZOVA, AQUA, SEDA, INK, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c", "#0b0b0b", "#52514e"
plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": SEDA, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.dpi": 160,
})


def nazvy(index) -> list[str]:
    return [dt.NAZVY[k] for k in index]


def analyzuj_korelace_marzi(M: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Korelace marží napříč scénáři a dvojice se silnou závislostí."""
    nazvy_plodin = nazvy(dt.KODY)
    matice = pd.DataFrame(np.corrcoef(M, rowvar=False), index=nazvy_plodin, columns=nazvy_plodin)
    dvojice = []
    for i, prvni in enumerate(nazvy_plodin):
        for j in range(i + 1, len(nazvy_plodin)):
            korelace = float(matice.iat[i, j])
            if korelace >= KORELACE_RIZIKOVA:
                typ = "Silná kladná (riziková)"
            elif korelace <= KORELACE_DIVERZIFIKACE:
                typ = "Silná záporná (diverzifikace)"
            else:
                continue
            dvojice.append({
                "plodina_1": prvni,
                "plodina_2": nazvy_plodin[j],
                "korelace": korelace,
                "typ": typ,
            })
    pary = pd.DataFrame(dvojice, columns=["plodina_1", "plodina_2", "korelace", "typ"])
    if not pary.empty:
        pary = pary.sort_values("korelace", ascending=False, ignore_index=True)
    return matice, pary


def krok_korelace_marzi(M: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    matice, pary = analyzuj_korelace_marzi(M)
    matice.to_csv(DET / "korelace_marzi_2025.csv", index_label="plodina")
    pary.to_csv(DET / "pary_korelace_marzi_2025.csv", index=False)
    return matice, pary


def analyzuj_soubeh_narodnich_vynosu(vynosy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Najde souběhy trendově slabých národních výnosů a testuje jejich četnost."""
    slabe_roky = {}
    dostupne_roky = {}
    for kod in dt.KODY:
        rada = np.log(vynosy[kod].where(vynosy[kod] > 0).dropna())
        roky = rada.index.astype(int)
        trend = np.polyval(np.polyfit(roky.to_numpy(float), rada.to_numpy(), 1), roky.to_numpy(float))
        odchylka = pd.Series(rada.to_numpy() - trend, index=roky)
        slabe_roky[kod] = set(odchylka[odchylka <= odchylka.quantile(0.10)].index)
        dostupne_roky[kod] = set(roky)

    matice = pd.DataFrame(0, index=nazvy(dt.KODY), columns=nazvy(dt.KODY), dtype=int)
    dvojice = []
    for i, prvni in enumerate(dt.KODY):
        for druhy in dt.KODY[i + 1:]:
            roky = dostupne_roky[prvni] & dostupne_roky[druhy]
            slabe_prvni = slabe_roky[prvni] & roky
            slabe_druhe = slabe_roky[druhy] & roky
            spolecne = slabe_prvni & slabe_druhe
            n = len(roky)
            n_prvni, n_druhe, pozorovano = len(slabe_prvni), len(slabe_druhe), len(spolecne)
            ocekavano = n_prvni * n_druhe / n
            p = float(hypergeom.sf(pozorovano - 1, n, n_prvni, n_druhe))
            matice.loc[dt.NAZVY[prvni], dt.NAZVY[druhy]] = pozorovano
            matice.loc[dt.NAZVY[druhy], dt.NAZVY[prvni]] = pozorovano
            dvojice.append({
                "plodina_1": dt.NAZVY[prvni],
                "plodina_2": dt.NAZVY[druhy],
                "pocet_spolecnych_slabych_roku": pozorovano,
                "ocekavano_pri_nezavislosti": ocekavano,
                "p_hodnota": p,
                "roky": ", ".join(map(str, sorted(spolecne))),
            })
    pary = pd.DataFrame(dvojice)
    pary["q_hodnota_BH"] = multipletests(pary["p_hodnota"], method="fdr_bh")[1]
    pary = pary.sort_values(
        ["pocet_spolecnych_slabych_roku", "p_hodnota"], ascending=[False, True], ignore_index=True
    )
    return matice, pary


def krok_soubehu_narodnich_vynosu(vynosy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    matice, pary = analyzuj_soubeh_narodnich_vynosu(vynosy)
    matice.to_csv(DET / "souběh_slabych_vynosu_narodni.csv", index_label="plodina")
    pary.to_csv(DET / "dvojice_slaby_vynos_narodni.csv", index=False)
    return matice, pary


# --------------------------------------------------------------------------
def krok_backtest(K: md.Kontext):
    btc = bt.predikce_backtest(K, md.MODELY_CEN, "cena")
    bty = bt.predikce_backtest(K, md.MODELY_VYNOSU, "vynos")
    mc, my = bt.vyhodnot(btc), bt.vyhodnot(bty)
    sc, sy = bt.souhrn(mc, "naivni"), bt.souhrn(my, "naivni")
    sc.round(4).to_csv(OUT / "backtest_ceny_souhrn.csv")
    sy.round(4).to_csv(OUT / "backtest_vynosy_souhrn.csv")
    mc.pivot_table(index="kod", columns="model", values="crps").rename(index=dt.NAZVY).round(4) \
        .to_csv(DET / "backtest_ceny_crps_podle_plodiny.csv")
    my.pivot_table(index="kod", columns="model", values="crps").rename(index=dt.NAZVY).round(4) \
        .to_csv(DET / "backtest_vynosy_crps_podle_plodiny.csv")
    dm = {
        "ceny_kombinace_vs_naivni": bt.diebold_mariano(mc, "kombinace", "naivni"),
        "ceny_ar_sdileny_vs_naivni": bt.diebold_mariano(mc, "ar_sdileny", "naivni"),
        "vynosy_kombinace_vs_naivni": bt.diebold_mariano(my, "kombinace", "naivni"),
        "vynosy_kombinace_vs_prumer5": bt.diebold_mariano(my, "kombinace", "prumer5"),
        "vynosy_kombinace_vs_prumer3": bt.diebold_mariano(my, "kombinace", "prumer3"),
        "vynosy_kombinace_vs_prumer3_mae": bt.diebold_mariano(my, "kombinace", "prumer3", "abs_chyba"),
        "vynosy_arima_vs_naivni": bt.diebold_mariano(my, "arima", "naivni"),
        "vynosy_pocasi_vs_trend15": bt.diebold_mariano(my, "trend15_pocasi", "trend15"),
    }
    return btc, bty, mc, my, sc, sy, dm


def krok_pocasi(K: md.Kontext, data: dt.Data) -> dict:
    """Kolik počasí vysvětluje a co by přineslo, kdybychom ho znali dopředu (oracle)."""
    gamma, _ = md.odhad_pocasi(K.do(2024), 2024)
    gamma = gamma.rename(index=dt.NAZVY)
    gamma.round(4).to_csv(DET / "pocasi_koeficienty_2024.csv")
    chyby = {"klimatologie": [], "oracle": []}
    for T in range(2010, 2024):
        k_T = K.do(T)
        skut = K.ly.loc[T + 1]
        p_klima = md.vynos_trend_pocasi(k_T, T)
        p_oracle = md.vynos_trend_pocasi(k_T, T, pocasi_T1=data.pocasi.loc[T + 1])
        chyby["klimatologie"].append((skut - p_klima).abs().mean())
        chyby["oracle"].append((skut - p_oracle).abs().mean())
    return {
        "mae_klimatologie": float(np.mean(chyby["klimatologie"])),
        "mae_oracle_se_znalosti_pocasi": float(np.mean(chyby["oracle"])),
        "koeficienty_na_1_sd": gamma.drop_duplicates().round(4).to_dict(orient="index"),
        "sd_srazky_mm": float(data.pocasi["srazky"].std()),
        "sd_teplota_c": float(data.pocasi["teplota"].std()),
    }


# --------------------------------------------------------------------------
def scenare_marzi(bod_lp, bod_ly, Ec, Ey, naklady, rng, n=N_SCENARU, vyhladit=True):
    sc, sy, roky = bt.scenare_chyb(Ec, Ey, n, rng, vyhladit=vyhladit)
    P = np.exp(bod_lp.to_numpy() + sc)
    Y = np.exp(bod_ly.to_numpy() + sy)
    M = P * Y / 1000 - naklady.to_numpy()
    return P, Y, M, roky


def podklady_2025(K, btc, bty, model_cen, model_vynosu):
    """Bodová predikce 2025 a matice historických chyb pro zvolené modely."""
    T = dt.POSLEDNI_ROK
    k = K.do(T)
    bod_lp = md.MODELY_CEN[model_cen](k, T)
    bod_ly = md.MODELY_VYNOSU[model_vynosu](k, T)
    return bod_lp, bod_ly, bt.matice_chyb(btc, model_cen), bt.matice_chyb(bty, model_vynosu)


def krok_predikce_2025(K, data, btc, bty, model_cen, model_vynosu):
    T = dt.POSLEDNI_ROK
    bod_lp, bod_ly, Ec, Ey = podklady_2025(K, btc, bty, model_cen, model_vynosu)
    ocek_infl = data.makro.loc[T, "inflace"] / 100
    naklady_2025 = data.naklady_2024 * (1 + ocek_infl)
    rng = np.random.default_rng(SEED)
    P, Y, M, roky = scenare_marzi(bod_lp, bod_ly, Ec, Ey, naklady_2025, rng)

    def q(a, p):
        return np.quantile(a, p, axis=0)

    tab = pd.DataFrame({
        "plodina": nazvy(dt.KODY),
        "cena_2024": data.ceny.loc[T].values,
        "cena_2025_median": q(P, 0.5), "cena_2025_q10": q(P, 0.1), "cena_2025_q90": q(P, 0.9),
        "vynos_2024": data.vynosy.loc[T].values,
        "vynos_2025_median": q(Y, 0.5), "vynos_2025_q10": q(Y, 0.1), "vynos_2025_q90": q(Y, 0.9),
        "naklady_2025": naklady_2025.values,
        "marze_2024": dt.marze_2024(data)["marze_kc_ha"].values,
        "marze_2025_prumer": M.mean(axis=0), "marze_2025_median": q(M, 0.5),
        "marze_2025_q10": q(M, 0.1), "marze_2025_q90": q(M, 0.9),
        "p_ztraty": (M < 0).mean(axis=0),
    }, index=pd.Index(dt.KODY, name="kod"))
    tab.round(3).to_csv(OUT / "predikce_2025.csv")
    kor = {
        "cena_vynos_stejna_plodina": {dt.NAZVY[c]: round(float(Ec[c].corr(Ey[c])), 3) for c in dt.KODY},
        "ceny_obiloviny": Ec[["0111", "0115", "0116", "0112"]].corr().rename(index=dt.NAZVY, columns=dt.NAZVY).round(2).to_dict(),
        "psenice_jecmen_chyby_vs_scenare": [round(float(Ec["0111"].corr(Ec["0115"])), 3),
                                            round(float(np.corrcoef(np.log(P[:, 0]), np.log(P[:, 1]))[0, 1]), 3)],
        "prumerna_korelace_chyb_cen": float(Ec.corr().to_numpy()[np.triu_indices(20, 1)].mean()),
        "prumerna_korelace_chyb_vynosu": float(Ey.corr().to_numpy()[np.triu_indices(20, 1)].mean()),
    }
    info = {
        "model_cen": model_cen, "model_vynosu": model_vynosu,
        "ocekavana_inflace_2025": ocek_infl, "roky_v_poolu_chyb": [int(r) for r in Ec.index],
        "bod_ln_cena": bod_lp.round(4).to_dict(), "bod_ln_vynos": bod_ly.round(4).to_dict(),
    }
    return tab, M, naklady_2025, kor, info, (bod_lp, bod_ly, Ec, Ey)


def krok_plan_2025(data, M_opt, M_test):
    """Optimalizace na scénářích M_opt, vyhodnocení na nezávislé sadě M_test."""
    om = op.omezeni(data.zelenina)
    plany, rizika = {}, {}
    for lam in LAMBDY:
        x = op.optimalizuj(M_opt, om, lam=lam)
        plany[lam] = x
        rizika[lam] = op.rizikove_ukazatele(M_test @ x)
    plan = pd.DataFrame(plany, index=pd.Index(nazvy(dt.KODY), name="plodina")).round(1)
    plan.columns = [f"lambda_{l}" for l in LAMBDY]
    plan["horni_mez_ha"] = om.horni.round(1)
    plan.to_csv(OUT / "osevni_plan_2025.csv")
    rz = pd.DataFrame(rizika).T
    rz.index.name = "lambda"
    rz.round({c: (3 if c == "p_ztraty" else 0) for c in rz.columns}).to_csv(OUT / "osevni_plan_2025_riziko.csv")
    return plan, rz, om


def krok_citlivost(K, data, btc, bty, model_cen, model_vynosu, naklady_2025):
    """Plán 2025 (lambda = 0.5) při změně modelu výnosů a způsobu tvorby scénářů."""
    varianty = [
        ("hlavní (vyhlazený bootstrap)", model_vynosu, True),
        ("bez vyhlazení", model_vynosu, False),
        (f"výnosy {ALTERNATIVNI_MODEL_VYNOSU}", ALTERNATIVNI_MODEL_VYNOSU, True),
        (f"výnosy {ALTERNATIVNI_MODEL_VYNOSU}, bez vyhlazení", ALTERNATIVNI_MODEL_VYNOSU, False),
    ]
    om = op.omezeni(data.zelenina)
    plany, rizika = {}, {}
    for nazev, model_vyn, vyhladit in varianty:
        bod_lp, bod_ly, Ec, Ey = podklady_2025(K, btc, bty, model_cen, model_vyn)
        _, _, M, _ = scenare_marzi(bod_lp, bod_ly, Ec, Ey, naklady_2025, np.random.default_rng(SEED), vyhladit=vyhladit)
        _, _, M_t, _ = scenare_marzi(bod_lp, bod_ly, Ec, Ey, naklady_2025, np.random.default_rng(SEED + 1), vyhladit=vyhladit)
        x = op.optimalizuj(M, om, lam=op.LAMBDA)
        plany[nazev] = x
        rizika[nazev] = op.rizikove_ukazatele(M_t @ x) | {"prumerna_marze_salat": float(M_t[:, dt.KODY.index("01214")].mean())}
    plan = pd.DataFrame(plany, index=pd.Index(nazvy(dt.KODY), name="plodina")).round(1)
    plan = plan[(plan > 0).any(axis=1)]
    plan.to_csv(OUT / "citlivost_plan_2025.csv")
    rz = pd.DataFrame(rizika).T
    rz.round(3).to_csv(DET / "citlivost_riziko_2025.csv")
    return plan, rz


# --------------------------------------------------------------------------
def krok_rozhodovaci_backtest(data, K, btc, bty):
    """Pro T = 2010..2023: plán z informací <= T, zisk podle skutečnosti roku T+1.

    Výběr modelu je vnořený: v roce T se model vybírá pravidlem `bt.vyber_modelu`
    jen z chyb známých do roku T. Test je tak nezávislý na tom, že jsme finální
    model vybrali podle celého období.
    """
    def pred(bt_df, model):
        return bt_df[bt_df["model"] == model].pivot(index="rok", columns="kod", values="predikce")[dt.KODY]

    polni = ~data.zelenina.reindex(dt.KODY).to_numpy(bool)
    om = op.omezeni(data.zelenina)
    radky, vybery = [], []
    rng = np.random.default_rng(SEED)
    for T in range(2010, 2024):
        t = T + 1
        mc, my = bt.vyber_modelu(btc, T), bt.vyber_modelu(bty, T)
        vybery.append({"rok_planu": t, "model_cen": mc, "model_vynosu": my})
        naklady_ocek = dt.naklady_v_roce(data, T) * (1 + data.makro.loc[T, "inflace"] / 100)
        Ec = bt.matice_chyb(btc, mc).loc[:T]
        _, _, M, _ = scenare_marzi(pred(btc, mc).loc[t], pred(bty, my).loc[t], Ec,
                                   bt.matice_chyb(bty, my).loc[:T], naklady_ocek, rng, n=2000)
        _, _, M_alt, _ = scenare_marzi(pred(btc, mc).loc[t], pred(bty, ALTERNATIVNI_MODEL_VYNOSU).loc[t], Ec,
                                       bt.matice_chyb(bty, ALTERNATIVNI_MODEL_VYNOSU).loc[:T], naklady_ocek, rng, n=2000)
        M_naivni = (data.ceny.loc[T] * data.vynosy.loc[T] / 1000 - naklady_ocek).to_numpy()[None, :]
        strategie = {
            "mean-CVaR (lambda 0.5)": op.optimalizuj(M, om, lam=0.5),
            f"mean-CVaR, výnosy {ALTERNATIVNI_MODEL_VYNOSU}": op.optimalizuj(M_alt, om, lam=0.5),
            "max. očekávání (lambda 0)": op.optimalizuj(M, om, lam=0.0),
            "jen CVaR (lambda 1)": op.optimalizuj(M, om, lam=1.0),
            "naivní: loňské marže": op.optimalizuj(M_naivni, om, lam=0.0),
            "rovnoměrně polní plodiny": np.where(polni, op.ROZLOHA / polni.sum(), 0.0),
        }
        skutecna_marze = (data.ceny.loc[t] * data.vynosy.loc[t] / 1000 - dt.naklady_v_roce(data, t)).to_numpy()
        defl = data.makro.loc[t, "cpi_index"]
        for nazev, x in strategie.items():
            radky.append({"rok": t, "strategie": nazev, "zisk_mil_kc_2024": float(x @ skutecna_marze) / defl / 1e6,
                          "ha_zelenina": float(x[~polni].sum())})
    df = pd.DataFrame(radky)
    df.round(3).to_csv(DET / "rozhodovaci_backtest.csv", index=False)
    piv = df.pivot(index="rok", columns="strategie", values="zisk_mil_kc_2024")
    souhrn = pd.DataFrame({
        "prumer": piv.mean(), "median": piv.median(), "smer_odch": piv.std(),
        "nejhorsi_rok": piv.min(), "roky_se_ztratou": (piv < 0).sum(), "soucet": piv.sum(),
    }).sort_values("prumer", ascending=False)
    souhrn.round(2).to_csv(OUT / "rozhodovaci_backtest_souhrn.csv")
    pd.DataFrame(vybery).to_csv(DET / "rozhodovaci_backtest_vybery_modelu.csv", index=False)
    return piv, souhrn


# --------------------------------------------------------------------------
# Grafy
# --------------------------------------------------------------------------
def graf_backtest(sc, sy):
    fig, osy = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, s, titulek in [(osy[0], sc, "Ceny"), (osy[1], sy, "Výnosy")]:
        s = s.sort_values("crps_vs_bench", ascending=False)
        barvy = [MODRA if m == "kombinace" else (SEDA if m == "naivni" else "#b9d3f2") for m in s.index]
        ax.barh(s.index, s["crps_vs_bench"], color=barvy, height=0.6)
        ax.axvline(1, color=INK2, lw=1)
        ax.set_xlim(0.75, 1.12)
        ax.set_title(f"{titulek}: CRPS vůči naivní predikci", loc="left", color=INK, fontsize=11)
        ax.set_xlabel("poměr (méně = lepší)")
        for i, v in enumerate(s["crps_vs_bench"]):
            ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=9, color=INK2)
        ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "graf_backtest_modelu.png")
    plt.close(fig)


def graf_kalibrace(mc, my):
    fig, osy = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    for ax, m, titulek in [(osy[0], mc, "Ceny"), (osy[1], my, "Výnosy")]:
        pit = m[m["model"] == "kombinace"]["pit"]
        ax.hist(pit, bins=10, range=(0, 1), color=MODRA, rwidth=0.92)
        ax.axhline(len(pit) / 10, color=INK2, lw=1, ls="--")
        ax.set_title(f"{titulek}: PIT histogram (ideál = rovná čára)", loc="left", color=INK, fontsize=11)
        ax.set_xlabel("kvantil skutečnosti v predikovaném rozdělení")
    osy[0].set_ylabel("počet (plodina × rok)")
    fig.tight_layout()
    fig.savefig(DET / "graf_kalibrace_pit.png")
    plt.close(fig)


def graf_vejire(data, tab, K, btc, bty):
    kody = ["0111", "01443", "01510", "01232"]
    fig, osy = plt.subplots(2, 4, figsize=(13, 5.6))
    for j, kod in enumerate(kody):
        for i, (hist, pref, jed, bt_df) in enumerate([
            (data.ceny, "cena", "Kč/t", btc), (data.vynosy, "vynos", "kg/ha", bty)]):
            ax = osy[i, j]
            s = hist[kod].loc[2000:]
            ax.plot(s.index, s.values, color=INK2, lw=1.6)
            b = bt_df[(bt_df["model"] == "kombinace") & (bt_df["kod"] == kod)].set_index("rok")
            ax.plot(b.index, np.exp(b["predikce"]), color=MODRA, lw=1.2, ls="--")
            r = tab.loc[kod]
            ax.fill_between([2024, 2025], [s.loc[2024], r[f"{pref}_2025_q10"]],
                            [s.loc[2024], r[f"{pref}_2025_q90"]], color=MODRA, alpha=0.18, lw=0)
            ax.plot([2024, 2025], [s.loc[2024], r[f"{pref}_2025_median"]], color=MODRA, lw=2)
            ax.plot(2025, r[f"{pref}_2025_median"], "o", color=MODRA, ms=5)
            ax.set_title(f"{dt.NAZVY[kod]}: {'cena' if i == 0 else 'výnos'} ({jed})", loc="left", fontsize=10, color=INK)
            ax.ticklabel_format(axis="y", style="plain")
    osy[0, 0].plot([], [], color=INK2, lw=1.6, label="skutečnost")
    osy[0, 0].plot([], [], color=MODRA, lw=1.2, ls="--", label="predikce v backtestu (o rok dopředu)")
    osy[0, 0].fill_between([], [], [], color=MODRA, alpha=0.18, label="2025: 80% interval")
    osy[0, 0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "graf_predikce_2025.png")
    plt.close(fig)


def graf_marze(tab, M):
    poradi = np.argsort(tab["marze_2025_median"].to_numpy() / 1)
    fig, osy = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [1, 1]})
    zelenina_bez_rajcat = tab.index.isin(dt.KODY[11:]) & (tab.index != "01234")
    for ax, maska, titulek in [(osy[0], ~tab.index.isin(dt.KODY[11:]), "Polní plodiny"),
                               (osy[1], zelenina_bez_rajcat, "Zelenina bez rajčat")]:
        idx = [i for i in poradi if maska[i]]
        data_box = [M[:, i] / 1000 for i in idx]
        ax.boxplot(data_box, vert=False, whis=(10, 90), showfliers=False, widths=0.55,
                   medianprops=dict(color=MODRA, lw=2), boxprops=dict(color=INK2), whiskerprops=dict(color=INK2),
                   capprops=dict(color=INK2))
        ax.set_yticks(range(1, len(idx) + 1), [tab["plodina"].iloc[i] for i in idx])
        ax.axvline(0, color=ORANZOVA, lw=1)
        ax.set_title(f"{titulek}: marže 2025 (tis. Kč/ha)", loc="left", color=INK, fontsize=11)
        ax.set_xlabel("krabice = 25-75 %, fousy = 10-90 % scénářů")
        ax.grid(axis="y", visible=False)
    r = tab.loc["01234"]
    osy[1].text(0.02, -0.16, f"Rajčata mimo graf: medián {r['marze_2025_median'] / 1e6:.1f} mil. Kč/ha, "
                f"ztráta v {r['p_ztraty']:.0%} scénářů", transform=osy[1].transAxes, fontsize=9, color=INK2)
    fig.tight_layout()
    fig.savefig(OUT / "graf_marze_2025.png")
    plt.close(fig)


def graf_plan(plan, rz):
    fig, osy = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = osy[0]
    doporuceny = plan[f"lambda_{op.LAMBDA}"]
    s = doporuceny[doporuceny > 0].sort_values()
    ax.barh(s.index, s.values, color=MODRA, height=0.6)
    for i, v in enumerate(s.values):
        ax.text(v + 3, i, f"{v:.0f} ha", va="center", fontsize=9, color=INK2)
    ax.set_title(f"Doporučený osevní plán 2025 (lambda = {op.LAMBDA})", loc="left", color=INK, fontsize=11)
    ax.set_xlim(0, 300)
    ax.grid(axis="y", visible=False)
    ax = osy[1]
    x, y = rz["CVaR10"] / 1e6, rz["ocekavany_zisk"] / 1e6
    ax.plot(x, y, "-o", color=MODRA, lw=2, ms=7)
    for lam, xi, yi in zip(rz.index, x, y):
        ax.annotate(f"λ = {lam}", (xi, yi), textcoords="offset points", xytext=(6, -12), fontsize=9, color=INK2)
    ax.set_xlabel("CVaR 10 % (průměr 10 % nejhorších scénářů), mil. Kč")
    ax.set_ylabel("očekávaný zisk, mil. Kč")
    ax.set_title("Kompromis výnos-riziko", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "graf_osevni_plan_2025.png")
    plt.close(fig)


def graf_korelace_marzi(matice):
    fig, ax = plt.subplots(figsize=(13, 11))
    obraz = ax.imshow(matice.to_numpy(), cmap="RdYlBu_r", vmin=-1, vmax=1)
    popisky = matice.columns.tolist()
    ax.set_xticks(range(len(popisky)), labels=popisky, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(popisky)), labels=popisky, fontsize=8)
    ax.tick_params(length=0)
    ax.grid(False)
    for i in range(len(popisky)):
        for j in range(len(popisky)):
            hodnota = matice.iat[i, j]
            ax.text(j, i, f"{hodnota:.2f}", ha="center", va="center", fontsize=6,
                    color="white" if abs(hodnota) > 0.65 else INK)
            if i == j:
                continue
            if hodnota >= KORELACE_RIZIKOVA:
                barva = ORANZOVA
            elif hodnota <= KORELACE_DIVERZIFIKACE:
                barva = MODRA
            else:
                continue
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=barva, linewidth=1.8))
    ax.set_title("Korelace scénářových marží plodin pro rok 2025", loc="left", color=INK, fontsize=13, pad=14)
    legenda = [
        Patch(facecolor="none", edgecolor=ORANZOVA, linewidth=2,
              label=f"Silná kladná korelace (r ≥ {KORELACE_RIZIKOVA:.2f}): společné riziko"),
        Patch(facecolor="none", edgecolor=MODRA, linewidth=2,
              label=f"Silná záporná korelace (r ≤ {KORELACE_DIVERZIFIKACE:.2f}): možná diverzifikace"),
    ]
    ax.legend(handles=legenda, loc="upper left", bbox_to_anchor=(0, -0.27), frameon=False, fontsize=9)
    bar = fig.colorbar(obraz, ax=ax, fraction=0.045, pad=0.04)
    bar.set_label("Pearsonův korelační koeficient")
    fig.subplots_adjust(left=0.27, bottom=0.32, right=0.91, top=0.92)
    fig.savefig(OUT / "graf_korelace_marzi_2025.png")
    plt.close(fig)


def graf_soubehu_vynosu(pary):
    top = pary.head(10).sort_values("pocet_spolecnych_slabych_roku")
    popisky = [f"{r.plodina_1} – {r.plodina_2}" for r in top.itertuples()]
    barvy = [ORANZOVA if p < 0.05 else SEDA for p in top["p_hodnota"]]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    y = np.arange(len(top))
    ax.barh(y, top["pocet_spolecnych_slabych_roku"], color=barvy, height=0.68)
    ax.scatter(top["ocekavano_pri_nezavislosti"], y, marker="D", color=INK, s=24, zorder=3)
    for yi, row in zip(y, top.itertuples()):
        ax.text(row.pocet_spolecnych_slabych_roku + 0.08, yi, f"q = {row.q_hodnota_BH:.3f}",
                va="center", fontsize=8, color=INK2)
    ax.set_yticks(y, labels=popisky, fontsize=9)
    ax.set_xlim(0, top["pocet_spolecnych_slabych_roku"].max() + 1.3)
    ax.set_xlabel("Počet společných slabých let (z 32)")
    fig.suptitle("Souběh slabých národních výnosů", x=0.19, y=0.98, ha="left", color=INK, fontsize=13)
    fig.text(0.19, 0.94, "10 nejčastějších dvojic; žádná není průkazná po korekci 190 testů",
             fontsize=9, color=INK2)
    ax.legend(handles=[
        Patch(facecolor=ORANZOVA, label="Neupravené p < 0,05; po korekci neprůkazné"),
        Patch(facecolor=SEDA, label="Neupravené p ≥ 0,05"),
        Line2D([], [], marker="D", color=INK, linestyle="None", label="Očekávání při nezávislosti"),
    ], frameon=False, loc="lower right", fontsize=8)
    fig.subplots_adjust(left=0.30, right=0.98, bottom=0.15, top=0.88)
    fig.savefig(OUT / "graf_soubehu_slabych_vynosu_narodni.png")
    plt.close(fig)


def graf_rozhodovaci(piv):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    styly = {
        "mean-CVaR (lambda 0.5)": (MODRA, 2.4, "-"),
        "max. očekávání (lambda 0)": (ORANZOVA, 1.6, "-"),
        "naivní: loňské marže": (SEDA, 1.6, "--"),
        "rovnoměrně polní plodiny": (AQUA, 1.6, "-"),
        "jen CVaR (lambda 1)": ("#4a3aa7", 1.2, ":"),
    }
    kum = piv.cumsum()
    posledni_y = []
    for s, (c, lw, ls) in sorted(styly.items(), key=lambda kv: -kum[kv[0]].iloc[-1]):
        ax.plot(kum.index, kum[s], color=c, lw=lw, ls=ls, label=s)
        y = kum[s].iloc[-1]
        if posledni_y and posledni_y[-1] - y < 14:   # popisky se nesmí překrývat
            y = posledni_y[-1] - 14
        posledni_y.append(y)
        ax.text(kum.index[-1] + 0.2, y, f"{kum[s].iloc[-1]:.0f}", va="center", fontsize=9, color=c)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_ylabel("kumulovaný zisk, mil. Kč (ceny 2024)")
    ax.set_title("Rozhodovací backtest 2011-2024: model i plán jen z dat do roku T, zisk podle skutečnosti T+1",
                 loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_xlim(2010.5, 2025.5)
    fig.tight_layout()
    fig.savefig(OUT / "graf_rozhodovaci_backtest.png")
    plt.close(fig)


# --------------------------------------------------------------------------
def main():
    data = dt.nacti()
    K = md.Kontext.z_dat(data)

    print("0/5 souběh slabých národních výnosů ...")
    matice_soubehu, pary_soubehu = krok_soubehu_narodnich_vynosu(data.vynosy)

    print("1/5 backtest modelů ...")
    btc, bty, mc, my, sc, sy, dm = krok_backtest(K)
    pocasi = krok_pocasi(K, data)

    model_cen, model_vynosu = bt.vyber_modelu(btc, dt.POSLEDNI_ROK), bt.vyber_modelu(bty, dt.POSLEDNI_ROK)
    print(f"   vybrané modely (nejnižší MAE 2003-2024): ceny = {model_cen}, výnosy = {model_vynosu}")

    print("2/5 scénáře 2025 ...")
    tab, M, naklady_2025, kor, info, (bod_lp, bod_ly, Ec, Ey) = krok_predikce_2025(
        K, data, btc, bty, model_cen, model_vynosu)
    korelace_marzi, pary_korelace_marzi = krok_korelace_marzi(M)

    print("3/5 osevní plán 2025 ...")
    rng = np.random.default_rng(SEED + 1)
    _, _, M_test, _ = scenare_marzi(bod_lp, bod_ly, Ec, Ey, naklady_2025, rng)
    plan, rz, om = krok_plan_2025(data, M, M_test)
    plan_cit, rz_cit = krok_citlivost(K, data, btc, bty, model_cen, model_vynosu, naklady_2025)

    print("4/5 rozhodovací backtest ...")
    piv, souhrn_rb = krok_rozhodovaci_backtest(data, K, btc, bty)

    print("5/5 grafy ...")
    graf_backtest(sc, sy)
    graf_kalibrace(mc, my)
    graf_vejire(data, tab, K, btc, bty)
    graf_marze(tab, M)
    graf_plan(plan, rz)
    graf_korelace_marzi(korelace_marzi)
    graf_soubehu_vynosu(pary_soubehu)
    graf_rozhodovaci(piv)

    vysledky = {
        "backtest_ceny": sc.round(4).to_dict(orient="index"),
        "backtest_vynosy": sy.round(4).to_dict(orient="index"),
        "diebold_mariano_t_p": dm,
        "pocasi": pocasi,
        "korelace": kor,
        "korelace_marzi_problemove_pary": pary_korelace_marzi.to_dict(orient="records"),
        "narodni_soubeh_slabych_vynosu": {
            "pocet_testovanych_dvojic": len(pary_soubehu),
            "pocet_neupravenych_pod_005": int((pary_soubehu["p_hodnota"] < 0.05).sum()),
            "pocet_po_BH_pod_005": int((pary_soubehu["q_hodnota_BH"] < 0.05).sum()),
            "nejcastejsi_dvojice": pary_soubehu.head(4).to_dict(orient="records"),
        },
        "predikce_info": info,
        "plan_riziko": rz.round(3).to_dict(orient="index"),
        "rozhodovaci_backtest": souhrn_rb.round(2).to_dict(orient="index"),
        "citlivost_riziko": rz_cit.round(3).to_dict(orient="index"),
    }
    (DET / "vysledky.json").write_text(json.dumps(vysledky, ensure_ascii=False, indent=2, default=float))

    pd.set_option("display.width", 200)
    print(sc[["mae", "crps", "crps_vs_bench", "pokryti80", "pokryti95"]].round(3))
    print(sy[["mae", "crps", "crps_vs_bench", "pokryti80", "pokryti95"]].round(3))
    print(tab[["plodina", "cena_2025_median", "vynos_2025_median", "marze_2025_prumer", "marze_2025_q10", "p_ztraty"]].round(2))
    print(plan)
    print((rz.drop(columns="p_ztraty") / 1e6).round(2).assign(p_ztraty=rz["p_ztraty"].round(3)))
    print(souhrn_rb)
    print(plan_cit)
    print(pary_korelace_marzi.to_string(index=False))
    print(pary_soubehu.head(10).to_string(index=False))
    print((rz_cit / 1e6).round(2))
    print(json.dumps(pocasi, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
