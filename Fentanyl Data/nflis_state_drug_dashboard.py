#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


NFLIS_DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "NFLIS_Drug_DQS_2026_03_03_13_26_55.csv"
)
CBP_DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "Drug Border Seizures"
    / "cbp_fentanyl_aor_monthly_2019_2026_dec.csv"
)
AMO_DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "Drug Border Seizures"
    / "amo_fentanyl_branch_monthly_2019_2026_dec.csv"
)
OPS_COMBINED_DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "Drug Border Seizures"
    / "cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv"
)
LIGHT_TO_DARK_SCALE = ["#fff7bc", "#fec44f", "#fe9929", "#d95f0e", "#8c2d04"]

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


@st.cache_data(show_spinner=False)
def load_nflis_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Supported NFLIS schemas:
    # 1) normalized local schema: state_abbr, state_name, year, drug_name, reports_count
    # 2) DQS export schema: STATE, STATE_LONG_NAME, YYYY, BASE_DESCRIPTION, DRUG_REPORTS
    normalized_required = {"state_name", "state_abbr", "year", "drug_name", "reports_count"}
    dqs_required = {"STATE", "STATE_LONG_NAME", "YYYY", "DRUG_REPORTS"}

    if normalized_required.issubset(df.columns):
        out = df.copy()
        out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
        out["reports_count"] = pd.to_numeric(out["reports_count"], errors="coerce").fillna(0)
        out["state_abbr"] = out["state_abbr"].astype(str).str.strip()
        out["state_name"] = out["state_name"].astype(str).str.strip()
        out["drug_name"] = out["drug_name"].astype(str).str.strip()
        out = out.dropna(subset=["year"])
        out["year"] = out["year"].astype(int)
        return out

    if dqs_required.issubset(df.columns):
        out = pd.DataFrame()
        out["state_abbr"] = df["STATE"].astype(str).str.strip()
        out["state_name"] = df["STATE_LONG_NAME"].astype(str).str.strip()
        out["year"] = pd.to_numeric(df["YYYY"], errors="coerce").astype("Int64")
        if "BASE_DESCRIPTION" in df.columns:
            out["drug_name"] = df["BASE_DESCRIPTION"].astype(str).str.strip()
        elif "SUBSTANCE_DESCRIPTION" in df.columns:
            out["drug_name"] = df["SUBSTANCE_DESCRIPTION"].astype(str).str.strip()
        else:
            raise ValueError("DQS schema missing BASE_DESCRIPTION/SUBSTANCE_DESCRIPTION")
        out["reports_count"] = pd.to_numeric(df["DRUG_REPORTS"], errors="coerce").fillna(0)

        out = out.dropna(subset=["year"])
        out = out[
            (out["state_abbr"] != "")
            & (out["state_name"] != "")
            & (out["drug_name"] != "")
        ].copy()
        out["year"] = out["year"].astype(int)

        # DQS exports can include multiple periods per year; aggregate to annual state-drug totals.
        out = (
            out.groupby(["state_abbr", "state_name", "year", "drug_name"], as_index=False)["reports_count"]
            .sum()
        )
        return out

    raise ValueError(
        "Unsupported NFLIS schema. Expected either normalized columns "
        f"{sorted(normalized_required)} or DQS columns {sorted(dqs_required)}."
    )


