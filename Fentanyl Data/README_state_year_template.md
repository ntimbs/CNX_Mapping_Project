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

## Interactive dashboard (Streamlit)

You can run the local multi-source dashboard with:

```bash
python3 -m pip install -r "Fentanyl Data/dashboard_requirements.txt"
streamlit run "Fentanyl Data/nflis_state_drug_dashboard.py"
```

Current Streamlit data sources:
- NFLIS state reports (all drugs)
- Synthetic opioid overdose deaths (state-level estimated monthly)
- CBP + AMO fentanyl seizures (combined)
- CBP fentanyl seizures (Field Office/Sector)
- AMO fentanyl seizures (Branch)

Current Streamlit behavior highlights:
- NFLIS: state choropleth + drug/year filters
- CBP/AMO/combined: fiscal-to-calendar converted monthly operational views
- Overdose: state-level choropleth and trend from estimated monthly counts (derived from 12 month-ending VSRR values)

## GitHub Pages dashboard

This repo includes a static dashboard in `docs/` that runs directly on GitHub Pages:

- `docs/index.html`
- `docs/NFLIS_Drug_DQS_2026_03_03_13_26_55.csv`
- `docs/cbp_fentanyl_aor_monthly_2019_2026_dec.csv`
- `docs/amo_fentanyl_branch_monthly_2019_2026_dec.csv`
- `docs/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv`
- `docs/state_synthetic_opioid_overdose_monthly_counts_estimated.csv`

GitHub Pages is published at:

`https://ntimbs.github.io/CNX_Mapping_Project/`

Pages deploy note:
- This repository currently uses GitHub's built-in Pages pipeline (`pages build and deployment`) from `main`.
- There is no custom `.github/workflows/deploy-pages.yml` in this repo.

## CBP/AMO fentanyl dataset builds

Raw source inputs are kept in `Drug Border Seizures/`:
- `nationwide-drugs-fy19-fy22.csv`
- `nationwide-drugs-fy23-fy26-dec.csv`
- `amo-drug-seizures-fy19-fy22.csv`
- `amo-drug-seizures-fy23-fy26-dec.csv`

Build CBP Field Office/Sector fentanyl rows:

```bash
python3 "Drug Border Seizures/build_cbp_fentanyl_dataset.py"
cp "Drug Border Seizures/cbp_fentanyl_aor_monthly_2019_2026_dec.csv" "docs/cbp_fentanyl_aor_monthly_2019_2026_dec.csv"
```

The builder filters to `Drug Type == Fentanyl` and converts fiscal month labels to real calendar month-year (`Oct-Dec` map to `FY-1`).

Build AMO branch fentanyl rows:

```bash
python3 "Drug Border Seizures/build_amo_fentanyl_dataset.py"
cp "Drug Border Seizures/amo_fentanyl_branch_monthly_2019_2026_dec.csv" "docs/amo_fentanyl_branch_monthly_2019_2026_dec.csv"
```

Build combined CBP + AMO location rows:

```bash
python3 "Drug Border Seizures/build_cbp_amo_combined_fentanyl_dataset.py"
cp "Drug Border Seizures/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv" "docs/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv"
```

Build state-level synthetic opioid overdose monthly estimates:

```bash
python3 "Fentanyl Data/build_state_overdose_monthly_from_vsrr.py"
```

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
