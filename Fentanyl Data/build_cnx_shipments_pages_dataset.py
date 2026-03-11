#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


US_STATE_ABBR_TO_NAME = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

STATE_CODES = set(US_STATE_ABBR_TO_NAME.keys())
STATE_NAME_TO_ABBR = {name.upper(): abbr for abbr, name in US_STATE_ABBR_TO_NAME.items()}
STATE_NAME_TO_ABBR.update(
    {
        "WASHINGTON DC": "DC",
        "WASHINGTON D C": "DC",
        "WASHINGTON, DC": "DC",
        "DISTRICT OF COLUMBIA": "DC",
    }
)

STATE_ABBR_PATTERN = "|".join(sorted(STATE_CODES, key=len, reverse=True))
STATE_NAME_PATTERN = "|".join(re.escape(name) for name in sorted(STATE_NAME_TO_ABBR.keys(), key=len, reverse=True))
ZIP_STATE_RE = re.compile(rf"\b({STATE_ABBR_PATTERN})\s+\d{{5}}(?:-\d{{4}})?\b", flags=re.IGNORECASE)
COMMA_STATE_RE = re.compile(rf",\s*({STATE_ABBR_PATTERN})\s*(?:,|$)", flags=re.IGNORECASE)
STATE_NAME_RE = re.compile(rf"\b({STATE_NAME_PATTERN})\b", flags=re.IGNORECASE)


def normalize_hs6(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"null", "none", "nan"}:
        return None
    digits_only = "".join(ch for ch in text if ch.isdigit())
    if len(digits_only) < 6:
        return None
    return digits_only[:6]


def clean_goods_description(value: object) -> str:
    if pd.isna(value):
        return "UNSPECIFIED"
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text == "" or text.lower() in {"null", "none", "nan"}:
        return "UNSPECIFIED"
    return text


def extract_state_from_address(address: object) -> str | None:
    if not isinstance(address, str):
        return None
    text = address.strip()
    if not text:
        return None

    normalized = re.sub(r"\s+", " ", text.upper().replace(".", " ")).strip()

    zip_match = ZIP_STATE_RE.search(normalized)
    if zip_match:
        return zip_match.group(1).upper()

    comma_match = COMMA_STATE_RE.search(normalized)
    if comma_match:
        return comma_match.group(1).upper()

    name_match = STATE_NAME_RE.search(normalized)
    if name_match:
        return STATE_NAME_TO_ABBR[name_match.group(1).upper()]

    tokens = [segment.strip() for segment in normalized.split(",") if segment.strip()]
    for token in reversed(tokens):
        if token in STATE_CODES:
            return token
        if token in STATE_NAME_TO_ABBR:
            return STATE_NAME_TO_ABBR[token]

        token_abbr_match = re.match(r"^([A-Z]{2})(?:\s+\d{5}(?:-\d{4})?)?$", token)
        if token_abbr_match:
            candidate = token_abbr_match.group(1)
            if candidate in STATE_CODES:
                return candidate

        token_name_zip_match = re.match(r"^([A-Z ]+)\s+\d{5}(?:-\d{4})?\b", token)
        if token_name_zip_match:
            candidate = token_name_zip_match.group(1).strip()
            if candidate in STATE_NAME_TO_ABBR:
                return STATE_NAME_TO_ABBR[candidate]

    return None


def load_base_shipments(
    input_csv: Path,
    *,
    country_iso2_col: str,
    address_col: str,
) -> pd.DataFrame:
    usecols = [
        "transaction_id",
        "sender_country_iso2",
        "sender_address",
        "receiver_country_iso2",
        "receiver_address",
        "transaction_date",
        "goods_description",
        "hs_code",
        "hs6_code",
        "predicted_hs6_codes_top_1",
        "kg_net",
        "kg_gross",
        "analytical_value_usd",
        "est_usd_value",
    ]
    df = pd.read_csv(input_csv, usecols=usecols, low_memory=False)
    df[country_iso2_col] = df[country_iso2_col].astype(str).str.strip().str.upper()
    df = df[df[country_iso2_col] == "US"].copy()

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["year"] = df["transaction_date"].dt.year.astype("Int64")

    hs6_final = pd.Series([None] * len(df), index=df.index, dtype="object")
    for col in ["hs6_code", "hs_code", "predicted_hs6_codes_top_1"]:
        hs6_candidate = df[col].apply(normalize_hs6)
        hs6_final = hs6_final.fillna(hs6_candidate)
    df["hs6"] = hs6_final.fillna("UNKNOWN")

    df[address_col] = df[address_col].astype(str)
    df["state_abbr"] = df[address_col].apply(extract_state_from_address)
    df["state_name"] = df["state_abbr"].map(US_STATE_ABBR_TO_NAME)

    df["goods_description"] = df["goods_description"].apply(clean_goods_description)

    df["kg_net"] = pd.to_numeric(df["kg_net"], errors="coerce")
    df["kg_gross"] = pd.to_numeric(df["kg_gross"], errors="coerce")
    df["quantity_kg"] = df["kg_net"].where(df["kg_net"].notna(), df["kg_gross"])

    df["analytical_value_usd"] = pd.to_numeric(df["analytical_value_usd"], errors="coerce")
    df["est_usd_value"] = pd.to_numeric(df["est_usd_value"], errors="coerce")
    df["value_usd"] = df["analytical_value_usd"].where(
        df["analytical_value_usd"].notna(), df["est_usd_value"]
    )

    return df