@st.cache_data(show_spinner=False)
def load_cbp_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "fiscal_year_label",
        "fiscal_year",
        "fiscal_year_is_partial",
        "month_abbr",
        "month_num",
        "calendar_month_label",
        "calendar_month_start",
        "component",
        "region",
        "land_filter",
        "area_of_responsibility",
        "aor_type",
        "count_of_event",
        "sum_qty_lbs",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").astype("Int64")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce").astype("Int64")
    df["count_of_event"] = pd.to_numeric(df["count_of_event"], errors="coerce").fillna(0)
    df["sum_qty_lbs"] = pd.to_numeric(df["sum_qty_lbs"], errors="coerce").fillna(0)
    df["calendar_month_start"] = pd.to_datetime(df["calendar_month_start"], errors="coerce")
    df["fiscal_year_is_partial"] = (
        df["fiscal_year_is_partial"].astype(str).str.lower().isin({"true", "1", "yes"})
    )

    string_cols = [
        "fiscal_year_label",
        "month_abbr",
        "calendar_month_label",
        "component",
        "region",
        "land_filter",
        "area_of_responsibility",
        "aor_type",
    ]
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["fiscal_year", "month_num", "calendar_month_start"])
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_amo_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "fiscal_year_label",
        "fiscal_year",
        "fiscal_year_is_partial",
        "month_abbr",
        "month_num",
        "calendar_month_label",
        "calendar_month_start",
        "component",
        "region",
        "land_filter",
        "branch",
        "branch_type",
        "count_of_event",
        "sum_qty_lbs",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").astype("Int64")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce").astype("Int64")
    df["count_of_event"] = pd.to_numeric(df["count_of_event"], errors="coerce").fillna(0)
    df["sum_qty_lbs"] = pd.to_numeric(df["sum_qty_lbs"], errors="coerce").fillna(0)
    df["calendar_month_start"] = pd.to_datetime(df["calendar_month_start"], errors="coerce")
    df["fiscal_year_is_partial"] = (
        df["fiscal_year_is_partial"].astype(str).str.lower().isin({"true", "1", "yes"})
    )

    string_cols = [
        "fiscal_year_label",
        "month_abbr",
        "calendar_month_label",
        "component",
        "region",
        "land_filter",
        "branch",
        "branch_type",
    ]
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["fiscal_year", "month_num", "calendar_month_start"])
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_ops_combined_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "organization",
        "fiscal_year_label",
        "fiscal_year",
        "fiscal_year_is_partial",
        "month_abbr",
        "month_num",
        "calendar_month_label",
        "calendar_month_start",
        "component",
        "region",
        "land_filter",
        "location_name",
        "location_type",
        "count_of_event",
        "sum_qty_lbs",
        "lat",
        "lon",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").astype("Int64")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce").astype("Int64")
    df["count_of_event"] = pd.to_numeric(df["count_of_event"], errors="coerce").fillna(0)
    df["sum_qty_lbs"] = pd.to_numeric(df["sum_qty_lbs"], errors="coerce").fillna(0)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["calendar_month_start"] = pd.to_datetime(df["calendar_month_start"], errors="coerce")
    df["fiscal_year_is_partial"] = (
        df["fiscal_year_is_partial"].astype(str).str.lower().isin({"true", "1", "yes"})
    )

    string_cols = [
        "organization",
        "fiscal_year_label",
        "month_abbr",
        "calendar_month_label",
        "component",
        "region",
        "land_filter",
        "location_name",
        "location_type",
    ]
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["fiscal_year", "month_num", "calendar_month_start"])
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    return df


