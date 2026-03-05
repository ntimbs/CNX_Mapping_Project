#!/usr/bin/env python3
"""
Build a US state-year fentanyl template by combining:
1) NFLIS Table 3 state counts (local files in this folder), and
2) DEA Fentanyl Profiling Program (FPP) placeholder columns for manual extraction.

Outputs:
- nflis_state_year_drug_counts_2017_2022.csv
- us_state_year_fentanyl_template_2017_2023.csv
"""

from __future__ import annotations

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


DATA_DIR = Path(__file__).resolve().parent
NFLIS_PUBLICATIONS_URL = "https://www.nflis.deadiversion.usdoj.gov/publicationsRedesign.xhtml"

# State naming in NFLIS files is long-form + District of Columbia.
STATE_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
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

DEA_FPP_BY_YEAR = {
    2022: {
        "dea_fpp_source_url": "https://www.dea.gov/documents/2024/2024-09/2024-09-11/cy-2022-fentanyl-profiling-program-report",
        "dea_fpp_source_pub_date": "2024-09-11",
    },
    2023: {
        "dea_fpp_source_url": "https://www.dea.gov/documents/2025/2025-09/2025-09-22/cy-2023-annual-fentanyl-report",
        "dea_fpp_source_pub_date": "2025-09-22",
    },
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def parse_int(value: str) -> int | None:
    cleaned = clean_text(value).replace(",", "")
    if not cleaned:
        return None
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)
    return None


def parse_year_from_filename(path: Path) -> int:
    match = re.search(r"(20\d{2})", path.name)
    if not match:
        raise ValueError(f"Could not parse year from file name: {path.name}")
    return int(match.group(1))


def excel_col_to_index(col: str) -> int:
    idx = 0
    for ch in col:
        if "A" <= ch <= "Z":
            idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def extract_cell_text(
    cell: ET.Element,
    shared_strings: Sequence[str],
    ns_main: Dict[str, str],
) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        parts = [node.text or "" for node in cell.findall(".//a:t", ns_main)]
        return "".join(parts)

    value_node = cell.find("a:v", ns_main)
    if value_node is None:
        return ""

    raw = value_node.text or ""
    if cell_type == "s" and raw.isdigit():
        return shared_strings[int(raw)]
    return raw


def read_rows_from_xlsx(path: Path) -> List[List[str]]:
    ns_main = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    ns_rel = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
    rel_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

    with zipfile.ZipFile(path) as archive:
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            sst = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", ns_main):
                parts = [node.text or "" for node in si.findall(".//a:t", ns_main)]
                shared_strings.append("".join(parts))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pr:Relationship", ns_rel)
        }

        target_rid = None
        for sheet in workbook.findall("a:sheets/a:sheet", ns_main):
            sheet_name = clean_text(sheet.attrib.get("name", "")).lower()
            if "fentanyl" in sheet_name:
                target_rid = sheet.attrib.get(rel_key)
                break
        if target_rid is None:
            first_sheet = workbook.find("a:sheets/a:sheet", ns_main)
            if first_sheet is None:
                return []
            target_rid = first_sheet.attrib.get(rel_key)
        if target_rid is None or target_rid not in rel_map:
            return []

        worksheet_path = "xl/" + rel_map[target_rid].lstrip("/")
        worksheet = ET.fromstring(archive.read(worksheet_path))

        rows: List[List[str]] = []
        for row in worksheet.findall("a:sheetData/a:row", ns_main):
            decoded: List[str] = []
            for cell in row.findall("a:c", ns_main):
                ref = cell.attrib.get("r", "A1")
                col_label = "".join(ch for ch in ref if ch.isalpha()).upper()
                col_idx = excel_col_to_index(col_label)
                while len(decoded) <= col_idx:
                    decoded.append("")
                decoded[col_idx] = extract_cell_text(cell, shared_strings, ns_main)

            if any(clean_text(value) for value in decoded):
                rows.append(decoded)

        return rows


