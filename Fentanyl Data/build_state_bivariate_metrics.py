#!/usr/bin/env python3
"""Build a combined 50-state metrics table for the bivariate map dashboard.

The output is a single per-state CSV that merges state-level metrics used across
existing dashboards:
- CDC/VSRR-derived monthly overdose estimates
- Fentanyl-specific law counts
- NFLIS fentanyl and fentanyl-related reports
- CNX receiver/sender shipment aggregates (HS6 and chemical-match subsets)
- Census annual population
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


# U.S. Census subregions/divisions mapped to 50 states.
SUBREGION_TO_STATES = {
    "New England": ["CT", "ME", "MA", "NH", "RI", "VT"],
    "Middle Atlantic": ["NJ", "NY", "PA"],
    "East North Central": ["IL", "IN", "MI", "OH", "WI"],
    "West North Central": ["IA", "KS", "MN", "MO", "NE", "ND", "SD"],
    "South Atlantic": ["DE", "FL", "GA", "MD", "NC", "SC", "VA", "WV"],
    "East South Central": ["AL", "KY", "MS", "TN"],
    "West South Central": ["AR", "LA", "OK", "TX"],
    "Mountain": ["AZ", "CO", "ID", "MT", "NV", "NM", "UT", "WY"],
    "Pacific": ["AK", "CA", "HI", "OR", "WA"],
}

SUBREGION_TO_REGION = {
    "New England": "Northeast",
    "Middle Atlantic": "Northeast",
    "East North Central": "Midwest",
    "West North Central": "Midwest",
    "South Atlantic": "South",
    "East South Central": "South",
    "West South Central": "South",
    "Mountain": "West",
    "Pacific": "West",
}

STATE_NAME_TO_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

STATE_ABBR_TO_NAME = {abbr: name for name, abbr in STATE_NAME_TO_ABBR.items()}

STATE_ABBR_TO_SUBREGION: Dict[str, str] = {}
for subregion, states in SUBREGION_TO_STATES.items():
    for abbr in states:
        STATE_ABBR_TO_SUBREGION[abbr] = subregion

STATE_ABBR_TO_REGION = {
    abbr: SUBREGION_TO_REGION[STATE_ABBR_TO_SUBREGION[abbr]] for abbr in STATE_ABBR_TO_SUBREGION
}

ALL_STATES = sorted(STATE_ABBR_TO_NAME.keys())

SYNTHETIC_VAR = "Synthetic opioids, excl. methadone (T40.4)"
ALL_OPIOIDS_VAR = "Opioids (T40.0-T40.4,T40.6)"


@dataclass
class OverdosePoint:
    date: datetime
    year: int
    monthly_count: float
    rolling_12mo_count: Optional[float]


def parse_float(value: str) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def parse_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_div_per_100k(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return (numerator / denominator) * 100000.0


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def get_population_by_state_year(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    for row in rows:
        abbr = str(row.get("state_abbr", "")).strip().upper()
        year = parse_int(row.get("year", ""))
        pop = parse_float(row.get("population", ""))
        if abbr not in STATE_ABBR_TO_NAME or year is None or pop is None or pop <= 0:
            continue
        out[(abbr, year)] = pop
    return out


def get_latest_population_by_state(pop_by_state_year: Dict[Tuple[str, int], float]) -> Dict[str, Tuple[int, float]]:
    out: Dict[str, Tuple[int, float]] = {}
    for (abbr, year), pop in pop_by_state_year.items():
        prev = out.get(abbr)
        if prev is None or year > prev[0]:
            out[abbr] = (year, pop)
    return out


def get_latest_overdose_points(rows: Iterable[Dict[str, str]]) -> Dict[Tuple[str, str], OverdosePoint]:
    latest: Dict[Tuple[str, str], OverdosePoint] = {}
    for row in rows:
        abbr = str(row.get("state_abbr", "")).strip().upper()
        variable = str(row.get("variable", "")).strip()
        date_str = str(row.get("date", "")).strip()
        if abbr not in STATE_ABBR_TO_NAME or variable not in {SYNTHETIC_VAR, ALL_OPIOIDS_VAR}:
            continue
        if not date_str:
            continue

        try:
            date_val = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        year = parse_int(row.get("year", ""))
        if year is None:
            year = date_val.year

        monthly_count = parse_float(row.get("count_est_float", ""))
        if monthly_count is None:
            monthly_count = parse_float(row.get("count", ""))
        if monthly_count is None:
            continue

        rolling = parse_float(row.get("rolling_12mo_count", ""))

        key = (abbr, variable)
        candidate = OverdosePoint(
            date=date_val,
            year=year,
            monthly_count=monthly_count,
            rolling_12mo_count=rolling,
        )
        current = latest.get(key)
        if current is None or candidate.date > current.date:
            latest[key] = candidate
    return latest


def aggregate_nflis(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    by_state_all_reports: Dict[str, float] = defaultdict(float)
    by_state_year_reports: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_substances: Dict[Tuple[str, int], set] = defaultdict(set)
    by_state_year_bases: Dict[Tuple[str, int], set] = defaultdict(set)

    years_seen = set()

    for row in rows:
        abbr = str(row.get("STATE", "")).strip().upper()
        year = parse_int(row.get("YYYY", ""))
        reports = parse_float(row.get("DRUG_REPORTS", ""))
        if abbr not in STATE_ABBR_TO_NAME or year is None or reports is None:
            continue

        years_seen.add(year)
        by_state_all_reports[abbr] += reports
        by_state_year_reports[(abbr, year)] += reports

        sub = str(row.get("SUBSTANCE_DESCRIPTION", "")).strip()
        base = str(row.get("BASE_DESCRIPTION", "")).strip()
        if sub:
            by_state_year_substances[(abbr, year)].add(sub)
        if base:
            by_state_year_bases[(abbr, year)].add(base)

    latest_year = max(years_seen) if years_seen else None

    out: Dict[str, Dict[str, float]] = {}
    for abbr in ALL_STATES:
        reports_all = by_state_all_reports.get(abbr, 0.0)
        if latest_year is None:
            reports_latest = 0.0
            uniq_sub_latest = 0
            uniq_base_latest = 0
            annual_avg = 0.0
        else:
            reports_latest = by_state_year_reports.get((abbr, latest_year), 0.0)
            uniq_sub_latest = len(by_state_year_substances.get((abbr, latest_year), set()))
            uniq_base_latest = len(by_state_year_bases.get((abbr, latest_year), set()))
            state_year_values = [
                v for (s, _y), v in by_state_year_reports.items() if s == abbr
            ]
            annual_avg = (sum(state_year_values) / len(state_year_values)) if state_year_values else 0.0

        out[abbr] = {
            "nflis_latest_year": float(latest_year) if latest_year is not None else 0.0,
            "nflis_reports_latest_year": reports_latest,
            "nflis_reports_all_years": reports_all,
            "nflis_reports_annual_average": annual_avg,
            "nflis_unique_substances_latest_year": float(uniq_sub_latest),
            "nflis_unique_bases_latest_year": float(uniq_base_latest),
        }

    return out


def aggregate_cnx_hs6(rows: Iterable[Dict[str, str]], prefix: str) -> Dict[str, Dict[str, float]]:
    by_state_all_records: Dict[str, float] = defaultdict(float)
    by_state_all_qty: Dict[str, float] = defaultdict(float)
    by_state_all_value: Dict[str, float] = defaultdict(float)
    by_state_all_hs6: Dict[str, set] = defaultdict(set)

    by_state_year_records: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_qty: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_value: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_hs6: Dict[Tuple[str, int], set] = defaultdict(set)

    years_seen = set()

    for row in rows:
        abbr = str(row.get("state_abbr", "")).strip().upper()
        year = parse_int(row.get("year", ""))
        records = parse_float(row.get("shipment_records", ""))
        qty = parse_float(row.get("total_quantity_kg", "")) or 0.0
        value = parse_float(row.get("total_value_usd", "")) or 0.0
        hs6 = str(row.get("hs6", "")).strip()

        if abbr not in STATE_ABBR_TO_NAME or year is None or records is None:
            continue

        years_seen.add(year)

        by_state_all_records[abbr] += records
        by_state_all_qty[abbr] += qty
        by_state_all_value[abbr] += value
        if hs6:
            by_state_all_hs6[abbr].add(hs6)

        key = (abbr, year)
        by_state_year_records[key] += records
        by_state_year_qty[key] += qty
        by_state_year_value[key] += value
        if hs6:
            by_state_year_hs6[key].add(hs6)

    latest_year = max(years_seen) if years_seen else None

    out: Dict[str, Dict[str, float]] = {}
    for abbr in ALL_STATES:
        if latest_year is None:
            rec_latest = qty_latest = value_latest = 0.0
            hs6_latest = 0
        else:
            key = (abbr, latest_year)
            rec_latest = by_state_year_records.get(key, 0.0)
            qty_latest = by_state_year_qty.get(key, 0.0)
            value_latest = by_state_year_value.get(key, 0.0)
            hs6_latest = len(by_state_year_hs6.get(key, set()))

        out[abbr] = {
            f"{prefix}_latest_year": float(latest_year) if latest_year is not None else 0.0,
            f"{prefix}_shipments_latest_year": rec_latest,
            f"{prefix}_quantity_kg_latest_year": qty_latest,
            f"{prefix}_value_usd_latest_year": value_latest,
            f"{prefix}_unique_hs6_latest_year": float(hs6_latest),
            f"{prefix}_shipments_all_years": by_state_all_records.get(abbr, 0.0),
            f"{prefix}_quantity_kg_all_years": by_state_all_qty.get(abbr, 0.0),
            f"{prefix}_value_usd_all_years": by_state_all_value.get(abbr, 0.0),
            f"{prefix}_unique_hs6_all_years": float(len(by_state_all_hs6.get(abbr, set()))),
        }

    return out


def aggregate_cnx_chem(rows: Iterable[Dict[str, str]], prefix: str) -> Dict[str, Dict[str, float]]:
    by_state_all_records: Dict[str, float] = defaultdict(float)
    by_state_all_qty: Dict[str, float] = defaultdict(float)
    by_state_all_value: Dict[str, float] = defaultdict(float)
    by_state_all_chem: Dict[str, set] = defaultdict(set)

    by_state_year_records: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_qty: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_value: Dict[Tuple[str, int], float] = defaultdict(float)
    by_state_year_chem: Dict[Tuple[str, int], set] = defaultdict(set)

    years_seen = set()

    for row in rows:
        abbr = str(row.get("state_abbr", "")).strip().upper()
        year = parse_int(row.get("year", ""))
        records = parse_float(row.get("shipment_records", ""))
        qty = parse_float(row.get("total_quantity_kg", "")) or 0.0
        value = parse_float(row.get("total_value_usd", "")) or 0.0
        chem = str(row.get("chemical_name", "")).strip()

        if abbr not in STATE_ABBR_TO_NAME or year is None or records is None:
            continue

        years_seen.add(year)

        by_state_all_records[abbr] += records
        by_state_all_qty[abbr] += qty
        by_state_all_value[abbr] += value
        if chem:
            by_state_all_chem[abbr].add(chem.lower())

        key = (abbr, year)
        by_state_year_records[key] += records
        by_state_year_qty[key] += qty
        by_state_year_value[key] += value
        if chem:
            by_state_year_chem[key].add(chem.lower())

    latest_year = max(years_seen) if years_seen else None

    out: Dict[str, Dict[str, float]] = {}
    for abbr in ALL_STATES:
        if latest_year is None:
            rec_latest = qty_latest = value_latest = 0.0
            chem_latest = 0
        else:
            key = (abbr, latest_year)
            rec_latest = by_state_year_records.get(key, 0.0)
            qty_latest = by_state_year_qty.get(key, 0.0)
            value_latest = by_state_year_value.get(key, 0.0)
            chem_latest = len(by_state_year_chem.get(key, set()))

        out[abbr] = {
            f"{prefix}_latest_year": float(latest_year) if latest_year is not None else 0.0,
            f"{prefix}_shipments_latest_year": rec_latest,
            f"{prefix}_quantity_kg_latest_year": qty_latest,
            f"{prefix}_value_usd_latest_year": value_latest,
            f"{prefix}_unique_chemicals_latest_year": float(chem_latest),
            f"{prefix}_shipments_all_years": by_state_all_records.get(abbr, 0.0),
            f"{prefix}_quantity_kg_all_years": by_state_all_qty.get(abbr, 0.0),
            f"{prefix}_value_usd_all_years": by_state_all_value.get(abbr, 0.0),
            f"{prefix}_unique_chemicals_all_years": float(len(by_state_all_chem.get(abbr, set()))),
        }

    return out


def get_policy_counts(rows: Iterable[Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {
        abbr: {
            "fentanyl_laws_total": 0.0,
            "fentanyl_laws_possession": 0.0,
            "fentanyl_laws_distribution_delivery": 0.0,
            "fentanyl_laws_exposing_others": 0.0,
            "fentanyl_laws_other": 0.0,
            "fentanyl_laws_sum_by_type": 0.0,
        }
        for abbr in ALL_STATES
    }

    for row in rows:
        state_name = str(row.get("state", "")).strip()
        abbr = STATE_NAME_TO_ABBR.get(state_name)
        if not abbr:
            continue

        out[abbr] = {
            "fentanyl_laws_total": parse_float(row.get("fentanyl_specific_law_count", "")) or 0.0,
            "fentanyl_laws_possession": parse_float(row.get("fentanyl_specific_law_count_possession", "")) or 0.0,
            "fentanyl_laws_distribution_delivery": parse_float(
                row.get("fentanyl_specific_law_count_distribution_delivery", "")
            )
            or 0.0,
            "fentanyl_laws_exposing_others": parse_float(
                row.get("fentanyl_specific_law_count_exposing_others", "")
            )
            or 0.0,
            "fentanyl_laws_other": parse_float(row.get("fentanyl_specific_law_count_other", "")) or 0.0,
            "fentanyl_laws_sum_by_type": parse_float(
                row.get("fentanyl_specific_law_count_sum_by_type", "")
            )
            or 0.0,
        }

    return out


def fmt(value: Optional[float], ndigits: int = 6) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.{ndigits}f}".rstrip("0").rstrip(".")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build state combined metrics CSV for bivariate map dashboard")
    parser.add_argument(
        "--od-input",
        type=Path,
        default=Path("docs/state_opioid_overdose_monthly_counts_estimated.csv"),
        help="State monthly overdose input CSV",
    )
    parser.add_argument(
        "--population-input",
        type=Path,
        default=Path("docs/us_census_state_population_annual_2015_2025.csv"),
        help="State annual population CSV",
    )
    parser.add_argument(
        "--policy-input",
        type=Path,
        default=Path("docs/fentanyl_specific_law_counts_by_state_simple.csv"),
        help="Fentanyl policy counts CSV",
    )
    parser.add_argument(
        "--nflis-input",
        type=Path,
        default=Path("docs/NFLIS_Drug_DQS_2026_03_03_13_26_55.csv"),
        help="NFLIS state-year drug reports CSV",
    )
    parser.add_argument(
        "--cnx-receiver-hs6-input",
        type=Path,
        default=Path("docs/cnx_shipments_us_state_year_hs6.csv"),
        help="CNX receiver state-year HS6 aggregate CSV",
    )
    parser.add_argument(
        "--cnx-receiver-chem-input",
        type=Path,
        default=Path("docs/cnx_shipments_us_state_year_chemical_matches.csv"),
        help="CNX receiver state-year chemical match aggregate CSV",
    )
    parser.add_argument(
        "--cnx-sender-hs6-input",
        type=Path,
        default=Path("docs/cnx_shipments_us_sender_state_year_hs6.csv"),
        help="CNX sender state-year HS6 aggregate CSV",
    )
    parser.add_argument(
        "--cnx-sender-chem-input",
        type=Path,
        default=Path("docs/cnx_shipments_us_sender_state_year_chemical_matches.csv"),
        help="CNX sender state-year chemical match aggregate CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/state_dashboard_combined_metrics.csv"),
        help="Output per-state combined metrics CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    od_rows = read_csv(args.od_input)
    pop_rows = read_csv(args.population_input)
    policy_rows = read_csv(args.policy_input)
    nflis_rows = read_csv(args.nflis_input)
    cnx_receiver_hs6_rows = read_csv(args.cnx_receiver_hs6_input)
    cnx_receiver_chem_rows = read_csv(args.cnx_receiver_chem_input)
    cnx_sender_hs6_rows = read_csv(args.cnx_sender_hs6_input)
    cnx_sender_chem_rows = read_csv(args.cnx_sender_chem_input)

    population_by_state_year = get_population_by_state_year(pop_rows)
    latest_population_by_state = get_latest_population_by_state(population_by_state_year)
    latest_overdose = get_latest_overdose_points(od_rows)
    policy = get_policy_counts(policy_rows)
    nflis = aggregate_nflis(nflis_rows)
    cnx_recv_hs6 = aggregate_cnx_hs6(cnx_receiver_hs6_rows, "cnx_recv")
    cnx_recv_chem = aggregate_cnx_chem(cnx_receiver_chem_rows, "cnx_recv_chem")
    cnx_send_hs6 = aggregate_cnx_hs6(cnx_sender_hs6_rows, "cnx_send")
    cnx_send_chem = aggregate_cnx_chem(cnx_sender_chem_rows, "cnx_send_chem")

    fieldnames = [
        "state_abbr",
        "state_name",
        "census_subregion",
        "census_region",
        "population_latest_year",
        "population_latest",
        "od_synth_latest_date",
        "od_synth_latest_year",
        "od_synth_latest_month_count",
        "od_synth_latest_month_per100k",
        "od_synth_latest_12mo_count",
        "od_synth_latest_12mo_per100k",
        "od_all_latest_date",
        "od_all_latest_year",
        "od_all_latest_month_count",
        "od_all_latest_month_per100k",
        "od_all_latest_12mo_count",
        "od_all_latest_12mo_per100k",
        "fentanyl_laws_total",
        "fentanyl_laws_possession",
        "fentanyl_laws_distribution_delivery",
        "fentanyl_laws_exposing_others",
        "fentanyl_laws_other",
        "fentanyl_laws_sum_by_type",
        "nflis_latest_year",
        "nflis_reports_latest_year",
        "nflis_reports_all_years",
        "nflis_reports_annual_average",
        "nflis_unique_substances_latest_year",
        "nflis_unique_bases_latest_year",
        "cnx_recv_latest_year",
        "cnx_recv_shipments_latest_year",
        "cnx_recv_quantity_kg_latest_year",
        "cnx_recv_value_usd_latest_year",
        "cnx_recv_unique_hs6_latest_year",
        "cnx_recv_shipments_all_years",
        "cnx_recv_quantity_kg_all_years",
        "cnx_recv_value_usd_all_years",
        "cnx_recv_unique_hs6_all_years",
        "cnx_recv_chem_latest_year",
        "cnx_recv_chem_shipments_latest_year",
        "cnx_recv_chem_quantity_kg_latest_year",
        "cnx_recv_chem_value_usd_latest_year",
        "cnx_recv_chem_unique_chemicals_latest_year",
        "cnx_recv_chem_shipments_all_years",
        "cnx_recv_chem_quantity_kg_all_years",
        "cnx_recv_chem_value_usd_all_years",
        "cnx_recv_chem_unique_chemicals_all_years",
        "cnx_send_latest_year",
        "cnx_send_shipments_latest_year",
        "cnx_send_quantity_kg_latest_year",
        "cnx_send_value_usd_latest_year",
        "cnx_send_unique_hs6_latest_year",
        "cnx_send_shipments_all_years",
        "cnx_send_quantity_kg_all_years",
        "cnx_send_value_usd_all_years",
        "cnx_send_unique_hs6_all_years",
        "cnx_send_chem_latest_year",
        "cnx_send_chem_shipments_latest_year",
        "cnx_send_chem_quantity_kg_latest_year",
        "cnx_send_chem_value_usd_latest_year",
        "cnx_send_chem_unique_chemicals_latest_year",
        "cnx_send_chem_shipments_all_years",
        "cnx_send_chem_quantity_kg_all_years",
        "cnx_send_chem_value_usd_all_years",
        "cnx_send_chem_unique_chemicals_all_years",
    ]

    output_rows: List[Dict[str, str]] = []

    for abbr in ALL_STATES:
        state_name = STATE_ABBR_TO_NAME[abbr]
        subregion = STATE_ABBR_TO_SUBREGION[abbr]
        region = STATE_ABBR_TO_REGION[abbr]

        pop_latest_year, pop_latest = latest_population_by_state.get(abbr, (None, None))

        synth = latest_overdose.get((abbr, SYNTHETIC_VAR))
        all_op = latest_overdose.get((abbr, ALL_OPIOIDS_VAR))

        synth_month = synth.monthly_count if synth else None
        synth_12mo = synth.rolling_12mo_count if synth else None
        all_month = all_op.monthly_count if all_op else None
        all_12mo = all_op.rolling_12mo_count if all_op else None

        synth_month_per100k = safe_div_per_100k(synth_month, population_by_state_year.get((abbr, synth.year)) if synth else None)
        synth_12mo_per100k = safe_div_per_100k(synth_12mo, population_by_state_year.get((abbr, synth.year)) if synth else None)
        all_month_per100k = safe_div_per_100k(all_month, population_by_state_year.get((abbr, all_op.year)) if all_op else None)
        all_12mo_per100k = safe_div_per_100k(all_12mo, population_by_state_year.get((abbr, all_op.year)) if all_op else None)

        row: Dict[str, str] = {
            "state_abbr": abbr,
            "state_name": state_name,
            "census_subregion": subregion,
            "census_region": region,
            "population_latest_year": fmt(pop_latest_year),
            "population_latest": fmt(pop_latest),
            "od_synth_latest_date": synth.date.strftime("%Y-%m-%d") if synth else "",
            "od_synth_latest_year": fmt(float(synth.year)) if synth else "",
            "od_synth_latest_month_count": fmt(synth_month),
            "od_synth_latest_month_per100k": fmt(synth_month_per100k),
            "od_synth_latest_12mo_count": fmt(synth_12mo),
            "od_synth_latest_12mo_per100k": fmt(synth_12mo_per100k),
            "od_all_latest_date": all_op.date.strftime("%Y-%m-%d") if all_op else "",
            "od_all_latest_year": fmt(float(all_op.year)) if all_op else "",
            "od_all_latest_month_count": fmt(all_month),
            "od_all_latest_month_per100k": fmt(all_month_per100k),
            "od_all_latest_12mo_count": fmt(all_12mo),
            "od_all_latest_12mo_per100k": fmt(all_12mo_per100k),
        }

        row.update({k: fmt(v) for k, v in policy[abbr].items()})
        row.update({k: fmt(v) for k, v in nflis[abbr].items()})
        row.update({k: fmt(v) for k, v in cnx_recv_hs6[abbr].items()})
        row.update({k: fmt(v) for k, v in cnx_recv_chem[abbr].items()})
        row.update({k: fmt(v) for k, v in cnx_send_hs6[abbr].items()})
        row.update({k: fmt(v) for k, v in cnx_send_chem[abbr].items()})

        output_rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Read {len(od_rows)} overdose rows from {args.od_input}")
    print(f"Read {len(pop_rows)} population rows from {args.population_input}")
    print(f"Read {len(policy_rows)} policy rows from {args.policy_input}")
    print(f"Read {len(nflis_rows)} NFLIS rows from {args.nflis_input}")
    print(f"Read {len(cnx_receiver_hs6_rows)} CNX receiver HS6 rows from {args.cnx_receiver_hs6_input}")
    print(f"Read {len(cnx_receiver_chem_rows)} CNX receiver chemical rows from {args.cnx_receiver_chem_input}")
    print(f"Read {len(cnx_sender_hs6_rows)} CNX sender HS6 rows from {args.cnx_sender_hs6_input}")
    print(f"Read {len(cnx_sender_chem_rows)} CNX sender chemical rows from {args.cnx_sender_chem_input}")
    print(f"Wrote {len(output_rows)} state rows to {args.output}")


if __name__ == "__main__":
    main()
