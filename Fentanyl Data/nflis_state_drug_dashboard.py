#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_FILE = Path(__file__).resolve().parent / "nflis_state_year_drug_counts_2017_2022.csv"


@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
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


def main() -> None:
    st.set_page_config(page_title="NFLIS Drug Map", layout="wide")
    st.title("NFLIS State Drug Reports Dashboard (2017-2022)")
    st.caption(f"Data source: {DATA_FILE.name}")

    if not DATA_FILE.exists():
        st.error(f"Data file not found: {DATA_FILE}")
        st.stop()

    df = load_data(DATA_FILE)
    years = sorted(df["year"].unique().tolist())
    drugs = sorted(df["drug_name"].unique().tolist())

    with st.sidebar:
        st.header("Filters")
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
        )
        hide_zero_states = st.checkbox("Hide states with zero value", value=False)

    if not selected_years or not selected_drugs:
        st.info("Select at least one year and one drug.")
        st.stop()

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
    c3.metric(metric_label, f"{total_reports:,.2f}" if aggregation.startswith("Average annual") else f"{int(total_reports):,}")
    st.caption(f"States with non-zero value: {states_with_data}")

    fig = px.choropleth(
        agg,
        locations="state_abbr",
        locationmode="USA-states",
        color="metric_value",
        scope="usa",
        hover_name="state_name",
        hover_data={"state_abbr": True, "metric_value": ":,.2f" if aggregation.startswith("Average annual") else ":,.0f"},
        color_continuous_scale="YlOrRd",
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


if __name__ == "__main__":
    main()
