"""Backtest s rolujícím počátkem, scénáře nejistoty a metriky přesnosti.

Postup pro každý počátek T (konec roku T):
  1. Kontext se ořízne na roky <= T.
  2. Každý model predikuje ln hodnotu pro T+1.
  3. Chyba e_{i,T+1} = skutečnost - predikce se uloží.

Tyto chyby jsou skutečné chyby predikce "mimo vzorek". Z nich se staví
nejistota: pro predikci roku t se použijí jen chyby z let < t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data import KODY
from modely import Kontext

PRVNI_POCATEK = 2002           # trénink 1993-2002 (10 let), první predikce 2003
PRVNI_VYHODNOCENY_ROK = 2011   # od 2011 máme >= 8 let historie chyb pro intervaly
MIN_CHYB = 8


def predikce_backtest(kontext: Kontext, modely: dict, veliciny: str, posledni_pocatek: int = 2023) -> pd.DataFrame:
    """Vrací dlouhou tabulku: model, rok (cílový), kod, predikce, skutecnost, chyba (vše v ln)."""
    skutecne = kontext.lp if veliciny == "cena" else kontext.ly
    radky = []
    for T in range(PRVNI_POCATEK, posledni_pocatek + 1):
        k_T = kontext.do(T)
        for nazev, f in modely.items():
            pred = f(k_T, T)
            for kod in KODY:
                radky.append((nazev, T + 1, kod, float(pred[kod]), float(skutecne.loc[T + 1, kod])))
    df = pd.DataFrame(radky, columns=["model", "rok", "kod", "predikce", "skutecnost"])
    df["chyba"] = df["skutecnost"] - df["predikce"]
    return df


def matice_chyb(bt: pd.DataFrame, model: str) -> pd.DataFrame:
    """Chyby jednoho modelu jako tabulka rok x plodina."""
    return bt[bt["model"] == model].pivot(index="rok", columns="kod", values="chyba")[KODY]


# --------------------------------------------------------------------------
# Scénáře: ročníkový bootstrap chyb
# --------------------------------------------------------------------------

def faktor_jadra(n: int) -> float:
    """Silvermanův faktor šířky jádra relativně ke směrodatné odchylce: b = 0.9 * n^(-1/5)."""
    return 0.9 * n ** (-0.2)


def vyhlazeny_bootstrap(E: np.ndarray, n: int, rng: np.random.Generator, vyhladit: bool = True):
    """Losuje n řádků z matice chyb E (roky x veličiny) ročníkovým bootstrapem.

    Bez vyhlazení: vybere se celý historický rok s a vezmou se jeho chyby.
    S vyhlazením (Silverman 1986, kap. 6.4, varianta se zachováním rozptylu):
        x = e_bar + (e_s - e_bar + b * eps) / sqrt(1 + b^2),  eps ~ N(0, Sigma)
    Sigma je výběrová kovarianční matice chyb, takže šum má stejné korelace jako
    chyby samotné. eps generujeme jako náhodnou kombinaci centrovaných řádků E,
    což dává přesně kovarianci Sigma i při singulární matici (40 veličin, 22 let).
    Dělení sqrt(1 + b^2) vrací rozptyl zpět na Sigma a průměr zůstává e_bar.
    Vyhlazení tak jen "rozmaže" 22 historických let, nemění průměr ani korelace.
    Vrací (scénáře n x d, index vylosovaného roku).
    """
    m = E.shape[0]
    tah = rng.integers(0, m, size=n)
    if not vyhladit:
        return E[tah], tah
    e_bar = E.mean(axis=0)
    C = E - e_bar
    b = faktor_jadra(m)
    eps = rng.normal(size=(n, m)) @ C / np.sqrt(m - 1)
    return e_bar + (C[tah] + b * eps) / np.sqrt(1 + b**2), tah


def scenare_chyb(chyby_cen: pd.DataFrame, chyby_vynosu: pd.DataFrame, n: int, rng: np.random.Generator,
                 vyhladit: bool = True):
    """Losuje n společných scénářů chyb pro všech 20 cen a 20 výnosů.

    Každý scénář = jeden historický rok s. Bere se chyba všech cen i výnosů z roku s,
    takže korelace mezi plodinami a vazba cena-výnos zůstanou zachované.
    """
    roky = chyby_cen.dropna().index.intersection(chyby_vynosu.dropna().index)
    E = np.hstack([chyby_cen.loc[roky].to_numpy(), chyby_vynosu.loc[roky].to_numpy()])
    S, tah = vyhlazeny_bootstrap(E, n, rng, vyhladit)
    d = chyby_cen.shape[1]
    return S[:, :d], S[:, d:], roky[tah]


# --------------------------------------------------------------------------
# Metriky
# --------------------------------------------------------------------------

def crps_vzorek(vzorek: np.ndarray, y: float) -> float:
    """CRPS z ensemble: E|X - y| - 0.5 E|X - X'|. Menší je lepší, jednotky jako y."""
    x = np.sort(vzorek)
    n = len(x)
    prvni = np.mean(np.abs(x - y))
    # E|X-X'| pro seřazený vzorek: 2/n^2 * sum (2i - n - 1) x_i
    i = np.arange(1, n + 1)
    druhy = 2.0 / n**2 * np.sum((2 * i - n - 1) * x)
    return prvni - 0.5 * druhy


