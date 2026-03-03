#!/usr/bin/env python3
"""
Build a cleaned AMO fentanyl dataset from AMO drug seizure source files.

Input files (expected in this directory):
- amo-drug-seizures-fy19-fy22.csv
- amo-drug-seizures-fy23-fy26-dec.csv

Output:
- amo_fentanyl_branch_monthly_2019_2026_dec.csv

Notes:
- Keeps only rows where Drug Type == Fentanyl.
- Converts US federal fiscal year month to calendar month/year:
  FY month Oct-Dec => calendar year FY-1
  FY month Jan-Sep => calendar year FY
"""

from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILES = [
    BASE_DIR / "amo-drug-seizures-fy19-fy22.csv",
    BASE_DIR / "amo-drug-seizures-fy23-fy26-dec.csv",
]
OUTPUT_FILE = BASE_DIR / "amo_fentanyl_branch_monthly_2019_2026_dec.csv"

MONTH_TO_NUM = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def parse_fy_label(label: str) -> tuple[int, bool]:
    raw = (label or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < 4:
        raise ValueError(f"Could not parse fiscal year from FY label: {label!r}")
    fiscal_year = int(digits[:4])
    is_partial = "FYTD" in raw.upper()
    return fiscal_year, is_partial


def month_to_calendar_year(fiscal_year: int, month_num: int) -> int:
    if month_num >= 10:
        return fiscal_year - 1
    return fiscal_year


def infer_branch_type(branch_name: str) -> str:
    name = (branch_name or "").upper()
    if "AIR BRANCH" in name:
        return "Air Branch"
    if "MARINE BRANCH" in name:
        return "Marine Branch"
    if "AIR AND MARINE BRANCH" in name:
        return "Air and Marine Branch"
    if "NASOC" in name:
        return "NASOC"
    if "CENTER" in name:
        return "Center"
    if "HQ" in name:
        return "HQ"
    return "Other"


def main() -> None:
    rows_out = []

    for file_path in INPUT_FILES:
        if not file_path.exists():
            raise FileNotFoundError(f"Missing input file: {file_path}")

        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {
                "FY",
                "Month (abbv)",
                "Component",
                "Region",
                "Land Filter",
                "Branch",
                "Drug Type",
                "Count of Event",
                "Sum Qty (lbs)",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{file_path.name} missing columns: {sorted(missing)}")

            for row in reader:
                drug = (row.get("Drug Type") or "").strip()
                if drug != "Fentanyl":
                    continue

                fy_label = (row.get("FY") or "").strip()
                month_abbr = (row.get("Month (abbv)") or "").strip().upper()
                if month_abbr not in MONTH_TO_NUM:
                    continue

                fiscal_year, fiscal_year_is_partial = parse_fy_label(fy_label)
                month_num = MONTH_TO_NUM[month_abbr]
                calendar_year = month_to_calendar_year(fiscal_year, month_num)
                calendar_month_start = f"{calendar_year:04d}-{month_num:02d}-01"
                calendar_month_label = f"{calendar_year:04d}-{month_num:02d}"

                count_event = float((row.get("Count of Event") or "0").strip() or 0)
                qty_lbs = float((row.get("Sum Qty (lbs)") or "0").strip() or 0)
                branch = (row.get("Branch") or "").strip()

                rows_out.append(
                    {
                        "fiscal_year_label": fy_label,
                        "fiscal_year": fiscal_year,
                        "fiscal_year_is_partial": str(fiscal_year_is_partial).lower(),
                        "month_abbr": month_abbr,
                        "month_num": month_num,
                        "calendar_year": calendar_year,
                        "calendar_month_label": calendar_month_label,
                        "calendar_month_start": calendar_month_start,
                        "component": (row.get("Component") or "").strip(),
                        "region": (row.get("Region") or "").strip(),
                        "land_filter": (row.get("Land Filter") or "").strip(),
                        "branch": branch,
                        "branch_type": infer_branch_type(branch),
                        "drug_type": drug,
                        "count_of_event": int(round(count_event)),
                        "sum_qty_lbs": qty_lbs,
                        "source_file": file_path.name,
                    }
                )

    rows_out.sort(
        key=lambda r: (
            r["calendar_month_start"],
            r["component"],
            r["branch"],
            r["land_filter"],
            r["region"],
        )
    )

    fieldnames = list(rows_out[0].keys()) if rows_out else []
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {OUTPUT_FILE}")
    print(f"Rows: {len(rows_out)}")


if __name__ == "__main__":
    main()
