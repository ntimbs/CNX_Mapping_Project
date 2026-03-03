#!/usr/bin/env python3
"""
Build a unified CBP + AMO fentanyl seizure dataset with normalized location fields.

Input files (expected in this directory):
- cbp_fentanyl_aor_monthly_2019_2026_dec.csv
- amo_fentanyl_branch_monthly_2019_2026_dec.csv

Output:
- cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv
"""

from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CBP_FILE = BASE_DIR / "cbp_fentanyl_aor_monthly_2019_2026_dec.csv"
AMO_FILE = BASE_DIR / "amo_fentanyl_branch_monthly_2019_2026_dec.csv"
OUTPUT_FILE = BASE_DIR / "cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv"


AOR_COORDS = {
    "ATLANTA FIELD OFFICE": (33.7490, -84.3880),
    "BALTIMORE FIELD OFFICE": (39.2904, -76.6122),
    "BIG BEND SECTOR": (30.3585, -103.6620),
    "BLAINE SECTOR": (48.9937, -122.7471),
    "BOSTON FIELD OFFICE": (42.3601, -71.0589),
    "BUFFALO FIELD OFFICE": (42.8864, -78.8784),
    "BUFFALO SECTOR": (42.8864, -78.8784),
    "CHICAGO FIELD OFFICE": (41.8781, -87.6298),
    "DEL RIO SECTOR": (29.3627, -100.8968),
    "DETROIT FIELD OFFICE": (42.3314, -83.0458),
    "DETROIT SECTOR": (42.3314, -83.0458),
    "EL CENTRO SECTOR": (32.7920, -115.5631),
    "EL PASO FIELD OFFICE": (31.7619, -106.4850),
    "EL PASO SECTOR": (31.7619, -106.4850),
    "GRAND FORKS SECTOR": (47.9253, -97.0329),
    "HAVRE SECTOR": (48.5500, -109.6841),
    "HOULTON SECTOR": (46.1262, -67.8398),
    "HOUSTON FIELD OFFICE": (29.7604, -95.3698),
    "LAREDO FIELD OFFICE": (27.5036, -99.5075),
    "LAREDO SECTOR": (27.5036, -99.5075),
    "LOS ANGELES FIELD OFFICE": (34.0522, -118.2437),
    "MIAMI FIELD OFFICE": (25.7617, -80.1918),
    "MIAMI SECTOR": (25.7617, -80.1918),
    "NEW ORLEANS FIELD OFFICE": (29.9511, -90.0715),
    "NEW ORLEANS SECTOR": (29.9511, -90.0715),
    "NEW YORK FIELD OFFICE": (40.7128, -74.0060),
    "PORTLAND FIELD OFFICE": (45.5152, -122.6784),
    "PRECLEARANCE FIELD OFFICE": (38.9072, -77.0369),
    "RAMEY SECTOR": (18.4274, -67.1541),
    "RIO GRANDE VALLEY SECTOR": (26.3017, -98.1633),
    "SAN DIEGO FIELD OFFICE": (32.7157, -117.1611),
    "SAN DIEGO SECTOR": (32.7157, -117.1611),
    "SAN FRANCISCO FIELD OFFICE": (37.7749, -122.4194),
    "SAN JUAN FIELD OFFICE": (18.4655, -66.1057),
    "SEATTLE FIELD OFFICE": (47.6062, -122.3321),
    "SPOKANE SECTOR": (47.6588, -117.4260),
    "SWANTON SECTOR": (44.9184, -73.1218),
    "TAMPA FIELD OFFICE": (27.9506, -82.4572),
    "TUCSON FIELD OFFICE": (32.2226, -110.9747),
    "TUCSON SECTOR": (32.2226, -110.9747),
    "YUMA SECTOR": (32.6927, -114.6277),
}

BRANCH_COORDS = {
    "AMOC Air And Marine Operations Center": (33.9533, -117.3962),
    "Bellingham Air Branch": (48.7519, -122.4787),
    "El Paso Air Branch": (31.7619, -106.4850),
    "Great Lakes Air And Marine Branch": (42.6070, -82.8360),
    "Ground Tactical Air Controller": (32.2226, -110.9747),
    "Houston Air And Marine Branch": (29.7604, -95.3698),
    "Jacksonville Air And Marine Branch": (30.3322, -81.6557),
    "Laredo Air Branch": (27.5036, -99.5075),
    "Manassas Air Branch": (38.7509, -77.4753),
    "Mc Allen Air And Marine Branch": (26.2034, -98.2300),
    "Mexico City IAC": (19.4326, -99.1332),
    "Miami Air And Marine Branch": (25.7617, -80.1918),
    "NASOC - Albuquerque": (35.0844, -106.6504),
    "NASOC - Grand Forks": (47.9253, -97.0329),
    "NASOC - San Angelo": (31.4638, -100.4370),
    "NASOC - Sierra Vista": (31.5455, -110.2773),
    "National Air Training Center Oklahoma City": (35.4676, -97.5164),
    "New Orleans Air And Marine Branch": (29.9511, -90.0715),
    "San Diego Air And Marine Branch": (32.7157, -117.1611),
    "Tucson Air Branch": (32.2226, -110.9747),
    "Yuma Air Branch": (32.6927, -114.6277),
}


