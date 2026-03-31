# Contributing to EWasteTradeFlow

Thank you for your interest in contributing. This project depends on community input — especially from people with domain expertise in e-waste policy, trade data, and environmental enforcement.

---

## Ways to contribute

### 1. Data corrections and source updates

The most valuable contributions are often data-related:

- **Outdated HS code mappings** — The `hs_to_ewaste_category.csv` seed file maps Comtrade HS codes to UN e-waste categories. If a mapping is wrong or a new HS code is missing, open an issue with the correct mapping and a citation.
- **Literature flag corrections** — The `literature_flags.csv` file records countries with documented informal e-waste processing. If a country's status has changed (e.g., improved regulation), open an issue with the citation.
- **New data sources** — If you know of a national or regional e-waste dataset not covered here, open an issue describing the source, its coverage, and its access method.

For data changes, use the [Data Correction issue template](.github/ISSUE_TEMPLATE/data-correction.md).

### 2. Bug reports

If you find incorrect data displayed on the platform, a broken API endpoint, or a UI issue, open a [Bug Report](.github/ISSUE_TEMPLATE/bug-report.md).

Please include:
- What you expected to see
- What you actually saw
- Steps to reproduce
- Browser/environment (for frontend issues)

### 3. Feature requests

Open a [Feature Request](.github/ISSUE_TEMPLATE/feature-request.md). Describe the use case before proposing a solution — this project is built for a specific audience (policy researchers, journalists, program managers) and new features are evaluated against their needs.

### 4. Code contributions

See the development setup in the main [README](README.md).

**Before opening a PR:**
- Check that an issue exists for the change. For non-trivial changes, discuss the approach in the issue first.
- Run the test suite (`pytest` for the API/pipeline, `npm test` for the frontend).
- For data pipeline changes, run `dbt test` to verify no data quality tests are broken.
- For dbt model changes, include the output of `dbt test` in your PR description.

---

## Development workflow

```
main        — stable, reflects deployed state
dev         — integration branch for in-progress work
feat/*      — feature branches, opened against dev
fix/*       — bug fix branches
data/*      — data source / seed file update branches
```

Open PRs against `dev`, not `main`. `main` is updated via release PRs from `dev`.

---

## Commit message format

We use a lightweight conventional commits style:

```
<type>: <short description>

[optional body]
```

Types: `feat`, `fix`, `data`, `docs`, `refactor`, `test`, `chore`

Examples:
```
feat: add OECD transboundary flow ingestion script
fix: correct ISO3 code for Serbia in Comtrade parser
data: update literature flag for China post-2018 import ban
docs: add PRS methodology page
```

---

## Data citation requirements

This project aggregates third-party data. When contributing data-related changes:

- Always cite the primary source (UN, World Bank, OECD, peer-reviewed paper)
- Include the access date for data you retrieved manually
- Do not commit raw data files from third-party sources — commit only the transformation logic and seed mappings

---

## Code of conduct

Be direct and evidence-based. Disputes about data methodology should be resolved by citing sources, not by volume. Treat all contributors with respect.

---

## Questions?

Open a [Discussion](https://github.com/VikramMenon09/ewaste-tradeflow/discussions) for anything that isn't a bug or feature request.