def interval_score(dolni: float, horni: float, y: float, alfa: float) -> float:
    """Winklerovo skóre: šířka intervalu + penalizace 2/alfa za každé minutí."""
    return (horni - dolni) + 2 / alfa * max(dolni - y, 0) + 2 / alfa * max(y - horni, 0)


def vyhodnot(bt: pd.DataFrame, n_vzorku: int = 2000, seed: int = 1) -> pd.DataFrame:
    """Pro každý model, rok >= PRVNI_VYHODNOCENY_ROK a plodinu spočte bodové i pravděpodobnostní metriky.

    Pravděpodobnostní predikce roku t = bodová predikce + vyhlazený bootstrap chyb
    stejného modelu z let < t (jen minulost, žádný únik informace).
    """
    rng = np.random.default_rng(seed)
    radky = []
    for model in bt["model"].unique():
        E = matice_chyb(bt, model)
        sub = bt[(bt["model"] == model) & (bt["rok"] >= PRVNI_VYHODNOCENY_ROK)]
        for r in sub.itertuples():
            minule = E.loc[:r.rok - 1, r.kod].dropna()
            if len(minule) < MIN_CHYB:
                continue
            e, _ = vyhlazeny_bootstrap(minule.to_numpy()[:, None], n_vzorku, rng)
            vz = r.predikce + e[:, 0]
            q = np.quantile(vz, [0.025, 0.10, 0.90, 0.975])
            radky.append({
                "model": model, "rok": r.rok, "kod": r.kod,
                "abs_chyba": abs(r.chyba), "chyba": r.chyba,
                "crps": crps_vzorek(vz, r.skutecnost),
                "pokryti80": q[1] <= r.skutecnost <= q[2],
                "pokryti95": q[0] <= r.skutecnost <= q[3],
                "is80": interval_score(q[1], q[2], r.skutecnost, 0.2),
                "pit": float(np.mean(vz <= r.skutecnost)),
            })
    return pd.DataFrame(radky)


def souhrn(metriky: pd.DataFrame, benchmark: str) -> pd.DataFrame:
    """Agregace přes plodiny a roky + poměr MAE a CRPS vůči benchmarku."""
    s = metriky.groupby("model").agg(
        mae=("abs_chyba", "mean"), bias=("chyba", "mean"), crps=("crps", "mean"),
        pokryti80=("pokryti80", "mean"), pokryti95=("pokryti95", "mean"), is80=("is80", "mean"),
    )
    s["mae_vs_bench"] = s["mae"] / s.loc[benchmark, "mae"]
    s["crps_vs_bench"] = s["crps"] / s.loc[benchmark, "crps"]
    # Kolikrát (plodina x rok) je model lepší než benchmark v absolutní chybě
    piv = metriky.pivot_table(index=["rok", "kod"], columns="model", values="abs_chyba")
    s["podil_lepsi_nez_bench"] = (piv.lt(piv[benchmark], axis=0)).mean()
    return s.sort_values("crps")


def vyber_modelu(bt_df: pd.DataFrame, do_roku: int) -> str:
    """Pravidlo výběru: nejnižší MAE (log) přes všechny plodiny a roky <= do_roku.

    MAE je k dispozici od prvního roku backtestu (2003), takže pravidlo jde
    použít i vnořeně: v rozhodovacím backtestu se pro rok T+1 vybírá jen podle
    chyb známých v roce T. Pro finální plán 2025 je do_roku = 2024.
    """
    sub = bt_df[bt_df["rok"] <= do_roku]
    return sub.assign(a=sub["chyba"].abs()).groupby("model")["a"].mean().idxmin()


def diebold_mariano(metriky: pd.DataFrame, a: str, b: str, sloupec: str = "crps") -> tuple[float, float]:
    """Jednoduchý DM test na ročních průměrech ztráty (průměr přes plodiny v každém roce).

    Průměrováním přes plodiny v rámci roku se zbavíme korelace mezi plodinami
    ve stejném roce. Zbývá ~14 ročních pozorování, test má proto malou sílu.
    """
    from scipy import stats
    roc = metriky.pivot_table(index="rok", columns="model", values=sloupec, aggfunc="mean")
    d = (roc[a] - roc[b]).dropna()
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    p = 2 * (1 - stats.t.cdf(abs(t), df=len(d) - 1))
    return float(t), float(p)
