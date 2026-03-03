#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


NFLIS_DATA_FILE = Path(__file__).resolve().parent / "nflis_state_year_drug_counts_2017_2022.csv"
CBP_DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "Drug Border Seizures"
    / "cbp_fentanyl_aor_monthly_2019_2026_dec.csv"
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


@st.cache_data(show_spinner=False)
def load_nflis_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"state_name", "state_abbr", "year", "drug_name", "reports_count"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["reports_count"] = pd.to_numeric(df["reports_count"], errors="coerce").fillna(0)
    df["state_abbr"] = df["state_abbr"].astype(str).str.strip()
    df["state_name"] = df["state_name"].astype(str).str.strip()
    df["drug_name"] = df["drug_name"].astype(str).str.strip()
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    return df


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


def main() -> None:
    st.set_page_config(page_title="U.S. Drug Seizure Dashboard", layout="wide")
    st.title("U.S. Drug Seizure Dashboard")
    st.caption("Switch between NFLIS state reports and CBP fentanyl seizure records.")

    if not NFLIS_DATA_FILE.exists():
        st.error(f"NFLIS data file not found: {NFLIS_DATA_FILE}")
        st.stop()
    if not CBP_DATA_FILE.exists():
        st.error(
            f"CBP fentanyl data file not found: {CBP_DATA_FILE}. "
            "Run Drug Border Seizures/build_cbp_fentanyl_dataset.py first."
        )
        st.stop()

    with st.sidebar:
        data_source = st.radio(
            "Data source",
            options=[
                "NFLIS state reports (all drugs)",
                "CBP fentanyl seizures (Field Office/Sector)",
            ],
        )

    if data_source.startswith("NFLIS"):
        st.caption(f"Current source file: {NFLIS_DATA_FILE.name}")
        nflis_df = load_nflis_data(NFLIS_DATA_FILE)
        run_nflis_view(nflis_df)
    else:
        st.caption(f"Current source file: {CBP_DATA_FILE.name}")
        cbp_df = load_cbp_data(CBP_DATA_FILE)
        run_cbp_view(cbp_df)


if __name__ == "__main__":
    main()
