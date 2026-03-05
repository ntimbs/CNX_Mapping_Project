#!/usr/bin/env python3
"""
Build a state-level opioid-indicator overdose monthly dataset from CDC VSRR data.

Input:
- VSRR_Provisional_Drug_Overdose_Death_Counts.csv

Output (written to both locations):
- Fentanyl Data/state_opioid_overdose_monthly_counts_estimated.csv
- docs/state_opioid_overdose_monthly_counts_estimated.csv

Notes:
- Keeps only selected opioid-related indicators (see TARGET_INDICATORS).
- Excludes non-state aggregates "US" and "YC".
- Source file values are 12 month-ending counts. Monthly values are estimated via
  a rolling-window deconvolution recurrence with a first-year seed assumption.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT_DIR / "VSRR_Provisional_Drug_Overdose_Death_Counts.csv"
OUTPUT_NAME = "state_opioid_overdose_monthly_counts_estimated.csv"
OUTPUT_STREAMLIT = Path(__file__).resolve().parent / OUTPUT_NAME
OUTPUT_DOCS = ROOT_DIR / "docs" / OUTPUT_NAME

TARGET_INDICATORS = {
    "Natural & semi-synthetic opioids (T40.2)",
    "Methadone (T40.3)",
    "Natural & semi-synthetic opioids, incl. methadone (T40.2, T40.3)",
    "Natural, semi-synthetic, & synthetic opioids, incl. methadone (T40.2-T40.4)",
    "Opioids (T40.0-T40.4,T40.6)",
    "Synthetic opioids, excl. methadone (T40.4)",
}
EXCLUDED_STATE_CODES = {"US", "YC"}

MONTH_TO_NUM = {
    "JANUARY": 1,
    "FEBRUARY": 2,
    "MARCH": 3,
    "APRIL": 4,
    "MAY": 5,
    "JUNE": 6,
    "JULY": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DECEMBER": 12,
}
MONTH_ABBR = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AUG",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def estimate_monthly_counts_from_rolling(rolling: pd.Series) -> tuple[pd.Series, int]:
    """
    Estimate monthly counts from a 12-month rolling series.

    Recurrence:
      x_t = y_t - y_{t-1} + x_{t-12}
    where:
      y_t = 12-month-ending count, x_t = monthly raw count estimate.

    Because the system is underdetermined by 12 initial values, we seed the first
    full-year block with y_seed / 12 using the earliest December value with data.
    """
    n = len(rolling)
    est = np.full(n, np.nan, dtype=float)
    negative_before_clip = 0

    dec_indices = [i for i in range(n) if pd.notna(rolling.iat[i]) and (i % 12 == 11)]
    if dec_indices:
        seed_idx = dec_indices[0]
    else:
        non_null = np.where(~rolling.isna().to_numpy())[0]
        if len(non_null) == 0:
            return pd.Series(est), negative_before_clip
        seed_idx = int(non_null[0])

    seed_value = float(rolling.iat[seed_idx]) / 12.0
    seed_start = max(0, seed_idx - 11)
    est[seed_start : seed_idx + 1] = seed_value

    for i in range(seed_idx + 1, n):
        if i - 12 < 0:
            continue
        if pd.notna(rolling.iat[i]) and pd.notna(rolling.iat[i - 1]) and pd.notna(est[i - 12]):
            est[i] = float(rolling.iat[i]) - float(rolling.iat[i - 1]) + float(est[i - 12])

    for i in range(seed_idx - 1, -1, -1):
        if i + 12 >= n:
            continue
        if pd.notna(rolling.iat[i + 1]) and pd.notna(rolling.iat[i]) and pd.notna(est[i + 12]):
            est[i] = float(est[i + 12]) - (float(rolling.iat[i + 1]) - float(rolling.iat[i]))

    negative_before_clip = int(np.sum((est < 0) & ~np.isnan(est)))
    est[(est < 0) & ~np.isnan(est)] = 0.0
    return pd.Series(est), negative_before_clip


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    required_cols = {
        "State",
        "State Name",
        "Year",
        "Month",
        "Period",
        "Indicator",
        "Data Value",
        "Predicted Value",
        "Percent Complete",
        "Percent Pending Investigation",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Input missing columns: {sorted(missing)}")

    df["variable"] = df["Indicator"].astype(str).str.strip()
    df = df[df["variable"].isin(TARGET_INDICATORS)].copy()
    df = df[~df["State"].astype(str).str.strip().isin(EXCLUDED_STATE_CODES)].copy()

    df["state_abbr"] = df["State"].astype(str).str.strip()
    df["state_name"] = df["State Name"].astype(str).str.strip()
    df["period"] = df["Period"].astype(str).str.strip()

    df["year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["month_num"] = (
        df["Month"]
        .astype(str)
        .str.strip()
        .str.upper()
        .map(MONTH_TO_NUM)
    )
    df = df.dropna(subset=["year", "month_num"]).copy()
    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df["month_abbr"] = df["month_num"].map(MONTH_ABBR)
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month_num"], day=1), errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    reported = to_num(df["Data Value"])
    predicted = to_num(df["Predicted Value"])
    df["rolling_12mo_count"] = reported.combine_first(predicted)
    df["source_value_type"] = np.where(reported.notna(), "data_value", np.where(predicted.notna(), "predicted_value", "missing"))

    df["percent_complete"] = to_num(df["Percent Complete"])
    df["percent_pending_investigation"] = to_num(df["Percent Pending Investigation"])

    result_rows: list[pd.DataFrame] = []
    negative_count_total = 0

    for (variable, state_abbr), group in df.groupby(["variable", "state_abbr"], sort=True):
        g = group.sort_values("date").drop_duplicates("date", keep="last").copy()

        monthly_index = pd.date_range(g["date"].min(), g["date"].max(), freq="MS")
        base = pd.DataFrame({"date": monthly_index})
        g = base.merge(
            g[
                [
                    "date",
                    "state_abbr",
                    "state_name",
                    "variable",
                    "period",
                    "rolling_12mo_count",
                    "source_value_type",
                    "percent_complete",
                    "percent_pending_investigation",
                ]
            ],
            on="date",
            how="left",
        )

        g["state_abbr"] = state_abbr
        g["state_name"] = g["state_name"].ffill().bfill()
        g["variable"] = variable
        g["period"] = g["period"].fillna("12 month-ending")
        g["source_value_type"] = g["source_value_type"].fillna("missing")

        monthly_est, negative_before_clip = estimate_monthly_counts_from_rolling(g["rolling_12mo_count"])
        negative_count_total += negative_before_clip
        g["count"] = monthly_est.round().astype("Int64")
        g["count_est_float"] = monthly_est

        g["year"] = g["date"].dt.year.astype(int)
        g["month_num"] = g["date"].dt.month.astype(int)
        g["month_abbr"] = g["month_num"].map(MONTH_ABBR)
        g["estimation_method"] = (
            "deconvolution_from_12mo_rolling_seeded_first_year_avg"
        )
        g["count_is_estimated"] = True

        result_rows.append(g)

    out = pd.concat(result_rows, ignore_index=True)
    out = out.dropna(subset=["count"]).copy()
    out["count"] = out["count"].astype(int)
    out = out[
        [
            "state_abbr",
            "state_name",
            "variable",
            "date",
            "year",
            "month_num",
            "month_abbr",
            "count",
            "count_est_float",
            "rolling_12mo_count",
            "source_value_type",
            "period",
            "percent_complete",
            "percent_pending_investigation",
            "count_is_estimated",
            "estimation_method",
        ]
    ].sort_values(["date", "state_abbr"])

    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    OUTPUT_STREAMLIT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOCS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_STREAMLIT, index=False)
    out.to_csv(OUTPUT_DOCS, index=False)

    print(f"Wrote {OUTPUT_STREAMLIT} ({len(out)} rows)")
    print(f"Wrote {OUTPUT_DOCS} ({len(out)} rows)")
    print(f"Rows with negative estimate before clip: {negative_count_total}")


if __name__ == "__main__":
    main()