def read_rows_from_csv(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def read_rows(path: Path) -> List[List[str]]:
    if path.suffix.lower() == ".csv":
        return read_rows_from_csv(path)
    if path.suffix.lower() == ".xlsx":
        return read_rows_from_xlsx(path)
    raise ValueError(f"Unsupported file extension: {path.suffix}")


def collect_table3_files(data_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in data_dir.iterdir():
        lower_name = path.name.lower()
        if path.is_file() and path.suffix.lower() in {".csv", ".xlsx"}:
            if "table3" in lower_name and ("nflis" in lower_name or "publicdata" in lower_name):
                files.append(path)

    return sorted(files, key=lambda p: (parse_year_from_filename(p), p.name.lower()))


def parse_nflis_counts_from_rows(rows: Iterable[List[str]]) -> Dict[str, Dict[str, int]]:
    state_to_drug_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    current_states: List[str] = []

    header_labels = {"drug", "state"}
    skip_prefixes = (
        "table 3.",
        "counts of fentanyl",
        "drug category",
        "methodology:",
        "source:",
        "suggested citation:",
    )

    for raw_row in rows:
        row = [clean_text(cell) for cell in raw_row]
        if not any(row):
            continue

        first = row[0]
        first_lower = first.lower()

        if first_lower in header_labels:
            current_states = [cell for cell in row[1:] if cell]
            continue

        if first.startswith("*") or "=" in first and first.split("=", 1)[0].isupper():
            continue

        if first_lower.startswith(skip_prefixes):
            continue

        if not current_states or not first:
            continue

        drug_name = clean_text(first)
        if not drug_name:
            continue

        for idx, state_name in enumerate(current_states, start=1):
            value = row[idx] if idx < len(row) else ""
            count = parse_int(value)
            if count is None:
                continue
            state_to_drug_counts[state_name][drug_name] += count

    return state_to_drug_counts


def rank_compounds(drug_counts: Dict[str, int], limit: int = 3) -> List[tuple[str, int]]:
    ranked = [(drug, count) for drug, count in drug_counts.items() if count > 0]
    ranked.sort(key=lambda item: (-item[1], item[0].lower()))
    return ranked[:limit]


def build_outputs(data_dir: Path) -> tuple[List[dict], List[dict]]:
    table3_files = collect_table3_files(data_dir)
    if not table3_files:
        raise FileNotFoundError(
            f"No NFLIS Table 3 files were found in {data_dir}. "
            "Expected names containing 'Table3'."
        )

    long_rows: List[dict] = []
    by_state_year: Dict[tuple[str, int], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    source_file_by_year: Dict[int, str] = {}

    for path in table3_files:
        year = parse_year_from_filename(path)
        source_file_by_year[year] = path.name
        rows = read_rows(path)
        parsed = parse_nflis_counts_from_rows(rows)

        for state_name, drug_counts in parsed.items():
            for drug_name, count in drug_counts.items():
                long_rows.append(
                    {
                        "state_name": state_name,
                        "state_abbr": STATE_ABBR.get(state_name, ""),
                        "year": year,
                        "drug_name": drug_name,
                        "reports_count": count,
                        "nflis_table3_source_file": path.name,
                        "nflis_source_url": NFLIS_PUBLICATIONS_URL,
                    }
                )
                by_state_year[(state_name, year)][drug_name] += count

    states = sorted(
        {state for state, _ in by_state_year.keys()},
        key=lambda name: (STATE_ABBR.get(name, "ZZ"), name),
    )
    years = sorted({year for _, year in by_state_year.keys()} | set(DEA_FPP_BY_YEAR.keys()))
    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    template_rows: List[dict] = []
    for state_name in states:
        for year in years:
            counts = by_state_year.get((state_name, year), {})
            fentanyl_reports = counts.get("Fentanyl")
            total_reports = sum(counts.values()) if counts else None
            analog_reports = None
            if total_reports is not None and fentanyl_reports is not None:
                analog_reports = total_reports - fentanyl_reports

            top_all = rank_compounds(counts, limit=3) if counts else []
            analog_only = {
                drug: value for drug, value in counts.items() if drug.lower() != "fentanyl"
            }
            top_analogs = rank_compounds(analog_only, limit=3) if analog_only else []

            dea_meta = DEA_FPP_BY_YEAR.get(year, {})

            row = {
                "state_name": state_name,
                "state_abbr": STATE_ABBR.get(state_name, ""),
                "year": year,
                "nflis_fentanyl_reports": fentanyl_reports,
                "nflis_related_reports_total": total_reports,
                "nflis_analog_reports": analog_reports,
                "nflis_unique_compounds_detected": (
                    sum(1 for value in counts.values() if value > 0) if counts else None
                ),
                "nflis_top_compound_1": top_all[0][0] if len(top_all) > 0 else None,
                "nflis_top_compound_1_reports": top_all[0][1] if len(top_all) > 0 else None,
                "nflis_top_compound_2": top_all[1][0] if len(top_all) > 1 else None,
                "nflis_top_compound_2_reports": top_all[1][1] if len(top_all) > 1 else None,
                "nflis_top_compound_3": top_all[2][0] if len(top_all) > 2 else None,
                "nflis_top_compound_3_reports": top_all[2][1] if len(top_all) > 2 else None,
                "nflis_top_analog_1": top_analogs[0][0] if len(top_analogs) > 0 else None,
                "nflis_top_analog_1_reports": top_analogs[0][1] if len(top_analogs) > 0 else None,
                "nflis_top_analog_2": top_analogs[1][0] if len(top_analogs) > 1 else None,
                "nflis_top_analog_2_reports": top_analogs[1][1] if len(top_analogs) > 1 else None,
                "nflis_top_analog_3": top_analogs[2][0] if len(top_analogs) > 2 else None,
                "nflis_top_analog_3_reports": top_analogs[2][1] if len(top_analogs) > 2 else None,
                "nflis_table3_source_file": source_file_by_year.get(year),
                "nflis_source_url": NFLIS_PUBLICATIONS_URL if year in source_file_by_year else None,
                "dea_fpp_powder_seizures": None,
                "dea_fpp_tablet_seizures": None,
                "dea_fpp_avg_powder_purity_pct": None,
                "dea_fpp_avg_tablet_potency_mg": None,
                "dea_fpp_dominant_composition_notes": None,
                "dea_fpp_source_url": dea_meta.get("dea_fpp_source_url"),
                "dea_fpp_source_pub_date": dea_meta.get("dea_fpp_source_pub_date"),
                "dea_fpp_extraction_status": (
                    "pending_manual_extract" if year in DEA_FPP_BY_YEAR else None
                ),
                "record_generated_utc": generated_utc,
            }
            template_rows.append(row)

    template_rows.sort(key=lambda r: (r["year"], r["state_abbr"], r["state_name"]))
    long_rows.sort(key=lambda r: (r["year"], r["state_abbr"], r["state_name"], r["drug_name"]))
    return long_rows, template_rows


def write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path.name}")
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    long_rows, template_rows = build_outputs(DATA_DIR)
    long_path = DATA_DIR / "nflis_state_year_drug_counts_2017_2022.csv"
    template_path = DATA_DIR / "us_state_year_fentanyl_template_2017_2023.csv"
    write_csv(long_path, long_rows)
    write_csv(template_path, template_rows)
    print(f"Wrote {long_path}")
    print(f"Wrote {template_path}")
    print(f"Rows: {len(template_rows)} state-year records, {len(long_rows)} state-year-drug records")


if __name__ == "__main__":
    main()
