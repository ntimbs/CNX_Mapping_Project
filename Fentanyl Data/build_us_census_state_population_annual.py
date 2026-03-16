#!/usr/bin/env python3
"""Build annual state population file for overdose per-capita calculations.

Sources:
- ACS 1-year table B01003_001E (2015-2019, 2021-2024)
- 2020 Decennial PL table P1_001N (2020)

For 2025, this script carries forward 2024 ACS estimates so monthly 2025 overdose
rows can be normalized in the dashboard.
"""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

ACS_YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024]

STATE_FIPS_TO_ABBR = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_state_name(name: str) -> str:
    return name.replace(" (United States)", "").strip()


def main() -> None:
    rows = []

    for year in ACS_YEARS:
        url = f"https://api.census.gov/data/{year}/acs/acs1?get=NAME,B01003_001E&for=state:*"
        data = fetch_json(url)
        header = data[0]
        name_idx = header.index("NAME")
        pop_idx = header.index("B01003_001E")
        state_idx = header.index("state")

        for rec in data[1:]:
            fips = rec[state_idx]
            if fips not in STATE_FIPS_TO_ABBR:
                continue
            rows.append(
                {
                    "state_abbr": STATE_FIPS_TO_ABBR[fips],
                    "state_name": clean_state_name(rec[name_idx]),
                    "year": year,
                    "population": int(rec[pop_idx]),
                    "source_dataset": "ACS 1-year B01003_001E",
                    "source_url": url,
                    "source_note": "Annual estimate",
                }
            )

    dec_url = "https://api.census.gov/data/2020/dec/pl?get=NAME,P1_001N&for=state:*"
    dec_data = fetch_json(dec_url)
    header = dec_data[0]
    name_idx = header.index("NAME")
    pop_idx = header.index("P1_001N")
    state_idx = header.index("state")

    for rec in dec_data[1:]:
        fips = rec[state_idx]
        if fips not in STATE_FIPS_TO_ABBR:
            continue
        rows.append(
            {
                "state_abbr": STATE_FIPS_TO_ABBR[fips],
                "state_name": clean_state_name(rec[name_idx]),
                "year": 2020,
                "population": int(rec[pop_idx]),
                "source_dataset": "2020 Census PL P1_001N",
                "source_url": dec_url,
                "source_note": "Decennial census count",
            }
        )

    by_state_year = {(r["state_abbr"], r["year"]): r for r in rows}
    for abbr in sorted({r["state_abbr"] for r in rows}):
        base = by_state_year[(abbr, 2024)]
        rows.append(
            {
                "state_abbr": abbr,
                "state_name": base["state_name"],
                "year": 2025,
                "population": base["population"],
                "source_dataset": "Carry-forward from 2024 ACS",
                "source_url": base["source_url"],
                "source_note": "Used for 2025 monthly normalization",
            }
        )

    rows.sort(key=lambda r: (r["state_abbr"], r["year"]))

    out_path = Path("docs/us_census_state_population_annual_2015_2025.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "state_abbr",
                "state_name",
                "year",
                "population",
                "source_dataset",
                "source_url",
                "source_note",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
