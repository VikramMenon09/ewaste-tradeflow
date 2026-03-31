# Processing Risk Score (PRS) — Methodology

The Processing Risk Score (PRS) is a composite index that estimates the likelihood that e-waste imported by a country is handled informally — through open burning, acid leaching, or manual dismantling without worker protection.

**Scale:** 1–10, where 10 = highest processing risk (worst conditions)

**Important:** The PRS is a modeled estimate, not an official measure. It should be used to identify patterns and prioritize investigation, not to make definitive legal or regulatory claims about specific countries.

---

## Formula

```
PRS = 0.30 × Capacity Score
    + 0.35 × Enforcement Score
    + 0.20 × Income Score
    + 0.15 × Literature Flag Score
```

---

## Components

### Capacity Score (weight: 0.30)

Measures the mismatch between a country's formal e-waste processing capacity and its e-waste import volume.

```
capacity_ratio = import_volume_mt / formal_capacity_mt
```

| Capacity Ratio | Score |
|---|---|
| < 0.5 (large surplus capacity) | 2 |
| 0.5 – 1.0 | 4 |
| 1.0 – 1.5 | 6 |
| 1.5 – 2.0 | 8 |
| > 2.0 (severely overwhelmed) | 10 |
| No formal capacity data | 8 (conservative default) |

**Data sources:** `formal_capacity_mt` from UN Global E-waste Monitor; `import_volume_mt` from Comtrade + OECD trade flows.

---

### Enforcement Score (weight: 0.35)

Derived from three World Bank Governance Indicators: Rule of Law (RL), Government Effectiveness (GE), and Control of Corruption (CC). Each ranges from approximately –2.5 (worst) to +2.5 (best).

```
wb_composite = (RL + GE + CC) / 3
enforcement_score = 10 − ((wb_composite + 2.5) / 5.0 × 9)
```

This maps –2.5 → 10 (worst governance, highest risk) and +2.5 → 1 (best governance, lowest risk).

Enforcement receives the highest weight (0.35) because it is the strongest predictor of informal processing outcomes in the academic literature.

**Data source:** World Bank Governance Indicators API (annual). Note that WBI data lags 1–2 years; the most recent available vintage within a 2-year window is used.

**Key citations:**
- Lepawsky, J. & Billah, M. (2011). Making chains that (un)make things: waste–value relations and the Bangladeshi rubbish electronics industry. *Geografiska Annaler*, 93(2), 121–139.
- Ongondo, F.O., Williams, I.D., & Cherrett, T.J. (2011). How are WEEE doing? A global review of the management of electrical and electronic wastes. *Waste Management*, 31(4), 714–730.

---

### Income Score (weight: 0.20)

Based on World Bank income classification. A proxy for informal sector size, worker protection legislation, and access to formal recycling infrastructure.

| World Bank Classification | Score |
|---|---|
| High income | 2 |
| Upper middle income | 4 |
| Lower middle income | 7 |
| Low income | 10 |

The non-linear scoring (jump from 4 to 7 between upper-middle and lower-middle) reflects the sharper risk gradient documented in the literature at this income threshold.

**Data source:** World Bank Country and Lending Groups classification (annual).

---

### Literature Flag Score (weight: 0.15)

A categorical modifier based on documented evidence of informal e-waste processing in peer-reviewed literature or major NGO investigations.

| Flag Level | Score | Criteria |
|---|---|---|
| None | 1 | No documented informal processing |
| Documented | 6 | Evidence of informal processing in at least one peer-reviewed paper or major NGO report |
| Major hub | 10 | Internationally recognized informal processing site with multiple independent studies |

This is the most subjective component and carries the lowest weight. It is maintained as a seed file (`seeds/literature_flags.csv`) requiring peer-reviewed citations for any entry. It is versioned — changes require a PR with citations.

---

## Composite score calculation

```sql
prs_score = GREATEST(1.0, LEAST(10.0,
    0.30 * capacity_score
    + 0.35 * enforcement_score
    + 0.20 * income_score
    + 0.15 * literature_score
))
```

If any component is missing, the remaining components are renormalized to sum to 1.0 and a `data_completeness` field (0.0–1.0) is attached to the score.

---

## Score interpretation

| Score Range | Risk Level | UI Color |
|---|---|---|
| 1.0 – 3.9 | Low | Green |
| 4.0 – 6.9 | Moderate | Amber |
| 7.0 – 8.9 | High | Orange |
| 9.0 – 10.0 | Severe | Red |

---

## Versioning

The PRS formula and component weights are versioned via the `methodology_version` field on every `processing_risk_scores` record. When the formula changes:

1. Bump `prs_methodology_version` in `dbt_project.yml`
2. Document the change in this file under a dated "Version history" section
3. All prior scores retain their original `methodology_version` for auditability

---

## Known limitations

- **No device-level resolution.** The PRS applies to all e-waste flows to a country, regardless of what specific devices are imported.
- **Formal capacity data is sparse.** Many countries do not report to the UN Monitor. The conservative default of 8 when capacity data is missing means high-volume importers with no data get a high PRS. This is intentional.
- **Governance indicators lag.** WBI data may not reflect recent regulatory improvements or deteriorations.
- **Literature flags are not exhaustive.** Only countries with published evidence are flagged. Absence of a flag does not imply absence of informal processing.
- **HS code mapping introduces uncertainty.** For MEDIUM and LOW confidence HS codes, the `waste_fraction_scalar` is an estimate. See [`hs-category-mapping.md`](hs-category-mapping.md).

---

## Version history

| Version | Date | Changes |
|---|---|---|
| 1 | March 2026 | Initial release. Weights: Capacity 0.30, Enforcement 0.35, Income 0.20, Literature 0.15. |
