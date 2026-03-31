# HS Code to UN E-waste Category Mapping

Comtrade trade data uses the Harmonized System (HS) commodity code classification. The UN Global E-waste Monitor uses 6 broad e-waste categories. These two taxonomies do not align directly — this document explains how we bridge them.

---

## UN e-waste categories

The 6 categories used by the UN Monitor (from the Global E-waste Monitor 2024):

| Code | Category | Examples |
|---|---|---|
| 1 | Temperature exchange equipment | Refrigerators, freezers, air conditioners, heat pumps |
| 2 | Screens and monitors | Televisions, monitors, laptops (screen component), tablets |
| 3 | Lamps | Fluorescent lamps, LED lamps, high-intensity discharge lamps |
| 4 | Large equipment | Washing machines, electric stoves, photovoltaic panels, large medical equipment |
| 5 | Small equipment | Vacuum cleaners, microwaves, small medical devices, power tools |
| 6 | Small IT and telecommunications | Mobile phones, GPS devices, routers, computers, printers |

---

## HS codes used in this project

We pull 10 HS code families from Comtrade. Their mapping confidence varies:

### HIGH confidence — explicit waste/scrap codes

| HS Code | Description | UN Category |
|---|---|---|
| 8549 | Electrical and electronic waste and scrap (HS 2022+) | Mixed (all categories) |
| 8548 | Waste/scrap of primary cells, batteries, electrical assemblies (HS 2017) | Mixed (all categories) |

These codes were introduced specifically for e-waste trade. Volume counted at 100% (`waste_fraction_scalar = 1.0`).

### MEDIUM confidence — IT equipment with significant secondhand/waste fraction

| HS Code | Description | UN Category | Waste Fraction |
|---|---|---|---|
| 8471.30 | Portable computers (laptops, tablets) | 6 | ~12% |
| 8471.41 | Desktop computers | 6 | ~10% |
| 8471.60 | Monitors and display units | 2 | ~15% |
| 8471.xx | Other computer equipment | 6 | 5–10% |
| 8472.xx | Office machines (copiers, fax, ATMs) | 5 | 12–20% |

These HS codes include both new goods trade and secondhand/end-of-life trade. The `waste_fraction_scalar` represents the estimated fraction of trade volume that is e-waste, derived from UN Monitor methodology appendices.

### LOW confidence — industrial machinery with small e-waste fraction

| HS Code | Description | UN Category | Waste Fraction |
|---|---|---|---|
| 8473.xx | Parts for computers and office machines | 6 | 3–5% |
| 8474.xx–8479.xx | Industrial and miscellaneous machinery | Various | 1–10% |

These codes cover broad categories of machinery. Their e-waste fraction is small and poorly characterized. Volumes are adjusted by `waste_fraction_scalar` and flagged with `mapping_confidence = 'LOW'` in the UI.

---

## Waste fraction scalar

For MEDIUM and LOW confidence codes, raw trade volume is multiplied by a `waste_fraction_scalar` to produce `estimated_ewaste_volume_mt`:

```
estimated_ewaste_volume_mt = volume_mt × waste_fraction_scalar
```

This is the figure used in Sankey diagrams and PRS calculations. The raw `volume_mt` is also retained for transparency.

**Scalars are derived from:**
- UN Global E-waste Monitor 2024, Chapter 4 (methodology appendix)
- Baldé et al. (2017), UNU-IAS e-waste data methodology
- Expert judgment for codes where no published estimate exists

---

## Known ambiguities

**HS 8473.30 (computer parts including circuit boards):** Contains some high-value e-waste (printed circuit boards, stripped for precious metals) but is mostly new components trade. Mapped to LOW confidence with `waste_fraction_scalar = 0.05`. High-volume flows to known informal processing destinations are flagged separately.

**HS 8477.80 (cable granulators):** Cable shredding and granulation equipment used in e-waste recycling appears here. Not e-waste itself, but relevant to processing infrastructure mapping. Low waste fraction for the code overall but flagged in notes.

**HS 8471.60 CRT monitors:** CRT monitors are a legacy issue — heavily exported from OECD countries to developing markets in the 2000s and 2010s. Current data likely undercounts this because many CRT flows were mislabeled as "secondhand goods." The `waste_fraction_scalar = 0.15` is conservative.

---

## What is NOT covered

The following e-waste categories are **not well-represented** in Comtrade at HS 4-digit level and are therefore underrepresented in this platform's trade flow data:

- **Temperature exchange equipment (category 1):** Refrigerators and ACs are under HS 8418/8415, which also includes large volumes of new goods. Not included due to very low mapping confidence.
- **Lamps (category 3):** Under HS 8539/8543. Not included — e-waste fraction is negligible in trade data.
- **Large equipment (category 4):** Washing machines (HS 8450), ovens (HS 8516), solar panels (HS 8541). Not included for MVP — high new goods fraction, minimal trade in end-of-life units.

Generation data for all 6 categories is available from the UN Monitor. The trade flow gap is documented in the UI for affected countries.

---

## How to improve the mapping

1. If you have access to HS 6-digit data (Comtrade Plus subscription), the mapping accuracy improves significantly — several MEDIUM codes can be split into HIGH and LOW confidence sub-codes.
2. National customs data (where available) sometimes includes end-of-life classifications not present in Comtrade.
3. Corrections or additions to the mapping should be submitted via the [Data Correction issue template](../../.github/ISSUE_TEMPLATE/data-correction.md) with citations.