def run_nflis_view(df: pd.DataFrame) -> None:
    years = sorted(df["year"].unique().tolist())
    drugs = sorted(df["drug_name"].unique().tolist())

    with st.sidebar:
        st.header("NFLIS Filters")
        selected_years = st.multiselect(
            "Years",
            options=years,
            default=[max(years)],
        )
        default_drug = ["Fentanyl"] if "Fentanyl" in drugs else drugs[:1]
        selected_drugs = st.multiselect(
            "Drugs",
            options=drugs,
            default=default_drug,
        )
        aggregation = st.radio(
            "Map value",
            options=[
                "Total reports (sum across selected years)",
                "Average annual reports (across selected years)",
            ],
            key="nflis_aggregation",
        )
        hide_zero_states = st.checkbox("Hide states with zero value", value=False, key="nflis_hide_zero")

    if not selected_years or not selected_drugs:
        st.info("Select at least one year and one drug.")
        return

    filtered = df[
        df["year"].isin(selected_years)
        & df["drug_name"].isin(selected_drugs)
    ].copy()

    agg = (
        filtered.groupby(["state_abbr", "state_name"], as_index=False)["reports_count"]
        .sum()
        .rename(columns={"reports_count": "metric_value"})
    )

    if aggregation.startswith("Average annual"):
        agg["metric_value"] = agg["metric_value"] / max(len(selected_years), 1)
        metric_label = "Average annual reports"
    else:
        metric_label = "Total reports"

    agg["metric_value"] = agg["metric_value"].round(2)

    if hide_zero_states:
        agg = agg[agg["metric_value"] > 0]

    total_reports = agg["metric_value"].sum()
    states_with_data = int((agg["metric_value"] > 0).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected drugs", len(selected_drugs))
    c2.metric("Selected years", len(selected_years))
    c3.metric(
        metric_label,
        f"{total_reports:,.2f}" if aggregation.startswith("Average annual") else f"{int(total_reports):,}",
    )
    st.caption(f"States with non-zero value: {states_with_data}")

    fig = px.choropleth(
        agg,
        locations="state_abbr",
        locationmode="USA-states",
        color="metric_value",
        scope="usa",
        hover_name="state_name",
        hover_data={"state_abbr": True, "metric_value": ":,.2f" if aggregation.startswith("Average annual") else ":,.0f"},
        color_continuous_scale=LIGHT_TO_DARK_SCALE,
        labels={"metric_value": metric_label},
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        coloraxis_colorbar={"title": metric_label},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("State Values")
    table = agg.sort_values("metric_value", ascending=False).reset_index(drop=True)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download filtered state totals (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="nflis_filtered_state_totals.csv",
        mime="text/csv",
    )


def run_cbp_view(df: pd.DataFrame) -> None:
    fiscal_year_labels_all = sorted(
        df["fiscal_year_label"].unique().tolist(),
        key=lambda label: (
            int("".join(ch for ch in label if ch.isdigit())[:4]),
            "FYTD" in label.upper(),
        ),
    )
    month_order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_options = [m for m in month_order if m in set(df["month_abbr"].unique())]
    component_options = sorted(df["component"].unique().tolist())
    region_options = sorted(df["region"].unique().tolist())
    land_filter_options = sorted(df["land_filter"].unique().tolist())
    aor_options = sorted(df["area_of_responsibility"].unique().tolist())

    with st.sidebar:
        st.header("CBP Fentanyl Filters")
        include_partial_fy = st.checkbox(
            "Include FYTD (partial fiscal year)",
            value=False,
            help="FYTD is partial and not directly comparable to full fiscal years.",
        )
        if include_partial_fy:
            fiscal_year_options = fiscal_year_labels_all
        else:
            fiscal_year_options = [fy for fy in fiscal_year_labels_all if "FYTD" not in fy.upper()]

        selected_fiscal_years = st.multiselect(
            "Fiscal years",
            options=fiscal_year_options,
            default=fiscal_year_options,
        )
        selected_months = st.multiselect(
            "Month (fiscal labels converted to calendar month-year internally)",
            options=month_options,
            default=month_options,
        )
        selected_components = st.multiselect("Component", options=component_options, default=component_options)
        selected_regions = st.multiselect("Region", options=region_options, default=region_options)
        selected_land_filters = st.multiselect("Land Filter", options=land_filter_options, default=land_filter_options)
        selected_aor = st.multiselect("Field Office / Sector", options=aor_options, default=aor_options)
        metric_mode = st.radio(
            "Map metric",
            options=[
                "Seizure events (count)",
                "Seized quantity (lbs)",
            ],
            key="cbp_metric_mode",
        )

    if (
        not selected_fiscal_years
        or not selected_months
        or not selected_components
        or not selected_regions
        or not selected_land_filters
        or not selected_aor
    ):
        st.info("Select at least one value for each CBP filter.")
        return

    filtered = df[
        df["fiscal_year_label"].isin(selected_fiscal_years)
        & df["month_abbr"].isin(selected_months)
        & df["component"].isin(selected_components)
        & df["region"].isin(selected_regions)
        & df["land_filter"].isin(selected_land_filters)
        & df["area_of_responsibility"].isin(selected_aor)
    ].copy()

    if filtered.empty:
        st.warning("No CBP fentanyl records match the selected filters.")
        return

    filtered["lat"] = filtered["area_of_responsibility"].map(lambda x: AOR_COORDS.get(x, (None, None))[0])
    filtered["lon"] = filtered["area_of_responsibility"].map(lambda x: AOR_COORDS.get(x, (None, None))[1])

    grouped = (
        filtered.groupby(["area_of_responsibility", "aor_type"], as_index=False)[["count_of_event", "sum_qty_lbs"]]
        .sum()
        .rename(columns={"count_of_event": "events_total", "sum_qty_lbs": "qty_lbs_total"})
    )
    grouped["lat"] = grouped["area_of_responsibility"].map(lambda x: AOR_COORDS.get(x, (None, None))[0])
    grouped["lon"] = grouped["area_of_responsibility"].map(lambda x: AOR_COORDS.get(x, (None, None))[1])
    grouped["metric_value"] = grouped["events_total"] if metric_mode.startswith("Seizure events") else grouped["qty_lbs_total"]
    metric_label = "Seizure events" if metric_mode.startswith("Seizure events") else "Seized quantity (lbs)"

    calendar_start = filtered["calendar_month_start"].min().date().isoformat()
    calendar_end = filtered["calendar_month_start"].max().date().isoformat()

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected AORs", grouped.shape[0])
    c2.metric("Calendar month span", f"{calendar_start} to {calendar_end}")
    c3.metric(metric_label, f"{grouped['metric_value'].sum():,.0f}" if metric_label == "Seizure events" else f"{grouped['metric_value'].sum():,.2f}")
    st.caption(
        "CBP records are fiscal-year based; month labels are converted to actual calendar month-year "
        "using U.S. FY rules (Oct-Dec belong to prior calendar year)."
    )
    st.caption("AOR marker locations are approximate headquarters centroids for Field Offices/Sectors.")

    map_df = grouped.dropna(subset=["lat", "lon"]).copy()
    missing_coords = grouped.shape[0] - map_df.shape[0]
    if map_df.empty:
        st.warning("No AOR coordinates available for map rendering.")
    else:
        fig = px.scatter_geo(
            map_df,
            lat="lat",
            lon="lon",
            size="metric_value",
            color="metric_value",
            scope="usa",
            hover_name="area_of_responsibility",
            hover_data={
                "aor_type": True,
                "events_total": ":,.0f",
                "qty_lbs_total": ":,.2f",
                "lat": False,
                "lon": False,
                "metric_value": ":,.0f" if metric_label == "Seizure events" else ":,.2f",
            },
            color_continuous_scale=LIGHT_TO_DARK_SCALE,
            labels={"metric_value": metric_label},
        )
        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            coloraxis_colorbar={"title": metric_label},
        )
        st.plotly_chart(fig, use_container_width=True)

    if missing_coords > 0:
        st.info(f"{missing_coords} AOR(s) have no coordinate mapping and were excluded from the map.")

    monthly = (
        filtered.groupby("calendar_month_start", as_index=False)[["count_of_event", "sum_qty_lbs"]]
        .sum()
        .sort_values("calendar_month_start")
    )
    monthly_value_col = "count_of_event" if metric_label == "Seizure events" else "sum_qty_lbs"
    trend_fig = px.line(
        monthly,
        x="calendar_month_start",
        y=monthly_value_col,
        markers=True,
        labels={
            "calendar_month_start": "Calendar month",
            monthly_value_col: metric_label,
        },
        title=f"Monthly CBP fentanyl trend ({metric_label})",
    )
    trend_fig.update_layout(margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(trend_fig, use_container_width=True)

    st.subheader("AOR Values")
    table = grouped.sort_values("metric_value", ascending=False).reset_index(drop=True)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download filtered CBP AOR totals (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="cbp_fentanyl_filtered_aor_totals.csv",
        mime="text/csv",
    )


def run_amo_view(df: pd.DataFrame) -> None:
    fiscal_year_labels_all = sorted(
        df["fiscal_year_label"].unique().tolist(),
        key=lambda label: (
            int("".join(ch for ch in label if ch.isdigit())[:4]),
            "FYTD" in label.upper(),
        ),
    )
    month_order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_options = [m for m in month_order if m in set(df["month_abbr"].unique())]
    component_options = sorted(df["component"].unique().tolist())
    region_options = sorted(df["region"].unique().tolist())
    land_filter_options = sorted(df["land_filter"].unique().tolist())
    branch_options = sorted(df["branch"].unique().tolist())

    with st.sidebar:
        st.header("AMO Fentanyl Filters")
        include_partial_fy = st.checkbox(
            "Include FYTD (partial fiscal year)",
            value=False,
            key="amo_include_fytd",
            help="FYTD is partial and not directly comparable to full fiscal years.",
        )
        if include_partial_fy:
            fiscal_year_options = fiscal_year_labels_all
        else:
            fiscal_year_options = [fy for fy in fiscal_year_labels_all if "FYTD" not in fy.upper()]

        selected_fiscal_years = st.multiselect(
            "Fiscal years",
            options=fiscal_year_options,
            default=fiscal_year_options,
            key="amo_fiscal_years",
        )
        selected_months = st.multiselect(
            "Month (fiscal labels converted to calendar month-year internally)",
            options=month_options,
            default=month_options,
            key="amo_months",
        )
        selected_components = st.multiselect("Component", options=component_options, default=component_options, key="amo_components")
        selected_regions = st.multiselect("Region", options=region_options, default=region_options, key="amo_regions")
        selected_land_filters = st.multiselect("Land Filter", options=land_filter_options, default=land_filter_options, key="amo_land_filter")
        selected_branches = st.multiselect("Branch", options=branch_options, default=branch_options, key="amo_branches")
        metric_mode = st.radio(
            "Map metric",
            options=[
                "Seizure events (count)",
                "Seized quantity (lbs)",
            ],
            key="amo_metric_mode",
        )

    if (
        not selected_fiscal_years
        or not selected_months
        or not selected_components
        or not selected_regions
        or not selected_land_filters
        or not selected_branches
    ):
        st.info("Select at least one value for each AMO filter.")
        return

    filtered = df[
        df["fiscal_year_label"].isin(selected_fiscal_years)
        & df["month_abbr"].isin(selected_months)
        & df["component"].isin(selected_components)
        & df["region"].isin(selected_regions)
        & df["land_filter"].isin(selected_land_filters)
        & df["branch"].isin(selected_branches)
    ].copy()

    if filtered.empty:
        st.warning("No AMO fentanyl records match the selected filters.")
        return

    grouped = (
        filtered.groupby(["branch", "branch_type"], as_index=False)[["count_of_event", "sum_qty_lbs"]]
        .sum()
        .rename(columns={"count_of_event": "events_total", "sum_qty_lbs": "qty_lbs_total"})
    )
    grouped["lat"] = grouped["branch"].map(lambda x: BRANCH_COORDS.get(x, (None, None))[0])
    grouped["lon"] = grouped["branch"].map(lambda x: BRANCH_COORDS.get(x, (None, None))[1])
    grouped["metric_value"] = grouped["events_total"] if metric_mode.startswith("Seizure events") else grouped["qty_lbs_total"]
    metric_label = "Seizure events" if metric_mode.startswith("Seizure events") else "Seized quantity (lbs)"

    calendar_start = filtered["calendar_month_start"].min().date().isoformat()
    calendar_end = filtered["calendar_month_start"].max().date().isoformat()

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected branches", grouped.shape[0])
    c2.metric("Calendar month span", f"{calendar_start} to {calendar_end}")
    c3.metric(metric_label, f"{grouped['metric_value'].sum():,.0f}" if metric_label == "Seizure events" else f"{grouped['metric_value'].sum():,.2f}")
    st.caption(
        "AMO records are fiscal-year based; month labels are converted to actual calendar month-year "
        "using U.S. FY rules (Oct-Dec belong to prior calendar year)."
    )
    st.caption("Branch marker locations are approximate operating hub centroids.")

    map_df = grouped.dropna(subset=["lat", "lon"]).copy()
    missing_coords = grouped.shape[0] - map_df.shape[0]
    if map_df.empty:
        st.warning("No branch coordinates available for map rendering.")
    else:
        fig = px.scatter_geo(
            map_df,
            lat="lat",
            lon="lon",
            size="metric_value",
            color="metric_value",
            scope="usa",
            hover_name="branch",
            hover_data={
                "branch_type": True,
                "events_total": ":,.0f",
                "qty_lbs_total": ":,.2f",
                "lat": False,
                "lon": False,
                "metric_value": ":,.0f" if metric_label == "Seizure events" else ":,.2f",
            },
            color_continuous_scale=LIGHT_TO_DARK_SCALE,
            labels={"metric_value": metric_label},
        )
        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            coloraxis_colorbar={"title": metric_label},
        )
        st.plotly_chart(fig, use_container_width=True)

    if missing_coords > 0:
        st.info(f"{missing_coords} branch(es) have no coordinate mapping and were excluded from the map.")

    monthly = (
        filtered.groupby("calendar_month_start", as_index=False)[["count_of_event", "sum_qty_lbs"]]
        .sum()
        .sort_values("calendar_month_start")
    )
    monthly_value_col = "count_of_event" if metric_label == "Seizure events" else "sum_qty_lbs"
    trend_fig = px.line(
        monthly,
        x="calendar_month_start",
        y=monthly_value_col,
        markers=True,
        labels={
            "calendar_month_start": "Calendar month",
            monthly_value_col: metric_label,
        },
        title=f"Monthly AMO fentanyl trend ({metric_label})",
    )
    trend_fig.update_layout(margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(trend_fig, use_container_width=True)

    st.subheader("Branch Values")
    table = grouped.sort_values("metric_value", ascending=False).reset_index(drop=True)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download filtered AMO branch totals (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="amo_fentanyl_filtered_branch_totals.csv",
        mime="text/csv",
    )


def run_ops_combined_view(df: pd.DataFrame) -> None:
    fiscal_year_labels_all = sorted(
        df["fiscal_year_label"].unique().tolist(),
        key=lambda label: (
            int("".join(ch for ch in label if ch.isdigit())[:4]),
            "FYTD" in label.upper(),
        ),
    )
    month_order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_options = [m for m in month_order if m in set(df["month_abbr"].unique())]
    org_options = sorted(df["organization"].unique().tolist())
    component_options = sorted(df["component"].unique().tolist())
    region_options = sorted(df["region"].unique().tolist())
    land_filter_options = sorted(df["land_filter"].unique().tolist())
    location_type_options = sorted(df["location_type"].unique().tolist())

    with st.sidebar:
        st.header("CBP + AMO Fentanyl Filters")
        include_partial_fy = st.checkbox(
            "Include FYTD (partial fiscal year)",
            value=False,
            key="ops_include_fytd",
            help="FYTD is partial and not directly comparable to full fiscal years.",
        )
        if include_partial_fy:
            fiscal_year_options = fiscal_year_labels_all
        else:
            fiscal_year_options = [fy for fy in fiscal_year_labels_all if "FYTD" not in fy.upper()]

        selected_fiscal_years = st.multiselect(
            "Fiscal years",
            options=fiscal_year_options,
            default=fiscal_year_options,
            key="ops_fiscal_years",
        )
        selected_months = st.multiselect(
            "Month (fiscal labels converted to calendar month-year internally)",
            options=month_options,
            default=month_options,
            key="ops_months",
        )
        selected_orgs = st.multiselect("Organization", options=org_options, default=org_options, key="ops_orgs")
        selected_components = st.multiselect("Component", options=component_options, default=component_options, key="ops_components")
        selected_regions = st.multiselect("Region", options=region_options, default=region_options, key="ops_regions")
        selected_land_filters = st.multiselect("Land Filter", options=land_filter_options, default=land_filter_options, key="ops_land_filter")
        selected_location_types = st.multiselect(
            "Location type",
            options=location_type_options,
            default=location_type_options,
            key="ops_location_types",
        )

        location_scope = df[
            df["organization"].isin(selected_orgs)
            & df["location_type"].isin(selected_location_types)
        ].copy()
        location_options = sorted(location_scope["location_name"].unique().tolist())
        selected_locations = st.multiselect(
            "Location (Field Office / Sector / Branch)",
            options=location_options,
            default=location_options,
            key="ops_locations",
        )
        metric_mode = st.radio(
            "Map metric",
            options=[
                "Seizure events (count)",
                "Seized quantity (lbs)",
            ],
            key="ops_metric_mode",
        )

    if (
        not selected_fiscal_years
        or not selected_months
        or not selected_orgs
        or not selected_components
        or not selected_regions
        or not selected_land_filters
        or not selected_location_types
        or not selected_locations
    ):
        st.info("Select at least one value for each combined filter.")
        return

    filtered = df[
        df["fiscal_year_label"].isin(selected_fiscal_years)
        & df["month_abbr"].isin(selected_months)
        & df["organization"].isin(selected_orgs)
        & df["component"].isin(selected_components)
        & df["region"].isin(selected_regions)
        & df["land_filter"].isin(selected_land_filters)
        & df["location_type"].isin(selected_location_types)
        & df["location_name"].isin(selected_locations)
    ].copy()

    if filtered.empty:
        st.warning("No combined CBP/AMO fentanyl records match the selected filters.")
        return

    grouped = (
        filtered.groupby(["organization", "location_name", "location_type"], as_index=False)
        .agg(
            events_total=("count_of_event", "sum"),
            qty_lbs_total=("sum_qty_lbs", "sum"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
        )
    )
    grouped["metric_value"] = grouped["events_total"] if metric_mode.startswith("Seizure events") else grouped["qty_lbs_total"]
    metric_label = "Seizure events" if metric_mode.startswith("Seizure events") else "Seized quantity (lbs)"

    calendar_start = filtered["calendar_month_start"].min().date().isoformat()
    calendar_end = filtered["calendar_month_start"].max().date().isoformat()

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected locations", grouped.shape[0])
    c2.metric("Calendar month span", f"{calendar_start} to {calendar_end}")
    c3.metric(metric_label, f"{grouped['metric_value'].sum():,.0f}" if metric_label == "Seizure events" else f"{grouped['metric_value'].sum():,.2f}")
    st.caption(
        "Combined CBP + AMO records are fiscal-year based; month labels are converted to actual "
        "calendar month-year using U.S. FY rules (Oct-Dec belong to prior calendar year)."
    )
    st.caption("Map locations are approximate headquarters or operating hub centroids.")

    map_df = grouped.dropna(subset=["lat", "lon"]).copy()
    missing_coords = grouped.shape[0] - map_df.shape[0]
    if map_df.empty:
        st.warning("No location coordinates available for map rendering.")
    else:
        fig = px.scatter_geo(
            map_df,
            lat="lat",
            lon="lon",
            size="metric_value",
            color="metric_value",
            scope="usa",
            hover_name="location_name",
            hover_data={
                "organization": True,
                "location_type": True,
                "events_total": ":,.0f",
                "qty_lbs_total": ":,.2f",
                "lat": False,
                "lon": False,
                "metric_value": ":,.0f" if metric_label == "Seizure events" else ":,.2f",
            },
            color_continuous_scale=LIGHT_TO_DARK_SCALE,
            labels={"metric_value": metric_label},
        )
        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            coloraxis_colorbar={"title": metric_label},
        )
        st.plotly_chart(fig, use_container_width=True)

    if missing_coords > 0:
        st.info(f"{missing_coords} location(s) have no coordinate mapping and were excluded from the map.")

    monthly = (
        filtered.groupby("calendar_month_start", as_index=False)[["count_of_event", "sum_qty_lbs"]]
        .sum()
        .sort_values("calendar_month_start")
    )
    monthly_value_col = "count_of_event" if metric_label == "Seizure events" else "sum_qty_lbs"
    trend_fig = px.line(
        monthly,
        x="calendar_month_start",
        y=monthly_value_col,
        markers=True,
        labels={
            "calendar_month_start": "Calendar month",
            monthly_value_col: metric_label,
        },
        title=f"Monthly combined CBP + AMO fentanyl trend ({metric_label})",
    )
    trend_fig.update_layout(margin={"l": 0, "r": 0, "t": 40, "b": 0})
    st.plotly_chart(trend_fig, use_container_width=True)

    st.subheader("Location Values")
    table = grouped.sort_values("metric_value", ascending=False).reset_index(drop=True)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        label="Download filtered CBP + AMO location totals (CSV)",
        data=table.to_csv(index=False).encode("utf-8"),
        file_name="cbp_amo_fentanyl_filtered_location_totals.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(page_title="U.S. Drug Seizure Dashboard", layout="wide")
    st.title("U.S. Drug Seizure Dashboard")
    st.caption(
        "Switch between NFLIS state reports, a combined CBP + AMO fentanyl seizure dataset, "
        "and the source-specific CBP/AMO views."
    )

    if not NFLIS_DATA_FILE.exists():
        st.error(f"NFLIS data file not found: {NFLIS_DATA_FILE}")
        st.stop()
    if not CBP_DATA_FILE.exists():
        st.error(
            f"CBP fentanyl data file not found: {CBP_DATA_FILE}. "
            "Run Drug Border Seizures/build_cbp_fentanyl_dataset.py first."
        )
        st.stop()
    if not AMO_DATA_FILE.exists():
        st.error(
            f"AMO fentanyl data file not found: {AMO_DATA_FILE}. "
            "Run Drug Border Seizures/build_amo_fentanyl_dataset.py first."
        )
        st.stop()
    if not OPS_COMBINED_DATA_FILE.exists():
        st.error(
            f"Combined CBP + AMO fentanyl data file not found: {OPS_COMBINED_DATA_FILE}. "
            "Run Drug Border Seizures/build_cbp_amo_combined_fentanyl_dataset.py first."
        )
        st.stop()

    with st.sidebar:
        data_source = st.radio(
            "Data source",
            options=[
                "NFLIS state reports (all drugs)",
                "CBP + AMO fentanyl seizures (Combined)",
                "CBP fentanyl seizures (Field Office/Sector)",
                "AMO fentanyl seizures (Branch)",
            ],
        )

    if data_source.startswith("NFLIS"):
        st.caption(f"Current source file: {NFLIS_DATA_FILE.name}")
        nflis_df = load_nflis_data(NFLIS_DATA_FILE)
        run_nflis_view(nflis_df)
    elif data_source.startswith("CBP + AMO"):
        st.caption(f"Current source file: {OPS_COMBINED_DATA_FILE.name}")
        ops_df = load_ops_combined_data(OPS_COMBINED_DATA_FILE)
        run_ops_combined_view(ops_df)
    elif data_source.startswith("CBP"):
        st.caption(f"Current source file: {CBP_DATA_FILE.name}")
        cbp_df = load_cbp_data(CBP_DATA_FILE)
        run_cbp_view(cbp_df)
    else:
        st.caption(f"Current source file: {AMO_DATA_FILE.name}")
        amo_df = load_amo_data(AMO_DATA_FILE)
        run_amo_view(amo_df)


if __name__ == "__main__":
    main()
