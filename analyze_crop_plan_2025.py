#!/usr/bin/env python3
"""Reproducible 2025 crop forecast, risk scenarios, and crop-plan optimization.

The historical files contain 1993-2024 observations.  Because only 32 annual
observations are available, the forecasting method deliberately compares a
linear trend with a naive last-value baseline and selects the better method by
expanding-window backtesting.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing


BASE_DIR = Path(__file__).resolve().parent
TARGET_YEAR = 2025
TOTAL_AREA_HA = 1_000.0
VEGETABLE_LIMIT_HA = 200.0


def normalize(value: object) -> str:
    text = str(value).strip().lower().replace("&", " and ")
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def load_crops() -> pd.DataFrame:
    source = pd.read_excel(BASE_DIR / "plodiny.xlsx", sheet_name="List1")
    if source.shape[1] < 5:
        raise ValueError("plodiny.xlsx must contain five crop metadata columns")
    result = source.iloc[:, :5].copy()
    result.columns = ["cpc", "crop", "crop_cz", "group", "cost_per_ha"]
    result["norm"] = result["crop"].map(normalize)
    result["cost_per_ha"] = pd.to_numeric(result["cost_per_ha"], errors="raise")
    result["is_vegetable"] = result["group"].map(normalize).str.contains("zelenin")
    return result


def load_series(file_name: str, element: str | None = None) -> pd.DataFrame:
    source = pd.read_csv(BASE_DIR / file_name)
    required = {"Item", "Year", "Value"}
    if element is not None:
        required.add("Element")
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"{file_name} missing columns: {sorted(missing)}")
    if element is not None:
        source = source[source["Element"].eq(element)]
    result = source.loc[:, ["Item", "Year", "Value"]].copy()
    result["norm"] = result["Item"].map(normalize)
    result["Year"] = pd.to_numeric(result["Year"], errors="raise").astype(int)
    result["Value"] = pd.to_numeric(result["Value"], errors="coerce")
    return result.dropna(subset=["Value"]).groupby(["norm", "Year"], as_index=False)["Value"].mean()


def _arima_predict(train: np.ndarray, steps: int, order: tuple[int, int, int]) -> float:
    fitted = ARIMA(train, order=order, trend="t" if order[1] == 0 else None).fit()
    return float(fitted.forecast(steps=steps)[-1])


def _holt_predict(train: np.ndarray, steps: int, damped: bool) -> float:
    fitted = ExponentialSmoothing(
        train, trend="add", damped_trend=damped, initialization_method="estimated"
    ).fit(optimized=True)
    return float(fitted.forecast(steps)[-1])


def forecast(values: pd.DataFrame, target_year: int) -> tuple[float, float, str, float]:
    """Return forecast, interval half-width, selected method, and backtest MAE."""
    values = values.sort_values("Year")
    y = values["Value"].to_numpy(dtype=float)
    years = values["Year"].to_numpy(dtype=float)
    if len(y) < 2:
        raise ValueError("At least two observations are required for forecasting")

    predictions: list[float] = []
    actuals: list[float] = []
    arima_orders = ((1, 1, 0), (0, 1, 1), (1, 0, 0), (1, 1, 1))
    candidate_errors: dict[str, list[float]] = {"trend": [], "naive": []}
    candidate_errors.update({f"arima{order}": [] for order in arima_orders})
    candidate_errors.update({"holt": [], "holt_damped": []})
    for i in range(10, len(y)):
        train_y, train_x = y[:i], years[:i]
        trend = np.polyfit(train_x, train_y, 1)
        trend_prediction = float(np.polyval(trend, years[i]))
        candidate_errors["trend"].append(abs(trend_prediction - y[i]))
        candidate_errors["naive"].append(abs(y[i - 1] - y[i]))
        for order in arima_orders:
            try:
                prediction = _arima_predict(train_y, 1, order)
            except (ValueError, np.linalg.LinAlgError):
                prediction = np.nan
            if np.isfinite(prediction):
                candidate_errors[f"arima{order}"].append(abs(prediction - y[i]))
        for damped in (False, True):
            method_name = "holt_damped" if damped else "holt"
            try:
                prediction = _holt_predict(train_y, 1, damped)
            except (ValueError, np.linalg.LinAlgError):
                prediction = np.nan
            if np.isfinite(prediction):
                candidate_errors[method_name].append(abs(prediction - y[i]))
        predictions.append(trend_prediction)
        actuals.append(y[i])
    maes = {
        method: float(np.mean(errors)) if errors else np.inf
        for method, errors in candidate_errors.items()
    }
    method = min(maes, key=maes.get)
    selected_mae = maes[method]
    if method == "trend":
        coefficients = np.polyfit(years, y, 1)
        point = float(np.polyval(coefficients, target_year))
        residuals = y - np.polyval(coefficients, years)
    elif method == "naive":
        point = float(y[-1])
        residuals = np.diff(y)
    elif method in ("holt", "holt_damped"):
        damped = method == "holt_damped"
        point = _holt_predict(y, 1, damped)
        fitted = ExponentialSmoothing(
            y, trend="add", damped_trend=damped, initialization_method="estimated"
        ).fit(optimized=True)
        residuals = np.asarray(fitted.resid, dtype=float)
    else:
        order = next(order for order in arima_orders if method == f"arima{order}")
        point = _arima_predict(y, 1, order)
        fitted = ARIMA(y, order=order, trend="t" if order[1] == 0 else None).fit()
        residuals = np.asarray(fitted.resid, dtype=float)
    half_width = max(1.96 * float(np.std(residuals, ddof=1)), selected_mae, abs(point) * 0.05)
    return max(point, 0.0), half_width, method, selected_mae


def build_forecasts(crops: pd.DataFrame) -> pd.DataFrame:
    prices = load_series("plodiny_ceny.csv")
    yields = load_series("plodiny_vynosy.csv", "Yield")
    rows: list[dict[str, object]] = []
    for _, crop in crops.iterrows():
        price_history = prices[prices["norm"].eq(crop["norm"])]
        yield_history = yields[yields["norm"].eq(crop["norm"])]
        if price_history.empty or yield_history.empty:
            raise KeyError(f"Missing price or yield history for {crop['crop']}")
        price, price_error, price_method, price_mae = forecast(price_history, TARGET_YEAR)
        yield_value, yield_error, yield_method, yield_mae = forecast(yield_history, TARGET_YEAR)
        rows.append(
            {
                "Plodina": crop["crop"],
                "Plodina_CZ": crop["crop_cz"],
                "CPC": crop["cpc"],
                "Skupina": crop["group"],
                "Naklady_2024_Kc_ha": crop["cost_per_ha"],
                "Cena_predikce_2025_Kc_t": price,
                "Cena_dolni_95_Kc_t": max(price - price_error, 0.0),
                "Cena_horni_95_Kc_t": price + price_error,
                "Vynos_predikce_2025_kg_ha": yield_value,
                "Vynos_dolni_95_kg_ha": max(yield_value - yield_error, 0.0),
                "Vynos_horni_95_kg_ha": yield_value + yield_error,
                "Metoda_ceny": price_method,
                "Metoda_vynosu": yield_method,
                "MAE_ceny_Kc_t": price_mae,
                "MAE_vynosu_kg_ha": yield_mae,
            }
        )
    result = pd.DataFrame(rows)
    result["Marze_ocekavana_Kc_ha"] = (
        result["Cena_predikce_2025_Kc_t"] * result["Vynos_predikce_2025_kg_ha"] / 1000
        - result["Naklady_2024_Kc_ha"]
    )
    result["Marze_neprizniva_Kc_ha"] = (
        result["Cena_dolni_95_Kc_t"] * result["Vynos_dolni_95_kg_ha"] / 1000
        - result["Naklady_2024_Kc_ha"]
    )
    result["Marze_prizniva_Kc_ha"] = (
        result["Cena_horni_95_Kc_t"] * result["Vynos_horni_95_kg_ha"] / 1000
        - result["Naklady_2024_Kc_ha"]
    )
    result["Riziko_downside_Kc_ha"] = (
        result["Marze_ocekavana_Kc_ha"] - result["Marze_neprizniva_Kc_ha"]
    ).clip(lower=0)
    return result


def optimize(
    forecasts: pd.DataFrame, risk_aversion: float, max_crop_share: float | None = None
) -> pd.DataFrame:
    score = forecasts["Marze_ocekavana_Kc_ha"] - risk_aversion * forecasts["Riziko_downside_Kc_ha"]
    vegetable = forecasts["Skupina"].map(normalize).str.contains("zelenin").astype(float).to_numpy()
    constraints = np.vstack([vegetable, np.ones(len(forecasts))])
    if max_crop_share is None:
        bounds = [(0, None) for _ in range(len(forecasts))]
    else:
        if not 0 < max_crop_share <= 1:
            raise ValueError("max_crop_share must be between 0 and 1")
        bounds = [(0, TOTAL_AREA_HA * max_crop_share) for _ in range(len(forecasts))]
    result = linprog(
        c=-score.to_numpy(),
        A_ub=constraints,
        b_ub=np.array([VEGETABLE_LIMIT_HA, TOTAL_AREA_HA]),
        A_eq=np.ones((1, len(forecasts))),
        b_eq=np.array([TOTAL_AREA_HA]),
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Crop-plan optimization failed: {result.message}")
    plan = forecasts[["Plodina", "Plodina_CZ", "CPC", "Skupina"]].copy()
    plan["Plocha_ha"] = result.x
    plan["Podil_pct"] = result.x / TOTAL_AREA_HA * 100
    plan["Ocekavana_marze_Kc_ha"] = forecasts["Marze_ocekavana_Kc_ha"]
    plan["Celkem_ocekavana_marze_Kc"] = result.x * forecasts["Marze_ocekavana_Kc_ha"]
    plan["Riziko_downside_Kc_ha"] = forecasts["Riziko_downside_Kc_ha"]
    return plan[plan["Plocha_ha"] > 1e-8].sort_values("Plocha_ha", ascending=False).reset_index(drop=True)


def optimize_robust(forecasts: pd.DataFrame, max_crop_share: float | None = None) -> pd.DataFrame:
    """Maximize the worst-case total margin over the three explicit scenarios."""
    scenario_margins = forecasts[
        ["Marze_neprizniva_Kc_ha", "Marze_ocekavana_Kc_ha", "Marze_prizniva_Kc_ha"]
    ].to_numpy(dtype=float)
    vegetable = forecasts["Skupina"].map(normalize).str.contains("zelenin").astype(float).to_numpy()
    # Variables are crop areas followed by z, the guaranteed total margin.
    objective = np.r_[np.zeros(len(forecasts)), -1.0]
    scenario_rows = [np.r_[-scenario_margins[:, index], 1.0] for index in range(3)]
    constraints = np.vstack(
        [
            np.r_[vegetable, 0.0],
            np.r_[np.ones(len(forecasts)), 0.0],
            *scenario_rows,
        ]
    )
    upper_bounds = [(0, None)] * len(forecasts) + [(None, None)]
    if max_crop_share is not None:
        if not 0 < max_crop_share <= 1:
            raise ValueError("max_crop_share must be between 0 and 1")
        upper_bounds = [(0, TOTAL_AREA_HA * max_crop_share)] * len(forecasts) + [(None, None)]
    result = linprog(
        c=objective,
        A_ub=constraints,
        b_ub=np.r_[VEGETABLE_LIMIT_HA, TOTAL_AREA_HA, np.zeros(3)],
        A_eq=np.r_[np.ones(len(forecasts)), 0.0][None, :],
        b_eq=[TOTAL_AREA_HA],
        bounds=upper_bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Robust crop-plan optimization failed: {result.message}")
    plan = forecasts[["Plodina", "Plodina_CZ", "CPC", "Skupina"]].copy()
    plan["Plocha_ha"] = result.x[:-1]
    plan["Podil_pct"] = result.x[:-1] / TOTAL_AREA_HA * 100
    plan["Ocekavana_marze_Kc_ha"] = forecasts["Marze_ocekavana_Kc_ha"]
    plan["Celkem_ocekavana_marze_Kc"] = result.x[:-1] * forecasts["Marze_ocekavana_Kc_ha"]
    plan["Marze_neprizniva_Kc_ha"] = forecasts["Marze_neprizniva_Kc_ha"]
    plan["Marze_prizniva_Kc_ha"] = forecasts["Marze_prizniva_Kc_ha"]
    return plan[plan["Plocha_ha"] > 1e-8].sort_values("Plocha_ha", ascending=False).reset_index(drop=True)


def main() -> None:
    crops = load_crops()
    forecasts = build_forecasts(crops)
    forecasts.to_csv(BASE_DIR / "predikce_2025.csv", index=False, encoding="utf-8-sig")

    primary = optimize(forecasts, risk_aversion=0.5)
    primary.to_csv(BASE_DIR / "osevni_plan_2025.csv", index=False, encoding="utf-8-sig")
    diversified = optimize(forecasts, risk_aversion=0.5, max_crop_share=0.25)
    diversified.to_csv(
        BASE_DIR / "osevni_plan_2025_diverzifikovany.csv", index=False, encoding="utf-8-sig"
    )
    diversified_200 = optimize(forecasts, risk_aversion=0.5, max_crop_share=0.20)
    diversified_200.to_csv(
        BASE_DIR / "osevni_plan_2025_diverzifikovany_200ha.csv",
        index=False,
        encoding="utf-8-sig",
    )
    robust = optimize_robust(forecasts, max_crop_share=0.20)
    robust.to_csv(
        BASE_DIR / "osevni_plan_2025_robustni.csv", index=False, encoding="utf-8-sig"
    )

    sensitivity_rows = []
    for risk_aversion in (0.0, 0.25, 0.5, 1.0):
        plan = optimize(forecasts, risk_aversion)
        for _, row in plan.iterrows():
            sensitivity_rows.append(
                {
                    "Lambda": risk_aversion,
                    "Plodina": row["Plodina"],
                    "Plocha_ha": row["Plocha_ha"],
                    "Celkem_ocekavana_marze_Kc": row["Celkem_ocekavana_marze_Kc"],
                }
            )
    pd.DataFrame(sensitivity_rows).to_csv(
        BASE_DIR / "citlivost_osevniho_planu_2025.csv", index=False, encoding="utf-8-sig"
    )

    vegetable_area = primary.loc[
        primary["Skupina"].map(normalize).str.contains("zelenin"), "Plocha_ha"
    ].sum()
    total_margin = primary["Celkem_ocekavana_marze_Kc"].sum()
    print(f"Očekávaná marže farmy: {total_margin:,.0f} Kč")
    print(f"Očekávaná marže na ha: {total_margin / TOTAL_AREA_HA:,.0f} Kč/ha")
    print(f"Plocha zeleniny: {vegetable_area:,.1f} ha ({vegetable_area / 10:,.1f} %)")
    print(
        "Výstupy: predikce_2025.csv, osevni_plan_2025.csv, "
        "osevni_plan_2025_diverzifikovany.csv, citlivost_osevniho_planu_2025.csv"
        ", osevni_plan_2025_diverzifikovany_200ha.csv, osevni_plan_2025_robustni.csv"
    )


if __name__ == "__main__":
    main()
