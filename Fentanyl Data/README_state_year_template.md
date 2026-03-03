# US State-Year Fentanyl Template

This folder now includes a generator that builds a single `state,year` template combining:

- NFLIS Table 3 state-level fentanyl/fentanyl-related report counts (2017-2022, from local files)
- DEA Fentanyl Profiling Program (FPP) placeholder columns for manual extraction (2022-2023)

## Build command

```bash
python3 "Fentanyl Data/build_fentanyl_state_year_template.py"
```

## Output files

- `Fentanyl Data/nflis_state_year_drug_counts_2017_2022.csv`
  - Long-form NFLIS rows: one row per `state_name, year, drug_name`
  - Useful for composition analysis and custom aggregations

- `Fentanyl Data/us_state_year_fentanyl_template_2017_2023.csv`
  - One row per `state_name, year`
  - Includes NFLIS derived metrics plus DEA FPP placeholder fields

## Interactive dashboard

You can run a local Streamlit dashboard that maps selected drug/year combinations:

```bash
python3 -m pip install -r "Fentanyl Data/dashboard_requirements.txt"
streamlit run "Fentanyl Data/nflis_state_drug_dashboard.py"
```

Dashboard features:
- Multi-select drugs
- Multi-select years
- U.S. choropleth map by state
- Toggle between total and average annual reports
- Download filtered state-level totals as CSV

## Key columns in `us_state_year_fentanyl_template_2017_2023.csv`

- `nflis_fentanyl_reports`: count where `drug_name == Fentanyl`
- `nflis_related_reports_total`: sum across all fentanyl/fentanyl-related compounds in Table 3
- `nflis_analog_reports`: `total - fentanyl`
- `nflis_unique_compounds_detected`: number of compounds with count > 0
- `nflis_top_compound_[1..3]` (+ `_reports`): top compounds by report count
- `nflis_top_analog_[1..3]` (+ `_reports`): top non-fentanyl compounds
- `dea_fpp_*`: placeholder fields for state-level DEA FPP extraction (powder/tablet seizures, purity/potency, composition notes)
- `dea_fpp_source_url`, `dea_fpp_source_pub_date`: report metadata for CY 2022 and CY 2023

## Notes

- This script only reads local files in this directory whose names contain `Table3` and end in `.csv` or `.xlsx`.
- DEA values are intentionally left blank (`pending_manual_extract`) so you can enter values from the report tables/maps you trust.