def build_pages_hs6_dataset(base_df: pd.DataFrame, output_csv: Path) -> None:
    base = base_df.dropna(subset=["year", "state_abbr"]).copy()
    base["year"] = base["year"].astype(int)
    base["hs6"] = base["hs6"].astype(str).str.strip().replace("", "UNKNOWN")

    grouped = (
        base.groupby(["state_abbr", "state_name", "year", "hs6"], as_index=False)
        .agg(
            shipment_records=("transaction_id", "count"),
            total_quantity_kg=("quantity_kg", "sum"),
            total_value_usd=("value_usd", "sum"),
        )
        .fillna({"total_quantity_kg": 0.0, "total_value_usd": 0.0})
        .sort_values(["year", "state_abbr", "hs6"])
        .reset_index(drop=True)
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(output_csv, index=False)

    print(f"Wrote: {output_csv}")
    print(f"Rows: {len(grouped):,}")
    print(f"Mapped source records used: {len(base):,}")
    print(f"Unique HS6: {grouped['hs6'].nunique():,}")
    print(f"Year range: {grouped['year'].min()}-{grouped['year'].max()}")


def build_pages_goods_dataset(base_df: pd.DataFrame, output_csv: Path) -> None:
    base = base_df.dropna(subset=["year", "state_abbr"]).copy()
    base["year"] = base["year"].astype(int)
    base["hs6"] = base["hs6"].astype(str).str.strip().replace("", "UNKNOWN")
    base["goods_description"] = base["goods_description"].apply(clean_goods_description)

    grouped = (
        base.groupby(["state_abbr", "state_name", "year", "hs6", "goods_description"], as_index=False)
        .agg(
            shipment_records=("transaction_id", "count"),
            total_quantity_kg=("quantity_kg", "sum"),
            total_value_usd=("value_usd", "sum"),
        )
        .fillna({"total_quantity_kg": 0.0, "total_value_usd": 0.0})
        .sort_values(["year", "state_abbr", "hs6", "goods_description"])
        .reset_index(drop=True)
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(output_csv, index=False)

    print(f"Wrote: {output_csv}")
    print(f"Rows: {len(grouped):,}")
    print(f"Mapped source records used: {len(base):,}")
    print(f"Unique goods_description: {grouped['goods_description'].nunique():,}")
    print(f"Unique HS6 (incl UNKNOWN): {grouped['hs6'].nunique():,}")
    print(f"Year range: {grouped['year'].min()}-{grouped['year'].max()}")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    input_csv = root / "cnx_transactions_us_sender_or_receiver.csv"

    print("Building CNX US-receiver datasets...")
    receiver_df = load_base_shipments(
        input_csv,
        country_iso2_col="receiver_country_iso2",
        address_col="receiver_address",
    )
    receiver_hs_output_csv = root / "docs" / "cnx_shipments_us_state_year_hs6.csv"
    build_pages_hs6_dataset(receiver_df, receiver_hs_output_csv)
    receiver_goods_output_csv = root / "docs" / "cnx_shipments_us_state_year_goods_hs6.csv"
    build_pages_goods_dataset(receiver_df, receiver_goods_output_csv)

    print("\nBuilding CNX US-sender datasets...")
    sender_df = load_base_shipments(
        input_csv,
        country_iso2_col="sender_country_iso2",
        address_col="sender_address",
    )
    sender_hs_output_csv = root / "docs" / "cnx_shipments_us_sender_state_year_hs6.csv"
    build_pages_hs6_dataset(sender_df, sender_hs_output_csv)
    sender_goods_output_csv = root / "docs" / "cnx_shipments_us_sender_state_year_goods_hs6.csv"
    build_pages_goods_dataset(sender_df, sender_goods_output_csv)


if __name__ == "__main__":
    main()
