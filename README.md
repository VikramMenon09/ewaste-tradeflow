# EWasteTradeFlow

**Map the global flow of electronic waste. Connect the data to the trade systems and economic incentives that drive it.**

EWasteTradeFlow is an open-source analytics platform that aggregates e-waste data from the UN, World Bank, and OECD into a single system — showing where waste originates, how it moves between countries, and what policy and compliance gaps let it end up in places it shouldn't.

> Built for policy researchers, journalists, and circular economy programs who need credible, citable data.

---

## What it does

| Feature | Description |
|---|---|
| **Interactive world map** | Choropleth showing e-waste generation, export intensity, or Processing Risk Score by country |
| **Trade flow diagram** | Sankey diagram of the top 20 bilateral trade routes by estimated e-waste volume |
| **Basel compliance flags** | Highlights routes that violate (or likely violate) the Basel Convention Ban Amendment |
| **Processing Risk Score (PRS)** | A 1–10 composite score per destination country based on formal recycling capacity, governance quality, income class, and literature evidence |
| **Country profiles** | 10-year time series of generation, formal collection rate, top export/import partners |
| **Report generation** | Downloadable PDF and CSV reports for researchers and advocates |
| **Embeddable widgets** | Iframe-ready map for publishers, no login required |

---

## Data sources

| Source | What it provides | Update cadence |
|---|---|---|
| [UN Global E-waste Monitor](https://ewastemonitor.info/) | Generation by country, formal collection rates | Every 2–3 years |
| [World Bank Comtrade](https://comtradeplus.un.org/) | Bilateral trade flows by HS commodity code | Annual |
| [OECD Waste Statistics](https://stats.oecd.org/) | Transboundary movement data for OECD members | Annual |
| [UNEP Basel Convention](https://www.basel.int/) | Country treaty membership and Ban Amendment ratification | Semi-static |
| [World Bank Governance Indicators](https://info.worldbank.org/governance/wgi/) | Rule of law, enforcement effectiveness (PRS component) | Annual |

All raw source data is stored immutably. Every figure on the platform links back to its source and vintage year. Estimated or modeled values are visually distinguished from officially reported figures.

---

## Architecture overview

```
ewaste-tradeflow/
├── frontend/          React + TypeScript + MapLibre GL + D3.js
├── api/               Python FastAPI (async)
├── data-pipeline/     Ingestion scripts + dbt transformation pipeline
│   ├── ingestion/     Per-source Python fetch/parse scripts
│   └── dbt/           Staging → Intermediate → Mart transformation models
├── docs/              Architecture decisions, data methodology, API notes
└── infra/             Docker Compose for local development
```

**Stack at a glance:**
- Frontend: React, TypeScript, Vite, MapLibre GL JS, D3.js, Zustand, React Query
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0 async, asyncpg
- Database: PostgreSQL 16 + PostGIS
- Pipeline: dbt-core, pandas, pyarrow
- Storage: S3-compatible object storage (raw data lake)
- Auth: Auth0
- Hosting: Vercel (frontend) + Railway (API + PostgreSQL)

See [`docs/architecture/`](docs/architecture/) for Architecture Decision Records (ADRs).

---

## Quickstart (local development)

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+
- A [Comtrade API key](https://comtradeplus.un.org/) (free tier: 500 calls/day)

### 1. Clone and configure

```bash
git clone https://github.com/VikramMenon09/ewaste-tradeflow.git
cd ewaste-tradeflow
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Start the database

```bash
docker compose -f infra/docker-compose.yml up postgres -d
```

### 3. Run the data pipeline

```bash
cd data-pipeline
pip install -r requirements.txt

# Dry run to verify API access before writing anything
python ingestion/run_ingestion.py --source comtrade --year 2022 --dry-run

# Full run
python ingestion/run_ingestion.py --source comtrade --year 2022
python ingestion/run_ingestion.py --source oecd --year 2022
python ingestion/run_ingestion.py --source wb_governance --year 2022

# UN Monitor requires a manual file download from https://ewastemonitor.info/
python ingestion/run_ingestion.py --source un_monitor --year 2024 --file /path/to/un_monitor_2024.xlsx
```

### 4. Run dbt transformations

```bash
cd data-pipeline/dbt
dbt deps
dbt seed          # Load reference tables (HS codes, PRS weights, literature flags)
dbt run           # Build all models (staging → intermediate → marts)
dbt test          # Validate data quality
```

### 5. Start the API

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs at http://localhost:8000/docs
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

---

## Project status

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Monorepo scaffold, Comtrade ingestion, dbt skeleton | ✅ Complete |
| Phase 1 | All API endpoints live, PRS scoring model | 🔄 In progress |
| Phase 2 | Core frontend: map, Sankey, filters, URL state | Planned |
| Phase 3 | PDF reports, embeddable widgets | Planned |
| Phase 4 | Performance audit, accessibility, public launch | Planned |

---

## Data pipeline details

See [`data-pipeline/README.md`](data-pipeline/README.md) for:
- How each source is ingested
- The HS code → UN e-waste category mapping methodology
- dbt model layer descriptions
- How to add a new data source

---

## Processing Risk Score (PRS) methodology

The PRS is a composite index (1–10, where 10 = highest processing risk) used to assess the likelihood that imported e-waste is handled informally in the destination country.

```
PRS = 0.30 × Capacity Score
    + 0.35 × Enforcement Score  (World Bank Governance Indicators)
    + 0.20 × Income Score
    + 0.15 × Literature Flag Score
```

Full methodology, including component definitions, data sources, and known limitations, is documented in [`docs/data/prs-methodology.md`](docs/data/prs-methodology.md).

**Important:** The PRS is a modeled estimate, not an official measure. It is versioned — changes to the scoring formula are tracked with `methodology_version` on every record.

---

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to:
- Report data errors or outdated source mappings
- Propose new data sources
- Contribute code (frontend, API, or pipeline)
- Run the test suite

---

## License

[MIT](LICENSE) — free to use, modify, and distribute. If you use this data or platform in published research, please cite the underlying sources (UN Global E-waste Monitor, World Bank, OECD) alongside this project.

---

## Acknowledgements

Data provided by the [UN University / UNU-ViE SCYCLE](https://scycle.unu.edu/), [World Bank](https://data.worldbank.org/), and [OECD](https://stats.oecd.org/). PRS literature flags draw on published academic research — see [`docs/data/prs-methodology.md`](docs/data/prs-methodology.md) for citations.
