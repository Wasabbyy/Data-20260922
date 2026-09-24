"""Načtení a vyčištění dat pro osevní plán.

Všechna data jsou tvrdě oříznutá na roky <= POSLEDNI_ROK (2024). Soubory s počasím
a makrem obsahují i rok 2025, ten se ale nesmí dostat do predikce sezóny 2025.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

def _najdi_data() -> Path:
    """Data leží v kořeni repozitáře (o složku výš). Lokálně případně ve složce Data-20260922."""
    koren = Path(__file__).resolve().parent.parent
    for kandidat in (koren, koren / "Data-20260922"):
        if (kandidat / "plodiny.xlsx").exists():
            return kandidat
    raise FileNotFoundError("Nenalezen plodiny.xlsx v kořeni repozitáře")


DATA_DIR = _najdi_data()
POSLEDNI_ROK = 2024
PRVNI_ROK = 1993

# Pořadí a CPC kódy podle zadání (slide 5). Podskupina je naše agronomická
# pomůcka pro sdílení parametrů počasí mezi podobnými plodinami.
PLODINY = [
    # kód CSV,  kód xlsx, český název,           podskupina
    ("0111", 111.00, "Pšenice", "obiloviny"),
    ("0115", 115.00, "Ječmen", "obiloviny"),
    ("0116", 116.00, "Žito", "obiloviny"),
    ("0117", 117.00, "Oves", "obiloviny"),
    ("0112", 112.00, "Kukuřice na zrno", "obiloviny"),
    ("01443", 1443.00, "Řepka", "olejniny"),
    ("01445", 1445.00, "Slunečnice", "olejniny"),
    ("01441", 1441.00, "Len olejný", "olejniny"),
    ("01705", 1705.00, "Hrách na zrno", "okopaniny_luskoviny"),
    ("01801", 1801.00, "Cukrová řepa", "okopaniny_luskoviny"),
    ("01510", 1510.00, "Brambory", "okopaniny_luskoviny"),
    ("01212", 1212.00, "Zelí", "zelenina"),
    ("01251", 1251.00, "Mrkev a tuřín", "zelenina"),
    ("01213", 1213.00, "Květák a brokolice", "zelenina"),
    ("01231", 1231.00, "Papriky a chilli", "zelenina"),
    ("01232", 1232.00, "Okurky a nakládačky", "zelenina"),
    ("01252", 1252.00, "Zelený česnek", "zelenina"),
    ("01214", 1214.00, "Salát a čekanka", "zelenina"),
    ("01253.02", 1253.02, "Cibule a šalotka", "zelenina"),
    ("01234", 1234.00, "Rajčata", "zelenina"),
]
KODY = [p[0] for p in PLODINY]
NAZVY = {p[0]: p[2] for p in PLODINY}
PODSKUPINY = {p[0]: p[3] for p in PLODINY}


@dataclass
class Data:
    ceny: pd.DataFrame        # rok x plodina, Kč/t
    vynosy: pd.DataFrame      # rok x plodina, kg/ha
    plochy: pd.DataFrame      # rok x plodina, ha (národní sklizená plocha)
    naklady_2024: pd.Series   # plodina -> Kč/ha
    zelenina: pd.Series       # plodina -> bool
    pocasi: pd.DataFrame      # rok -> srazky (mm), teplota (°C)
    makro: pd.DataFrame       # rok -> inflace (% CPI), cpi_index (2024 = 1), eur (CZK/EUR)


def _faostat(soubor: str, element: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / soubor, dtype={"Item Code (CPC)": str})
    df = df[(df["Element"] == element) & df["Item Code (CPC)"].isin(KODY)]
    tab = df.pivot(index="Year", columns="Item Code (CPC)", values="Value")
    tab = tab.reindex(index=range(PRVNI_ROK, POSLEDNI_ROK + 1), columns=KODY).astype(float)
    return tab


def _plodiny_xlsx() -> pd.DataFrame:
    df = pd.read_excel(DATA_DIR / "plodiny.xlsx")
    mapa = {round(p[1], 2): p[0] for p in PLODINY}
    df["kod"] = df["Kód plodiny"].round(2).map(mapa)
    if df["kod"].isna().any():
        raise ValueError("Neznámý kód plodiny v plodiny.xlsx")
    return df.set_index("kod").loc[KODY]


def _pocasi() -> pd.DataFrame:
    s = pd.read_csv(DATA_DIR / "pocasi_srazky.csv")
    t = pd.read_csv(DATA_DIR / "pocasi_teplota.csv")
    s = s[s["Code"] == "CZE"].set_index("Year")["Annual precipitation"]
    t = t[t["Code"] == "CZE"].set_index("Year")["Average surface temperature"]
    out = pd.DataFrame({"srazky": s, "teplota": t})
    return out.loc[(out.index >= 1950) & (out.index <= POSLEDNI_ROK)]


def _makro() -> pd.DataFrame:
    raw = pd.read_excel(DATA_DIR / "makroekonomicke_ukazatele.xlsx", sheet_name="CR", header=None)
    roky = raw.iloc[4, 6:].astype(int).tolist()

    def radek(nazev: str, jednotka: str) -> pd.Series:
        maska = (raw[0].astype(str).str.strip() == nazev) & (raw[4].astype(str).str.strip() == jednotka)
        hodnoty = pd.to_numeric(raw.loc[maska].iloc[0, 6:], errors="coerce").tolist()
        return pd.Series(hodnoty, index=roky, dtype=float)

    makro = pd.DataFrame({
        "inflace": radek("CPI", "%, y/y, avrg."),
        "eur": radek("CZK/EUR", "avrg."),
    })
    makro = makro.loc[makro.index <= POSLEDNI_ROK]
    # Cenový index: rok 2024 = 1. Rok 1993 je první rok s cenami plodin.
    idx = (1 + makro["inflace"] / 100).loc[PRVNI_ROK + 1:].cumprod()
    idx = pd.concat([pd.Series({PRVNI_ROK: 1.0}), idx])
    makro["cpi_index"] = idx / idx.loc[POSLEDNI_ROK]
    return makro


def nacti() -> Data:
    xl = _plodiny_xlsx()
    data = Data(
        ceny=_faostat("plodiny_ceny.csv", "Producer Price (SLC/tonne)"),
        vynosy=_faostat("plodiny_vynosy.csv", "Yield"),
        plochy=_faostat("plodiny_vynosy.csv", "Area harvested"),
        naklady_2024=xl["Referenční náklady (Kč/ha)"].astype(float),
        zelenina=(xl["Produkční skupina"].str.contains("zelenin")),
        pocasi=_pocasi(),
        makro=_makro(),
    )
    for nazev in ("ceny", "vynosy", "plochy", "pocasi", "makro"):
        tab = getattr(data, nazev)
        assert tab.index.max() <= POSLEDNI_ROK, f"{nazev} obsahuje rok po {POSLEDNI_ROK}"
    return data


def marze_2024(data: Data) -> pd.DataFrame:
    """Dílčí úkol: M_i = P_i * Y_i / 1000 - C_i pro rok 2024."""
    p = data.ceny.loc[2024]
    y = data.vynosy.loc[2024]
    c = data.naklady_2024
    trzba = p * y / 1000
    return pd.DataFrame({
        "plodina": [NAZVY[k] for k in KODY],
        "cena_kc_t": p.values,
        "vynos_kg_ha": y.values,
        "trzba_kc_ha": trzba.values,
        "naklady_kc_ha": c.values,
        "marze_kc_ha": (trzba - c).values,
    }, index=pd.Index(KODY, name="kod"))


def naklady_v_roce(data: Data, rok: int) -> pd.Series:
    """Náklady přepočtené z roku 2024 do daného roku přes CPI (předpoklad)."""
    return data.naklady_2024 * data.makro.loc[rok, "cpi_index"]
