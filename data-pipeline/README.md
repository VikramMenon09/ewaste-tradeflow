# Data Pipeline

The data pipeline ingests e-waste data from five sources, normalizes it to a common schema, and loads it into PostgreSQL via dbt transformations.

---

## How it works

```
External APIs / Manual Files
        ↓
ingestion/  — per-source Python fetch + parse scripts
        ↓  → Parquet files in S3 (raw/, immutable, timestamped)
        ↓
dbt/staging/       — type casting, ISO3 normalization, source tagging
dbt/intermediate/  — HS code mapping, source reconciliation, Basel flags
dbt/marts/         — final application tables + pre-aggregated API caches
        ↓
PostgreSQL (API reads mart tables directly)
```

Every raw file written to S3 is immutable and timestamped. Transformations are applied in dbt — never on the raw data itself.

---

## Data sources

| Source | Script | Schedule | Notes |
|---|---|---|---|
| UN Global E-waste Monitor | `ingestion/sources/un_monitor/` | Manual (every 2–3 years) | Excel file download from [ewastemonitor.info](https://ewastemonitor.info/) |
| World Bank Comtrade | `ingestion/sources/comtrade/` | Weekly (automated) | Requires API key from [comtradeplus.un.org](https://comtradeplus.un.org/) |
| OECD.Stat | `ingestion/sources/oecd/` | Weekly (automated) | No API key needed |
| World Bank Governance Indicators | `ingestion/sources/wb_governance/` | Annual (automated) | No API key needed |
| Basel Convention status | `ingestion/sources/basel/` | Manual (annual review) | Static CSV from UNEP, updated via PR |

---

## Running the pipeline

```bash
cd data-pipeline
pip install -r requirements.txt

# Single source, single year
python ingestion/run_ingestion.py --source comtrade --year 2022

# Historical backfill
python ingestion/run_ingestion.py --source comtrade --start-year 2010 --end-year 2022

# All automated sources for a year
python ingestion/run_ingestion.py --source all --year 2022

# Manual source (UN Monitor requires a downloaded file)
python ingestion/run_ingestion.py --source un_monitor --year 2024 --file /path/to/file.xlsx

# Dry run — logs what would happen without writing anything
python ingestion/run_ingestion.py --source comtrade --year 2022 --dry-run
```

Every run is logged to the `pipeline_runs` table in PostgreSQL. Use `--run-type scheduled` for cron runs and `--triggered-by <name>` for the audit trail.

---

## dbt models

### Layer structure

```
dbt/models/
├── staging/          One model per source. Views only. Type casting + cleaning.
├── intermediate/     Cross-source joins, HS mapping, compliance flags.
└── marts/            Final tables consumed by the API + materialized caches.
```

### Running dbt

```bash
cd data-pipeline/dbt

dbt seed                       # Load seed reference tables
dbt run                        # Build all models
dbt run --select staging       # Build only staging layer
dbt run --select marts         # Build only mart layer
dbt test                       # Run all data quality tests
dbt docs generate && dbt docs serve   # Browse lineage graph
```

### Key models

| Model | Layer | Description |
|---|---|---|
| `stg_comtrade` | Staging | Normalized Comtrade trade flows |
| `stg_un_monitor` | Staging | UN Monitor generation and collection rate data |
| `stg_oecd_flows` | Staging | OECD transboundary movement data |
| `int_trade_flows_unified` | Intermediate | **Central reconciliation model.** Joins Comtrade + OECD, applies HS-to-category mapping, computes Basel compliance flags. All downstream trade analysis depends on this. |
| `int_prs_components` | Intermediate | Assembles PRS input variables per country-year |
| `mart_trade_flows` | Marts | Final trade flow table (API reads this) |
| `mart_ewaste_generation` | Marts | Final generation table (API reads this) |
| `mart_processing_risk_scores` | Marts | Computed PRS per country-year |
| `mart_choropleth_cache` | Marts | **Pre-aggregated choropleth data.** One row per (country, year, metric). Queried by the `/map/choropleth` API endpoint. |
| `mart_sankey_cache` | Marts | **Pre-ranked Sankey routes.** Top 50 routes per year. Queried by the `/map/flows/sankey` endpoint. |

---

## Seed files

Seed files are static reference tables committed to git. They are the authoritative source for mappings and classifications that don't come from an API.

| File | Description |
|---|---|
| `seeds/hs_to_ewaste_category.csv` | Maps 52 Comtrade HS codes to 6 UN e-waste categories. Includes `mapping_confidence` (HIGH/MEDIUM/LOW) and `waste_fraction_scalar`. **This is the highest-impact single file in the pipeline.** |
| `seeds/income_class_prs_weights.csv` | PRS income component scores by World Bank income classification |
| `seeds/literature_flags.csv` | Countries with documented informal e-waste processing (peer-reviewed citations required) |

To update a seed file, edit the CSV and run `dbt seed`. All changes must include citations in the PR description.

---

## HS code mapping methodology

Comtrade uses HS commodity codes; the UN Monitor uses 6 broad e-waste categories. Mapping between them is imperfect — see [`docs/data/hs-category-mapping.md`](../docs/data/hs-category-mapping.md) for the full methodology.

**Confidence tiers:**
- `HIGH` — HS codes that explicitly cover waste/scrap of electrical equipment (8548, 8549). Full volume counted.
- `MEDIUM` — IT equipment codes (8471, 8472) where some fraction is secondhand/waste. A `waste_fraction_scalar` is applied.
- `LOW` — Industrial machinery codes with a small e-waste fraction. Volume is adjusted and flagged in the UI as an estimate.

---

## Adding a new data source

1. Create a new directory under `ingestion/sources/<source_name>/`
2. Implement `fetch.py` (API client), `parse.py` (normalization), and `schema.py` (column contracts)
3. Add a `__init__.py` that exports the client and `normalize` function
4. Add a handler in `run_ingestion.py` under `_run_<source_name>()`
5. Create a staging model in `dbt/models/staging/stg_<source_name>.sql`
6. Update `dbt/models/sources.yml` to register the new raw table
7. Open a PR with a description of the source, its coverage, and its license

---

## Environment variables

See [`.env.example`](../.env.example) at the repo root for all required variables.

The most important for the pipeline:

```bash
DATABASE_SYNC_URL      # PostgreSQL connection string (sync driver for ingestion scripts)
S3_BUCKET              # Raw data lake bucket name
S3_ENDPOINT_URL        # Leave blank for AWS S3; set for MinIO or R2
COMTRADE_API_KEY       # Required for Comtrade source
```
