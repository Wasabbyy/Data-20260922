#!/usr/bin/env python3
"""Compute reference margins per hectare for selected crops in 2024.

Formula:
    Mi = (Pi * Yi / 1000) - Ci
where:
    Pi = price in Kč/t
    Yi = yield in kg/ha
    Ci = reference cost in Kč/ha
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"   # vstupní data jsou ve složce data/ v kořeni repozitáře


def normalize_crop_name(value: str) -> str:
    """Normalize English crop names so they match across source files."""
    text = str(value).strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_crop_costs() -> pd.DataFrame:
    excel_path = DATA_DIR / "plodiny.xlsx"
    df = pd.read_excel(excel_path, sheet_name="List1")
    required = ["Anglický název", "Referenční náklady (Kč/ha)"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected Excel columns: {missing}")

    df = df[required].copy()
    df.columns = ["crop", "cost_per_ha"]
    df["norm"] = df["crop"].map(normalize_crop_name)
    return df


def load_price_lookup() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "plodiny_ceny.csv")
    if "Year" not in df.columns or "Item" not in df.columns or "Value" not in df.columns:
        raise ValueError("Price CSV missing required columns: Year, Item, Value")

    df = df[df["Year"] == 2024].copy()
    df["norm"] = df["Item"].map(normalize_crop_name)
    df = df[["norm", "Value"]].dropna().drop_duplicates(subset="norm")
    df.columns = ["norm", "price_per_t"]
    return df


def load_yield_lookup() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "plodiny_vynosy.csv")
    if "Year" not in df.columns or "Item" not in df.columns or "Element" not in df.columns or "Value" not in df.columns:
        raise ValueError("Yield CSV missing required columns: Year, Item, Element, Value")

    df = df[(df["Year"] == 2024) & (df["Element"] == "Yield")].copy()
    df["norm"] = df["Item"].map(normalize_crop_name)
    df = df[["norm", "Value"]].dropna().drop_duplicates(subset="norm")
    df.columns = ["norm", "yield_kg_per_ha"]
    return df


def compute_margins() -> pd.DataFrame:
    crop_costs = load_crop_costs()
    prices = load_price_lookup().set_index("norm")
    yields = load_yield_lookup().set_index("norm")

    results = []
    for _, row in crop_costs.iterrows():
        key = row["norm"]
        if key not in prices.index or key not in yields.index:
            raise KeyError(f"No matching 2024 price/yield found for crop: {row['crop']}")

        price = float(prices.loc[key, "price_per_t"])
        yield_kg_per_ha = float(yields.loc[key, "yield_kg_per_ha"])
        cost_per_ha = float(str(row["cost_per_ha"]).replace(" ", "").replace(",", "."))

        margin = (price * yield_kg_per_ha / 1000.0) - cost_per_ha
        results.append(
            {
                "Plodina": row["crop"],
                "Cena_Pi_Kc_t": price,
                "Vynos_Yi_kg_ha": yield_kg_per_ha,
                "Naklady_Ci_Kc_ha": cost_per_ha,
                "Marze_Mi_Kc_ha": margin,
            }
        )

    out = pd.DataFrame(results)
    return out.sort_values("Marze_Mi_Kc_ha", ascending=False).reset_index(drop=True)


def main() -> None:
    results = compute_margins()

    output_csv = BASE_DIR / "marze_2024.csv"
    results.to_csv(output_csv, index=False, encoding="utf-8")

    print("Referenční marže na hektar v roce 2024")
    print(results.to_string(index=False, formatters={
        "Cena_Pi_Kc_t": lambda x: f"{x:,.1f}",
        "Vynos_Yi_kg_ha": lambda x: f"{x:,.1f}",
        "Naklady_Ci_Kc_ha": lambda x: f"{x:,.0f}",
        "Marze_Mi_Kc_ha": lambda x: f"{x:,.0f}",
    }))
    print(f"\nSaved CSV: {output_csv}")


if __name__ == "__main__":
    main()
