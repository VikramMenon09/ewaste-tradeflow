# Annual Data Refresh Guide

This document explains how to update EWasteTradeFlow with new-year data. Run this process once per year, typically in Q1 after the prior year's Comtrade and UN Monitor releases.

---

## Prerequisites

- Python 3.11+ with the data pipeline deps installed (`pip install -r data-pipeline/requirements.txt`)
- A configured `.env` file at the repo root (copy from `.env.example`)
- `COMTRADE_API_KEY` set — required for trade flow ingestion
- AWS credentials set — required to upload raw files to S3
- PostgreSQL running and `DATABASE_SYNC_URL` pointing to it
- dbt installed: `pip install dbt-core dbt-postgres`

---

## Step 1 — Ingest automated sources

Run all three API-based sources for the new year. Replace `YYYY` with the target year (typically `current year - 1`).

```bash
cd data-pipeline/ingestion
python run_ingestion.py --source all --year YYYY --run-type manual --triggered-by "your-name"
```

This runs Comtrade, OECD, and World Bank Governance in sequence. Each source logs a summary table on completion.

**Expected output:** `All sources completed successfully.`

If a source fails, re-run it individually:

```bash
# Comtrade only
python run_ingestion.py --source comtrade --year YYYY

# OECD only
python run_ingestion.py --source oecd --year YYYY

# World Bank Governance only
python run_ingestion.py --source wb_governance --year YYYY
```

Use `--dry-run` to validate connectivity and record counts without writing anything:

```bash
python run_ingestion.py --source all --year YYYY --dry-run
```

---

## Step 2 — Ingest manual sources

### UN Global E-waste Monitor (required)

The UN Monitor is published as an Excel workbook — it cannot be fetched automatically.

1. Download the latest edition from the GEM website (link in `docs/data/prs-methodology.md §1`)
2. Save it anywhere accessible, e.g. `/tmp/gem_2024.xlsx`
3. Run:

```bash
python run_ingestion.py --source un_monitor --year YYYY --file /tmp/gem_2024.xlsx
```

### Basel Convention status (if updated)

The Basel Convention signatory/ratification list changes infrequently. Check the Basel Convention website for updates; if there are changes:

1. Update `data-pipeline/dbt/seeds/literature_flags.csv` with new country status
2. Run the ingestion to replace the static reference data:

```bash
python run_ingestion.py --source basel --file /path/to/updated_basel_status.csv
```

---

## Step 3 — Run dbt transformations

After all sources are ingested, run the full dbt pipeline to refresh staging, intermediate, and mart tables:

```bash
cd data-pipeline/dbt

# Refresh seeds (authoritative CSV mappings)
dbt seed --target production

# Run all models
dbt run --target production

# Validate data quality
dbt test --target production
```

All tests should pass. Common failures and their fixes:

| Test failure | Likely cause | Fix |
|---|---|---|
| `not_null` on `trade_flows.volume_tonnes` | Comtrade returned null-value records | Re-run with `--year` and check Comtrade API quota |
| `accepted_values` on `confidence_tier` | New tier value from source | Update `schema.yml` accepted values list |
| `unique` on `countries.iso3` | Duplicate country inserted | Check `run_ingestion.py` deduplication logic |

---

## Step 4 — Update the data dictionary version

Open `frontend/src/app/pages/DataDictionaryPage.tsx` and update the two constants at the top:

```ts
const DATA_DICT_VERSION = '2.0'   // increment major if schema changed, minor if data only
const LAST_UPDATED = 'March 2027' // month + year of this refresh
```

Commit this change with a message like:
```
chore: bump data dictionary to v2.0 for 2026 data refresh
```

---

## Step 5 — Invalidate the API cache

After dbt runs, the Redis cache will serve stale data until it expires (24 hours). Invalidate it immediately:

```bash
curl -X POST "${API_URL}/api/v1/internal/cache/invalidate" \
  -H "X-Service-Key: ${CACHE_INVALIDATION_KEY}"
```

If the invalidation endpoint is unreachable, the cache will self-expire within 24 hours.

---

## Step 6 — Verify the refresh

1. Open the app in a browser
2. Set the year slider to the new year — choropleth data should appear (not gray)
3. Open a country panel — generation chart should include the new year
4. Check the Sankey diagram — trade flows for the new year should be visible
5. Download a PDF report — confirm it references the new year in the header

---

## Troubleshooting

**Comtrade returns 0 records for a recent year**
Comtrade typically lags 12–18 months. If YYYY is within 18 months of today, Comtrade may not have published it yet. Check `https://comtradedeveloper.un.org` for release status.

**OECD returns 404 for a year**
OECD ENV_WASTE_TRAN data lags 2–3 years. This is expected — the fetch returns an empty DataFrame silently.

**dbt test fails with `schema_mismatch`**
A source changed its column names. Update the corresponding `stg_*.sql` model in `data-pipeline/dbt/models/staging/` to remap the new column names.

**Pipeline ran but API still shows old year as latest**
The `mart_choropleth_cache` and `mart_sankey_cache` tables may not have been refreshed. Re-run `dbt run --select marts.*`.
