#!/usr/bin/env python3
"""Vypočítá referenční marži 20 plodin v roce 2024.

Postup:
1. Načte seznam plodin a jejich náklady z Excelu.
2. Z CSV vybere české ceny a výnosy za rok 2024.
3. Spojí údaje podle názvu plodiny a vypočítá M_i = P_i * Y_i / 1000 - C_i.

Jediným výstupem je soubor marze_2024.csv.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


# Vstupní data se mohou nacházet vedle skriptu nebo v pracovní složce.
ROK = 2024
VSTUPNI_SOUBORY = ("plodiny.xlsx", "plodiny_ceny.csv", "plodiny_vynosy.csv")


def najdi_slozku_se_vstupy() -> Path:
    """Hledá všechny vstupy nejprve vedle skriptu, potom v aktuální složce."""
    kandidati = dict.fromkeys((Path(__file__).resolve().parent, Path.cwd()))
    for slozka in kandidati:
        if all((slozka / soubor).is_file() for soubor in VSTUPNI_SOUBORY):
            return slozka
    seznam = ", ".join(VSTUPNI_SOUBORY)
    raise FileNotFoundError(
        f"Vstupní soubory ({seznam}) musí být vedle skriptu nebo v aktuální složce."
    )


SLOZKA = najdi_slozku_se_vstupy()


# ---------------------------------------------------------------------------
# Párování názvů plodin napříč Excelovým a CSV zdrojem
# ---------------------------------------------------------------------------
def normalizuj_nazev(hodnota: object) -> str:
    """Sjednotí názvy lišící se velikostí písmen, diakritikou či interpunkcí."""
    text = str(hodnota).strip().lower().replace("&", " and ")
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(znak for znak in text if not unicodedata.combining(znak))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def jedinecny_slovnik(tab: pd.DataFrame, nazev_sloupce: str, hodnota_sloupce: str,
                      cilove_klice: set[str], zdroj: str) -> pd.DataFrame:
    """Připraví jednu číselnou hodnotu na plodinu a odmítne nejednoznačná data."""
    vyber = tab[[nazev_sloupce, hodnota_sloupce]].copy()
    vyber["klic"] = vyber[nazev_sloupce].map(normalizuj_nazev)

    # Necháme jen vybrané plodiny; ostatní záznamy nejsou součástí zadání.
    vyber = vyber[vyber["klic"].isin(cilove_klice)][["klic", hodnota_sloupce]]

    # Duplicitní záznam nesmíme svévolně vybrat, mohl by změnit výsledek.
    if vyber["klic"].duplicated().any():
        raise ValueError(f"Zdroj {zdroj} obsahuje více hodnot pro stejnou plodinu.")

    # CSV může číselnou hodnotu obsahovat jako text; převedeme ji na číslo.
    vyber[hodnota_sloupce] = pd.to_numeric(vyber[hodnota_sloupce], errors="coerce")
    if vyber[hodnota_sloupce].isna().any():
        raise ValueError(f"Zdroj {zdroj} obsahuje chybějící nebo nečíselnou hodnotu.")
    return vyber.rename(columns={hodnota_sloupce: zdroj})


# ---------------------------------------------------------------------------
# Výpočet marží za požadovaný rok
# ---------------------------------------------------------------------------
def vypocitej_marze() -> pd.DataFrame:
    """Spojí zdroje podle plodiny a použije M_i = P_i * Y_i / 1000 - C_i."""
    # Ci: referenční náklady a seznam plodin jsou v listu List1 souboru Excel.
    excel = pd.read_excel(SLOZKA / "plodiny.xlsx", sheet_name="List1")
    pozadovane_sloupce = ["Anglický název", "Referenční náklady (Kč/ha)"]
    if any(sloupec not in excel.columns for sloupec in pozadovane_sloupce):
        raise ValueError("V plodiny.xlsx chybí očekávaný název plodiny nebo náklady.")

    # Zachováme původní anglický název pro výslednou tabulku a přejmenujeme Ci.
    naklady = excel[pozadovane_sloupce].copy()
    naklady.columns = ["Plodina", "Naklady_Ci_Kc_ha"]
    naklady["klic"] = naklady["Plodina"].map(normalizuj_nazev)

    # Náklady zůstanou číselné i tehdy, pokud jsou v Excelu uložené jako text.
    naklady["Naklady_Ci_Kc_ha"] = pd.to_numeric(
        naklady["Naklady_Ci_Kc_ha"].astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    if len(naklady) != 20 or naklady["klic"].duplicated().any() or naklady["Naklady_Ci_Kc_ha"].isna().any():
        raise ValueError("Seznam plodin musí obsahovat právě 20 jedinečných plodin s platnými náklady.")
    klice = set(naklady["klic"])

    # Pi: cena musí být za požadovaný rok, pro Česko a v Kč za tunu.
    ceny_raw = pd.read_csv(SLOZKA / "plodiny_ceny.csv")
    sloupce_cen = {"Year", "Area", "Element", "Item", "Value"}
    if not sloupce_cen.issubset(ceny_raw.columns):
        raise ValueError("V plodiny_ceny.csv chybí požadované sloupce.")
    ceny_raw = ceny_raw[
        (ceny_raw["Year"] == ROK)
        & (ceny_raw["Area"] == "Czechia")
        & (ceny_raw["Element"] == "Producer Price (SLC/tonne)")
    ]
    ceny = jedinecny_slovnik(ceny_raw, "Item", "Value", klice, "Cena_Pi_Kc_t")

    # Yi: vybíráme stejný rok a záznam Yield, jehož jednotkou je kg/ha.
    vynosy_raw = pd.read_csv(SLOZKA / "plodiny_vynosy.csv")
    sloupce_vynosu = {"Year", "Area", "Element", "Item", "Value"}
    if not sloupce_vynosu.issubset(vynosy_raw.columns):
        raise ValueError("V plodiny_vynosy.csv chybí požadované sloupce.")
    vynosy_raw = vynosy_raw[
        (vynosy_raw["Year"] == ROK)
        & (vynosy_raw["Area"] == "Czechia")
        & (vynosy_raw["Element"] == "Yield")
    ]
    vynosy = jedinecny_slovnik(vynosy_raw, "Item", "Value", klice, "Vynos_Yi_kg_ha")

    # Spojení one-to-one zaručí právě jeden náklad, cenu a výnos na plodinu.
    vysledek = naklady.merge(ceny, on="klic", how="left", validate="one_to_one")
    vysledek = vysledek.merge(vynosy, on="klic", how="left", validate="one_to_one")
    if len(vysledek) != 20 or vysledek[["Cena_Pi_Kc_t", "Vynos_Yi_kg_ha"]].isna().any().any():
        raise ValueError("Pro některou z 20 plodin chybí cena nebo výnos za rok 2024.")

    # P je v Kč/t a Y v kg/ha: dělením 1000 převedeme tržbu na Kč/ha.
    # Od tržby odečteme Ci a získáme požadovanou marži Mi v Kč/ha.
    vysledek["Marze_Mi_Kc_ha"] = (
        vysledek["Cena_Pi_Kc_t"] * vysledek["Vynos_Yi_kg_ha"] / 1000
        - vysledek["Naklady_Ci_Kc_ha"]
    ).round(2)
    return vysledek[["Plodina", "Marze_Mi_Kc_ha"]].sort_values(
        "Marze_Mi_Kc_ha", ascending=False
    ).reset_index(drop=True)


def main() -> None:
    vysledek = vypocitej_marze()
    # Vytvoříme jedinou odpověď na zadání.
    vysledek.to_csv(SLOZKA / "marze_2024.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
