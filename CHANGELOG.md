# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Phase 0: Monorepo scaffold with full directory structure
- Comtrade Plus API v2 ingestion client with pagination and rate limit backoff
- HS-to-UN-e-waste-category seed mapping (52 HS codes, confidence tiers, waste fraction scalars)
- Literature flags seed (15 countries, peer-reviewed citations)
- Income classification PRS weight seed
- dbt project: staging → intermediate → mart transformation layers
- `int_trade_flows_unified` — central reconciliation model with Basel compliance flagging
- `mart_choropleth_cache` and `mart_sankey_cache` — pre-aggregated for API performance
- `run_ingestion.py` CLI with dry-run support, rich terminal output, and audit logging
- S3 upload utility with immutable timestamped Parquet keys
- Pipeline run audit log (`catalog.py`)
- Docker Compose for local development (PostgreSQL/PostGIS + Redis)
- `.env.example` documenting all required environment variables
