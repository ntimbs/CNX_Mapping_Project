#!/usr/bin/env python3
"""
Merge NFLIS drug types into the fentanyl precursor workbook.

Behavior:
- Loads BASE_DESCRIPTION values from NFLIS CSV.
- Matches those against chemical_name_list in the Excel workbook (case-insensitive).
- Adds a boolean match column for existing workbook rows.
- Appends new rows for NFLIS drug types not present in the workbook.
- Writes back to the same workbook and saves a timestamped backup copy first.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
NFLIS_FILE = BASE_DIR / "NFLIS_Drug_DQS_2026_03_03_13_26_55.csv"
WORKBOOK_FILE = BASE_DIR / "Fentanyl Data" / "Fentanyl_Precursor_List_Combined_with_schedule_dates.xlsx"
SHEET_NAME = "Sheet 1"
MATCH_COL = "nflis_base_description_match"


def normalize_name(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return " ".join(text.strip().lower().split())


def load_nflis_drug_names(path: Path) -> list[str]:
    use_cols = ["BASE_DESCRIPTION"]
    df = pd.read_csv(path, usecols=use_cols, dtype=str)
    names = [name for name in df["BASE_DESCRIPTION"].fillna("").astype(str).map(str.strip) if name]
    return sorted(set(names), key=lambda x: x.lower())


def main() -> None:
    if not NFLIS_FILE.exists():
        raise FileNotFoundError(f"NFLIS file not found: {NFLIS_FILE}")
    if not WORKBOOK_FILE.exists():
        raise FileNotFoundError(f"Workbook file not found: {WORKBOOK_FILE}")

    nflis_names = load_nflis_drug_names(NFLIS_FILE)
    nflis_norm_to_name = {normalize_name(name): name for name in nflis_names}
    nflis_norm_set = set(nflis_norm_to_name.keys())

    xls = pd.ExcelFile(WORKBOOK_FILE)
    if SHEET_NAME not in xls.sheet_names:
        raise ValueError(f"Sheet '{SHEET_NAME}' not found in {WORKBOOK_FILE}")

    df = pd.read_excel(WORKBOOK_FILE, sheet_name=SHEET_NAME)
    if "chemical_name_list" not in df.columns:
        raise ValueError("Workbook is missing required column: chemical_name_list")

    df = df.copy()
    df[MATCH_COL] = df["chemical_name_list"].map(lambda v: normalize_name(v) in nflis_norm_set)

    existing_norm = set(df["chemical_name_list"].map(normalize_name))
    missing_norm = sorted(nflis_norm_set - existing_norm)

    base_columns = list(df.columns)

    rows_to_add: list[dict[str, object]] = []
    for norm_name in missing_norm:
        canonical_name = nflis_norm_to_name[norm_name]
        new_row = {col: pd.NA for col in base_columns}

        if "source" in new_row:
            new_row["source"] = "NFLIS"
        if "chemical_name_list" in new_row:
            new_row["chemical_name_list"] = canonical_name
        if "sources_names" in new_row:
            new_row["sources_names"] = "NFLIS"
        if "num_pre" in new_row:
            new_row["num_pre"] = 0
        if "alt_names" in new_row:
            new_row["alt_names"] = pd.NA
        new_row[MATCH_COL] = True

        rows_to_add.append(new_row)

    if rows_to_add:
        df_out = pd.concat([df, pd.DataFrame(rows_to_add, columns=base_columns)], ignore_index=True)
    else:
        df_out = df

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = WORKBOOK_FILE.with_name(f"{WORKBOOK_FILE.stem}.backup_{ts}{WORKBOOK_FILE.suffix}")
    shutil.copy2(WORKBOOK_FILE, backup)

    with pd.ExcelWriter(WORKBOOK_FILE, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name=SHEET_NAME)

    matched_existing = int(df[MATCH_COL].sum())
    unmatched_existing = int((~df[MATCH_COL]).sum())
    print(f"Backup created: {backup}")
    print(f"NFLIS unique BASE_DESCRIPTION names: {len(nflis_names)}")
    print(f"Original workbook rows: {len(df)}")
    print(f"Existing workbook rows matched to NFLIS: {matched_existing}")
    print(f"Existing workbook rows without NFLIS match: {unmatched_existing}")
    print(f"New NFLIS rows appended: {len(rows_to_add)}")
    print(f"Final workbook rows: {len(df_out)}")


if __name__ == "__main__":
    main()
