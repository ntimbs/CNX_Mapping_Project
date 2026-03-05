# CNX Dashboard Context

Last updated: 2026-03-05

This file is a persistent context log for the active dashboard implementation in this repository.

## Current dashboard surfaces

- Streamlit app: `Fentanyl Data/nflis_state_drug_dashboard.py`
- GitHub Pages app: `docs/index.html`

Both dashboards currently support the following data sources:

1. NFLIS state reports (all drugs)
2. Synthetic opioid overdose deaths (national)
3. CBP + AMO fentanyl seizures (combined)
4. CBP fentanyl seizures (Field Office/Sector)
5. AMO fentanyl seizures (Branch)

## Key data files

### NFLIS

- Primary NFLIS file used in both dashboards:
  - `NFLIS_Drug_DQS_2026_03_03_13_26_55.csv`

### Overdose

- Source file added by user:
  - `Fentanyl Data/overdoseDeathsData_cleaned.csv`
- Docs copy for GitHub Pages:
  - `docs/overdoseDeathsData_cleaned.csv`
- Schema:
  - `variable, date, count`
- Important limitation:
  - This file is national monthly data and does not include state-level geographic columns.
  - Dashboard rendering for this source is therefore:
    - single U.S. marker on map
    - monthly trend chart
    - monthly table + CSV download

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

Rebuild combined ops dataset:

```bash
python3 "Drug Border Seizures/build_cbp_amo_combined_fentanyl_dataset.py"
cp "Drug Border Seizures/cbp_amo_fentanyl_location_monthly_2019_2026_dec.csv" docs/
```

## Overdose integration behavior

### Streamlit

- Loader validates required columns (`variable`, `date`, `count`) and derives:
  - `year`
  - `month_abbr`
- Sidebar filters:
  - variable
  - year
  - month
  - metric mode (`Total deaths` / `Average monthly deaths`)
  - optional 12-month rolling average overlay
- Outputs:
  - national marker map
  - monthly trend
  - monthly table + download

### GitHub Pages

- Added data source option:
  - `Synthetic opioid overdose deaths (national)`
- Added overdose control panel:
  - variable filter
  - year filter (+ all/clear)
  - month filter
  - metric mode radio
  - rolling-average toggle
- JS normalizer parses `date` and derives year/month for filters and plotting.

## Notes on design consistency

- Existing color scale direction remains:
  - light colors = lower values
  - dark colors = higher values
- Overdose view intentionally avoids choropleth rendering due to missing state-level data.

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

## Pending context-sensitive files (outside this commit scope)

There are additional untracked datasets/scripts in this repo that are not part of this dashboard commit.
When committing, stage only dashboard-relevant files unless requested otherwise.