def to_bool_text(value: str) -> str:
    text = (value or "").strip().lower()
    return "true" if text in {"true", "1", "yes"} else "false"


def to_int_str(value: str) -> str:
    try:
        return str(int(float((value or "0").strip() or 0)))
    except ValueError:
        return "0"


def to_float_str(value: str) -> str:
    try:
        return str(float((value or "0").strip() or 0))
    except ValueError:
        return "0.0"


def main() -> None:
    if not CBP_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {CBP_FILE}")
    if not AMO_FILE.exists():
        raise FileNotFoundError(f"Missing input file: {AMO_FILE}")

    rows_out: list[dict[str, str]] = []

    with CBP_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            location_name = (row.get("area_of_responsibility") or "").strip()
            lat, lon = AOR_COORDS.get(location_name, ("", ""))
            rows_out.append(
                {
                    "organization": "CBP",
                    "fiscal_year_label": (row.get("fiscal_year_label") or "").strip(),
                    "fiscal_year": (row.get("fiscal_year") or "").strip(),
                    "fiscal_year_is_partial": to_bool_text(row.get("fiscal_year_is_partial") or ""),
                    "month_abbr": (row.get("month_abbr") or "").strip().upper(),
                    "month_num": (row.get("month_num") or "").strip(),
                    "calendar_year": (row.get("calendar_year") or "").strip(),
                    "calendar_month_label": (row.get("calendar_month_label") or "").strip(),
                    "calendar_month_start": (row.get("calendar_month_start") or "").strip(),
                    "component": (row.get("component") or "").strip(),
                    "region": (row.get("region") or "").strip(),
                    "land_filter": (row.get("land_filter") or "").strip(),
                    "location_name": location_name,
                    "location_type": (row.get("aor_type") or "").strip(),
                    "drug_type": (row.get("drug_type") or "").strip(),
                    "count_of_event": to_int_str(row.get("count_of_event") or "0"),
                    "sum_qty_lbs": to_float_str(row.get("sum_qty_lbs") or "0"),
                    "lat": "" if lat == "" else str(lat),
                    "lon": "" if lon == "" else str(lon),
                    "source_dataset": CBP_FILE.name,
                    "source_file": (row.get("source_file") or "").strip(),
                }
            )

    with AMO_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            location_name = (row.get("branch") or "").strip()
            lat, lon = BRANCH_COORDS.get(location_name, ("", ""))
            rows_out.append(
                {
                    "organization": "AMO",
                    "fiscal_year_label": (row.get("fiscal_year_label") or "").strip(),
                    "fiscal_year": (row.get("fiscal_year") or "").strip(),
                    "fiscal_year_is_partial": to_bool_text(row.get("fiscal_year_is_partial") or ""),
                    "month_abbr": (row.get("month_abbr") or "").strip().upper(),
                    "month_num": (row.get("month_num") or "").strip(),
                    "calendar_year": (row.get("calendar_year") or "").strip(),
                    "calendar_month_label": (row.get("calendar_month_label") or "").strip(),
                    "calendar_month_start": (row.get("calendar_month_start") or "").strip(),
                    "component": (row.get("component") or "").strip(),
                    "region": (row.get("region") or "").strip(),
                    "land_filter": (row.get("land_filter") or "").strip(),
                    "location_name": location_name,
                    "location_type": (row.get("branch_type") or "").strip(),
                    "drug_type": (row.get("drug_type") or "").strip(),
                    "count_of_event": to_int_str(row.get("count_of_event") or "0"),
                    "sum_qty_lbs": to_float_str(row.get("sum_qty_lbs") or "0"),
                    "lat": "" if lat == "" else str(lat),
                    "lon": "" if lon == "" else str(lon),
                    "source_dataset": AMO_FILE.name,
                    "source_file": (row.get("source_file") or "").strip(),
                }
            )

    rows_out.sort(
        key=lambda r: (
            r["calendar_month_start"],
            r["organization"],
            r["component"],
            r["location_name"],
            r["land_filter"],
            r["region"],
        )
    )

    fieldnames = [
        "organization",
        "fiscal_year_label",
        "fiscal_year",
        "fiscal_year_is_partial",
        "month_abbr",
        "month_num",
        "calendar_year",
        "calendar_month_label",
        "calendar_month_start",
        "component",
        "region",
        "land_filter",
        "location_name",
        "location_type",
        "drug_type",
        "count_of_event",
        "sum_qty_lbs",
        "lat",
        "lon",
        "source_dataset",
        "source_file",
    ]

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {OUTPUT_FILE}")
    print(f"Rows: {len(rows_out)}")


if __name__ == "__main__":
    main()
