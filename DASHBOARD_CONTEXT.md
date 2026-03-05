# CNX Dashboard Context

Last updated: 2026-03-05

This file is a persistent context log for the active dashboard implementation in this repository.

## Current dashboard surfaces

- Streamlit app: `Fentanyl Data/nflis_state_drug_dashboard.py`
- GitHub Pages app: `docs/index.html`

Both dashboards currently support the following data sources:

1. NFLIS state reports (all drugs)
2. Synthetic opioid overdose deaths (state-level estimated monthly)
3. CBP + AMO fentanyl seizures (combined)
4. CBP fentanyl seizures (Field Office/Sector)
5. AMO fentanyl seizures (Branch)

## Key data files

### Branch + deploy baseline

- Deployment branch: `main`
- Working branch: `codex/pages-dashboard`
- Current practice: keep `main` and `codex/pages-dashboard` synchronized for dashboard changes.
- Pages deploy system: GitHub built-in `pages build and deployment` (dynamic), not a custom workflow file.

### NFLIS

- Primary NFLIS file used in both dashboards:
  - `NFLIS_Drug_DQS_2026_03_03_13_26_55.csv`

### Overdose

- Raw source file added by user:
  - `VSRR_Provisional_Drug_Overdose_Death_Counts.csv`
- Derived dashboard file:
  - `Fentanyl Data/state_synthetic_opioid_overdose_monthly_counts_estimated.csv`
- Docs copy for GitHub Pages:
  - `docs/state_synthetic_opioid_overdose_monthly_counts_estimated.csv`
- Schema:
  - `state_abbr, state_name, variable, date, year, month_num, month_abbr, count, ...`
- Indicator filter:
  - `Synthetic opioids, excl. methadone (T40.4)`
- Monthly count method:
  - Source file has only `12 month-ending` series.
  - Dashboard uses monthly estimates produced by recurrence/deconvolution with first-year seed assumptions.

### CBP / AMO source-specific files

- CBP normalized:
  - `Drug Border Seizures/cbp_fentanyl_aor_monthly_2019_2026_dec.csv`
- AMO normalized:
  - `Drug Border Seizures/amo_fentanyl_branch_monthly_2019_2026_dec.csv`
- Docs copies:
  - `docs/cbp_fentanyl_aor_monthly_2019_2026_dec.csv`
  - `docs/amo_fentanyl_branch_monthly_2019_2026_dec.csv`

### Combined CBP + AMO file

- Combined normalized dataset:
  - `Drug Border Seizures/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv`
- Docs copy:
  - `docs/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv`

## Data build scripts

- CBP builder:
  - `Drug Border Seizures/build_cbp_fentanyl_dataset.py`
- AMO builder:
  - `Drug Border Seizures/build_amo_fentanyl_dataset.py`
- CBP + AMO combined builder:
  - `Drug Border Seizures/build_cbp_amo_combined_fentanyl_dataset.py`
- Overdose builder:
  - `Fentanyl Data/build_state_overdose_monthly_from_vsrr.py`

### Raw CBP/AMO inputs (versioned)

- `Drug Border Seizures/nationwide-drugs-fy19-fy22.csv`
- `Drug Border Seizures/nationwide-drugs-fy23-fy26-dec.csv`
- `Drug Border Seizures/amo-drug-seizures-fy19-fy22.csv`
- `Drug Border Seizures/amo-drug-seizures-fy23-fy26-dec.csv`

Rebuild combined ops dataset:

```bash
python3 "Drug Border Seizures/build_cbp_amo_combined_fentanyl_dataset.py"
cp "Drug Border Seizures/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv" docs/
```

Rebuild state-level overdose dataset:

```bash
python3 "Fentanyl Data/build_state_overdose_monthly_from_vsrr.py"
```

## Overdose integration behavior

### Streamlit

- Loader validates required columns (`state_abbr`, `state_name`, `variable`, `date`, `count`) and derives:
  - `year`
  - `month_abbr`
- Sidebar filters:
  - variable
  - year
  - month
  - states/territories
  - metric mode (`Total deaths` / `Average monthly deaths`)
  - optional 12-month rolling average overlay
- Outputs:
  - state choropleth map
  - national monthly trend (summed from selected state rows)
  - state totals table + download

### GitHub Pages

- Added data source option:
  - `Synthetic opioid overdose deaths (state-level estimated monthly)`
- Added overdose control panel:
  - variable filter
  - year filter (+ all/clear)
  - month filter
  - state/territory filter (+ all/clear)
  - metric mode radio
  - rolling-average toggle
- JS normalizer parses `date` and state columns for filters and plotting.

## Notes on design consistency

- Existing color scale direction remains:
  - light colors = lower values
  - dark colors = higher values
- Overdose choropleth now uses state-level estimated monthly counts.

## Run and verify

### Streamlit

```bash
.venv/bin/streamlit run "Fentanyl Data/nflis_state_drug_dashboard.py"
```

### Docs local test

```bash
python3 -m http.server 8765 --directory docs
```

Then open:

- `http://localhost:8765/index.html`

## Cleanup + repo hygiene status

- Added root `.gitignore` to suppress local-only non-dashboard data/workspaces and cache artifacts.
- `docs/nflis_state_year_drug_counts_2017_2022.csv` is not used by the current `docs/index.html` app and can remain out of the active docs runtime set.
- Streamlit reproducibility requires all of these files to be present in git:
  - `NFLIS_Drug_DQS_2026_03_03_13_26_55.csv`
  - `Drug Border Seizures/cbp_fentanyl_aor_monthly_2019_2026_dec.csv`
  - `Drug Border Seizures/amo_fentanyl_branch_monthly_2019_2026_dec.csv`
  - `Drug Border Seizures/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv`
  - `VSRR_Provisional_Drug_Overdose_Death_Counts.csv`
  - `Fentanyl Data/state_synthetic_opioid_overdose_monthly_counts_estimated.csv`
