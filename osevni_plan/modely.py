"""Predikční modely pro log-ceny a log-výnosy.

Každý model je funkce `f(kontext, T) -> pd.Series` s bodovou predikcí logaritmu
pro rok T + 1. Model smí použít jen data s rokem <= T; to hlídá `Kontext.do(T)`,
který vrací kopie tabulek oříznuté na T. Díky tomu stejný kód slouží pro
backtest (T = 2002 ... 2023) i pro finální predikci (T = 2024).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from data import KODY, PODSKUPINY, Data

OKNO_TREND = 15   # délka okna pro "krátký" trend výnosů (roky)
OKNO_KLIMA = 15   # z kolika posledních let se bere očekávané počasí
OKNO_CENY = 15    # okno pro odhad průměrné reálné ceny (reálné ceny od 90. let klesají)


@dataclass
class Kontext:
    """Data dostupná v okamžiku predikce (konec roku T)."""
    lp: pd.DataFrame        # log cena (Kč/t)
    ly: pd.DataFrame        # log výnos (kg/ha)
    pocasi: pd.DataFrame    # srážky, teplota
    makro: pd.DataFrame     # inflace, eur, cpi_index

    @classmethod
    def z_dat(cls, data: Data) -> "Kontext":
        lp = np.log(data.ceny).interpolate(limit_area="inside")  # 1 chybějící cena česneku (1998)
        ly = np.log(data.vynosy)
        return cls(lp, ly, data.pocasi, data.makro)

    def do(self, T: int) -> "Kontext":
        return Kontext(
            self.lp.loc[:T].copy(), self.ly.loc[:T].copy(),
            self.pocasi.loc[:T].copy(), self.makro.loc[:T].copy(),
        )


# --------------------------------------------------------------------------
# Ceny
# --------------------------------------------------------------------------

def _realna_log_cena(k: Kontext, T: int) -> pd.DataFrame:
    """ln(P_t / CPI_t) za posledních OKNO_CENY let: cena v cenách roku 2024.

    Okno je nutné, protože reálné ceny plodin od roku 1993 zhruba o polovinu klesly.
    Průměr přes celou historii by predikci táhl k cenám 90. let.
    """
    r = k.lp.sub(np.log(k.makro["cpi_index"].reindex(k.lp.index)), axis=0)
    return r.loc[T - OKNO_CENY + 1:T]


def _preved_na_nominal(realna_T1: pd.Series, k: Kontext, T: int) -> pd.Series:
    """Reálná predikce -> nominál. Očekávaná inflace na T+1 = inflace roku T (jediná známá)."""
    ocek_inflace = k.makro.loc[T, "inflace"] / 100
    return realna_T1 + np.log(k.makro.loc[T, "cpi_index"]) + np.log1p(ocek_inflace)


def cena_naivni(k: Kontext, T: int) -> pd.Series:
    """Benchmark: ln P_{T+1} = ln P_T (náhodná procházka)."""
    return k.lp.loc[T]


def cena_drift(k: Kontext, T: int) -> pd.Series:
    """Náhodná procházka s driftem: poslední hodnota + průměrná meziroční log-změna."""
    return k.lp.loc[T] + k.lp.diff().mean()


def cena_ar_sdileny(k: Kontext, T: int) -> pd.Series:
    """Panelový AR(1) na reálných log-cenách se sdíleným koeficientem phi.

    r_{i,t} - mu_i = phi * (r_{i,t-1} - mu_i) + e_{i,t}
    mu_i = dlouhodobý průměr reálné ceny plodiny i, phi je společné pro všechny plodiny.
    Sdílení phi přes 20 plodin dává ~600 pozorování místo ~30.
    """
    r = _realna_log_cena(k, T)
    mu = r.mean()
    odchylka = r - mu
    x = odchylka.shift(1).to_numpy().ravel()
    y = odchylka.to_numpy().ravel()
    ok = ~np.isnan(x) & ~np.isnan(y)
    phi = float(np.clip((x[ok] @ y[ok]) / (x[ok] @ x[ok]), 0.0, 1.0))
    realna_T1 = mu + phi * odchylka.loc[T]
    return _preved_na_nominal(realna_T1, k, T)


def cena_ar_plodina(k: Kontext, T: int) -> pd.Series:
    """AR(1) na reálných log-cenách, pro každou plodinu zvlášť (bez sdílení)."""
    r = _realna_log_cena(k, T)
    out = {}
    for kod in KODY:
        s = r[kod].dropna()
        x, y = s.shift(1).iloc[1:], s.iloc[1:]
        b, a = np.polyfit(x, y, 1)
        b = float(np.clip(b, 0.0, 1.0))
        a = y.mean() - b * x.mean()
        out[kod] = a + b * s.loc[T]
    return _preved_na_nominal(pd.Series(out), k, T)


def cena_ar_sdileny_kurz(k: Kontext, T: int) -> pd.Series:
    """Sdílený AR(1) + zpožděná změna kurzu CZK/EUR a zpožděná inflace.

    Delta r_{i,t} = a + (phi - 1)(r_{i,t-1} - mu_i) + b * Delta ln EUR_{t-1} + c * infl_{t-1}
    Makro vstupuje jen se zpožděním, protože hodnoty za T+1 v době plánování nejsou známé.
    """
    r = _realna_log_cena(k, T)
    mu = r.mean()
    odch = (r - mu).shift(1)
    d_eur = np.log(k.makro["eur"]).diff().shift(1).reindex(r.index)
    infl = (k.makro["inflace"] / 100).shift(1).reindex(r.index)
    radky = []
    for kod in KODY:
        radky.append(pd.DataFrame({
            "dy": r[kod].diff(), "odch": odch[kod], "deur": d_eur, "infl": infl,
        }))
    panel = pd.concat(radky).dropna()
    X = np.column_stack([np.ones(len(panel)), panel[["odch", "deur", "infl"]].to_numpy()])
    beta, *_ = np.linalg.lstsq(X, panel["dy"].to_numpy(), rcond=None)
    d_eur_T = np.log(k.makro.loc[T, "eur"] / k.makro.loc[T - 1, "eur"])
    infl_T = k.makro.loc[T, "inflace"] / 100
    odch_T = r.loc[T] - mu
    realna_T1 = r.loc[T] + beta[0] + beta[1] * odch_T + beta[2] * d_eur_T + beta[3] * infl_T
    return _preved_na_nominal(realna_T1, k, T)


def cena_kombinace(k: Kontext, T: int) -> pd.Series:
    """Průměr naivní predikce a sdíleného AR(1) (kombinace predikcí)."""
    return 0.5 * cena_naivni(k, T) + 0.5 * cena_ar_sdileny(k, T)


MODELY_CEN = {
    "naivni": cena_naivni,
    "drift": cena_drift,
    "ar_sdileny": cena_ar_sdileny,
    "ar_plodina": cena_ar_plodina,
    "ar_sdileny_kurz": cena_ar_sdileny_kurz,
    "kombinace": cena_kombinace,
}


# --------------------------------------------------------------------------
# Výnosy
# --------------------------------------------------------------------------

def _trend_ols(s: pd.Series, T: int) -> float:
    s = s.dropna()
    b, a = np.polyfit(s.index.to_numpy(float), s.to_numpy(), 1)
    return a + b * (T + 1)


def vynos_naivni(k: Kontext, T: int) -> pd.Series:
    """Benchmark: ln Y_{T+1} = ln Y_T."""
    return k.ly.loc[T]


def vynos_prumer5(k: Kontext, T: int) -> pd.Series:
    """Průměr posledních 5 let (tlumí náhodné výkyvy počasí)."""
    return k.ly.loc[T - 4:T].mean()


def vynos_trend(k: Kontext, T: int) -> pd.Series:
    """Lineární trend ln Y = a + b*t přes celou historii."""
    return pd.Series({kod: _trend_ols(k.ly[kod], T) for kod in KODY})


def vynos_trend15(k: Kontext, T: int) -> pd.Series:
    """Lineární trend jen z posledních 15 let (reaguje na zlomy, např. skleníková rajčata)."""
    ly = k.ly.loc[T - OKNO_TREND + 1:T]
    return pd.Series({kod: _trend_ols(ly[kod], T) for kod in KODY})


def vynos_trend15_robustni(k: Kontext, T: int) -> pd.Series:
    """Theil-Sen trend z posledních 15 let: medián sklonů, odolný vůči extrémním rokům."""
    ly = k.ly.loc[T - OKNO_TREND + 1:T]
    out = {}
    for kod in KODY:
        s = ly[kod].dropna()
        t = s.index.to_numpy(float)
        sklon, _, _, _ = stats.theilslopes(s.to_numpy(), t)
        usek = np.median(s.to_numpy() - sklon * t)
        out[kod] = usek + sklon * (T + 1)
    return pd.Series(out)


def _pocasi_std(k: Kontext) -> pd.DataFrame:
    p = k.pocasi
    return (p - p.mean()) / p.std()


def odhad_pocasi(k: Kontext, T: int) -> tuple[pd.DataFrame, pd.Series]:
    """Trend (15 let) + počasí se sdíleným efektem v rámci podskupiny plodin.

    ln Y_{i,t} = a_i + b_i * t + g_{s,1} * srazky_t + g_{s,2} * teplota_t + e

    Společná OLS regrese přes všechny plodiny podskupiny s, kde každá plodina má
    vlastní úrovňovou konstantu a_i a trend b_i, ale efekt počasí g_s je sdílený.
    Počítá se přes Frisch-Waugh-Lovellovu větu: z log-výnosů i z počasí se
    odstraní lineární trend (všechny plodiny mají stejné roky, takže stačí jeden
    detrend počasí) a g_s je OLS z očištěných dat. Bez očištění počasí o trend
    by se růst teploty (~0,13 °C/rok v 2010-2024) pletl s technologickým trendem.
    Vrací efekty počasí a koeficienty trendu (a_i, b_i) pro každou plodinu.
    """
    ly = k.ly.loc[T - OKNO_TREND + 1:T]
    w = _pocasi_std(k).loc[ly.index]
    t = ly.index.to_numpy(float)
    X_t = np.column_stack([np.ones_like(t), t])
    H = X_t @ np.linalg.pinv(X_t)                 # projekce na (1, t)
    w_rez = w.to_numpy() - H @ w.to_numpy()        # počasí očištěné o trend
    y_rez = {kod: ly[kod].to_numpy() - H @ ly[kod].to_numpy() for kod in KODY}
    gamma = {}
    for skupina in set(PODSKUPINY.values()):
        clenove = [kod for kod in KODY if PODSKUPINY[kod] == skupina]
        Y = np.concatenate([y_rez[kod] for kod in clenove])
        X = np.vstack([w_rez for _ in clenove])
        g, *_ = np.linalg.lstsq(X, Y, rcond=None)
        for kod in clenove:
            gamma[kod] = g
    koef = {}
    for kod in KODY:
        ocisteno = ly[kod].to_numpy() - w.to_numpy() @ gamma[kod]
        b, a = np.polyfit(t, ocisteno, 1)
        koef[kod] = (a, b)
    gamma_df = pd.DataFrame(gamma, index=["srazky", "teplota"]).T
    return gamma_df, pd.Series(koef)


def vynos_trend_pocasi(k: Kontext, T: int, pocasi_T1: pd.Series | None = None) -> pd.Series:
    """Predikce z modelu trend + počasí.

    Počasí roku T+1 v době plánování neznáme. Bez `pocasi_T1` se proto dosadí
    očekávané počasí: lineární trend standardizovaného počasí za posledních
    OKNO_KLIMA let prodloužený na T+1 (teplota roste, prostý průměr by ji podhodnotil).
    Parametr `pocasi_T1` slouží jen pro analýzu "co kdybychom počasí znali" (oracle).
    """
    gamma, koef = odhad_pocasi(k, T)
    w = _pocasi_std(k)
    if pocasi_T1 is None:
        okno = w.loc[T - OKNO_KLIMA + 1:T]
        t = okno.index.to_numpy(float)
        w_T1 = pd.Series({c: np.polyval(np.polyfit(t, okno[c].to_numpy(), 1), T + 1) for c in okno.columns})
    else:
        w_T1 = (pocasi_T1 - k.pocasi.mean()) / k.pocasi.std()
    return pd.Series({
        kod: koef[kod][0] + koef[kod][1] * (T + 1) + float(gamma.loc[kod].to_numpy() @ w_T1.to_numpy())
        for kod in KODY
    })


def vynos_prumer3(k: Kontext, T: int) -> pd.Series:
    """Průměr posledních 3 let (kandidát z druhého řešení skupiny)."""
    return k.ly.loc[T - 2:T].mean()


def vynos_kombinace(k: Kontext, T: int) -> pd.Series:
    """Průměr krátkého trendu a průměru posledních 5 let."""
    return 0.5 * vynos_trend15(k, T) + 0.5 * vynos_prumer5(k, T)


MODELY_VYNOSU = {
    "naivni": vynos_naivni,
    "prumer3": vynos_prumer3,
    "prumer5": vynos_prumer5,
    "trend": vynos_trend,
    "trend15": vynos_trend15,
    "trend15_robustni": vynos_trend15_robustni,
    "trend15_pocasi": vynos_trend_pocasi,
    "kombinace": vynos_kombinace,
}
