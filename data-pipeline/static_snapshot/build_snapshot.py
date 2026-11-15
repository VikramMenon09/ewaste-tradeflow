"""
Build a static JSON data snapshot for the frontend's static-data mode.

This runs the parts of the pipeline that do NOT need PostgreSQL, a UN Comtrade
API key, AWS or Auth0, and writes JSON files that match the API's response
shapes so the frontend can be hosted as a plain static site.

Sources (all keyless, fetched live when this script runs):
  - OECD Data Explorer, dataflow OECD.ENV.EPI:DSD_EWASTE@DF_EWASTE
    (e-waste generated / collected). Preferred generation source.
  - UN SDG Global Database, indicator 12.4.2 (EN_EWT_GENV, EN_EWT_GENPCAP,
    EN_EWT_COLLR; custodian UNITAR, publisher of the Global E-waste Monitor).
    Country-reported observations (Nature = "C") for countries OECD lacks,
    Both sources pass a plausibility screen (see screen_observations).
  - World Bank population (SP.POP.TOTL) for that screen.
  - World Bank Worldwide Governance Indicators (source 3: GOV_WGI_RL.EST,
    GOV_WGI_GE.EST, GOV_WGI_CC.EST) -> PRS enforcement component.
  - World Bank country metadata API -> income classification (PRS income
    component).
  - UN Treaty Collection, chapter XXVII-3 (Basel Convention) and XXVII-3-a
    (Ban Amendment) -> Basel party / Ban ratification flags.
  - UN M49 standard (UN Statistics Division) -> names, ISO3, region, subregion.
  - dbt seeds in ../dbt/seeds (income_class_prs_weights, literature_flags).

Transformations ported from the dbt models (Postgres SQL -> DuckDB):
  - int_generation_filled: linear interpolation + edge carry, flagged
    `is_interpolated` / confidence_tier 'interpolated'.
  - stg_wb_governance: composite governance -> enforcement score [0, 1].
  - int_prs_components / mart_processing_risk_scores: PRS v1.

Not produced (they depend on UN Comtrade bilateral trade data):
  exports, imports, net_trade, export_intensity, compliance_rate, the Sankey
  diagram, and country trade partners. Without trade data the PRS capacity
  component uses the formal collection rate only (the same branch the dbt
  model takes when import volume is zero).

Usage:
    pip install pandas duckdb lxml requests
    python data-pipeline/static_snapshot/build_snapshot.py \
        --out frontend/public/static-data [--cache .snapshot-cache]
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import logging
import re
import shutil
from pathlib import Path

import duckdb
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("snapshot")

HERE = Path(__file__).resolve().parent
SEEDS = HERE.parent / "dbt" / "seeds"

MIN_YEAR, MAX_YEAR = 2010, 2024  # dbt_project.yml vars
PRS_METHODOLOGY_VERSION = 1
W_CAPACITY, W_ENFORCEMENT, W_INCOME, W_LITERATURE = 0.35, 0.35, 0.20, 0.10  # int_prs_components

URLS = {
    "m49": "https://unstats.un.org/unsd/methodology/m49/overview/",
    "sdg": "https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Series/Data?seriesCode={code}&pageSize=20000",
    "oecd_ewaste": "https://sdmx.oecd.org/public/rest/data/OECD.ENV.EPI,DSD_EWASTE@DF_EWASTE,1.0/all?format=csv",
    "wb_countries": "https://api.worldbank.org/v2/country?format=json&per_page=500",
    "population": "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&per_page=20000&date=2000:2024",
    "wgi": "https://api.worldbank.org/v2/country/all/indicator/{code}?source=3&format=json&per_page=20000&date={start}:{end}",
    "basel": "https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no=XXVII-3&chapter=27&clang=_en",
    "ban": "https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no=XXVII-3-a&chapter=27&clang=_en",
}

SOURCES = [
    {
        "name": "OECD Data Explorer: Waste - Electrical and electronic equipment (DF_EWASTE)",
        "url": "https://data-explorer.oecd.org/",
        "used_for": "E-waste generated, per capita and collected (preferred source)",
    },
    {
        "name": "UN SDG Global Database, indicator 12.4.2 (custodian: UNITAR, Global E-waste Monitor)",
        "url": "https://unstats.un.org/sdgs/dataportal",
        "used_for": "E-waste generated, per capita, collection rate for countries OECD does not cover",
    },
    {
        "name": "World Bank Worldwide Governance Indicators",
        "url": "https://www.worldbank.org/en/publication/worldwide-governance-indicators",
        "used_for": "PRS enforcement component (Rule of Law, Gov. Effectiveness, Control of Corruption)",
    },
    {
        "name": "World Bank population (SP.POP.TOTL)",
        "url": "https://data.worldbank.org/indicator/SP.POP.TOTL",
        "used_for": "Plausibility screen and derived per capita values for SDG observations",
    },
    {
        "name": "World Bank country classifications",
        "url": "https://datahelpdesk.worldbank.org/knowledgebase/articles/906519",
        "used_for": "Income classification (PRS income component)",
    },
    {
        "name": "UN Treaty Collection: Basel Convention and Ban Amendment status",
        "url": "https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no=XXVII-3&chapter=27&clang=_en",
        "used_for": "Basel party and Ban Amendment ratification flags",
    },
    {
        "name": "UN M49 standard country codes",
        "url": "https://unstats.un.org/unsd/methodology/m49/overview/",
        "used_for": "Country names, ISO3 codes, regions",
    },
    {
        "name": "Project dbt seeds (literature_flags.csv, income_class_prs_weights.csv)",
        "url": "https://github.com/VikramMenon09/ewaste-tradeflow/tree/main/data-pipeline/dbt/seeds",
        "used_for": "PRS literature and income scores",
    },
]

AVAILABLE_METRICS = ["generation", "per_capita", "formal_collection", "prs"]
UNAVAILABLE_METRICS = ["net_trade", "exports", "imports", "export_intensity", "compliance_rate"]

# UN Treaty Collection participant names that differ from UN M49 names
TREATY_NAME_ALIASES = {
    "Bahamas (The)": "BHS",
    "Côte d'Ivoire": "CIV",
    "Czech Republic": "CZE",
    "St. Kitts and Nevis": "KNA",
    "St. Lucia": "LCA",
    "St. Vincent and the Grenadines": "VCT",
}

# Plausibility bounds for country-reported e-waste generation (kg per person)
PER_CAPITA_BOUNDS_KG = (0.2, 40.0)
PARTIAL_SCOPE_PATTERN = r"covers only|batteries and accumulators"

WB_INCOME_MAP = {"HIC": "high", "UMC": "upper_middle", "LMC": "lower_middle", "LIC": "low"}

HEADERS = {"User-Agent": "EWasteTradeFlow-static-snapshot/1.0 (open-source research project)"}


# ─── Fetch helpers (cached on disk so re-runs are reproducible) ──────────────


class Fetcher:
    def __init__(self, cache_dir: Path, refresh: bool):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.refresh = refresh

    def get(self, key: str, url: str) -> bytes:
        path = self.cache_dir / key
        if path.exists() and not self.refresh:
            return path.read_bytes()
        log.info("GET %s", url)
        resp = requests.get(url, headers=HEADERS, timeout=180)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        return resp.content


# ─── Loaders ─────────────────────────────────────────────────────────────────


def load_m49(f: Fetcher) -> pd.DataFrame:
    html = f.get("m49.html", URLS["m49"]).decode("utf-8")
    t = pd.read_html(io.StringIO(html), attrs={"id": "downloadTableEN"})[0]
    t = t[t["ISO-alpha3 Code"].notna()]
    return pd.DataFrame({
        "iso3": t["ISO-alpha3 Code"].str.strip(),
        "m49": t["M49 Code"].astype(int),
        "name": t["Country or Area"].str.strip(),
        "region": t["Region Name"].fillna("Other"),
        "subregion": t["Intermediate Region Name"].fillna(t["Sub-region Name"]).fillna(""),
    }).drop_duplicates("iso3")


def load_population(f: Fetcher, valid_iso3: set[str]) -> pd.DataFrame:
    payload = json.loads(f.get("wb_population.json", URLS["population"]))
    rows = [
        {"iso3": r["countryiso3code"], "year": int(r["date"]), "population": float(r["value"])}
        for r in payload[1]
        if r["countryiso3code"] in valid_iso3 and r["value"]
    ]
    return pd.DataFrame(rows)


def screen_observations(obs: pd.DataFrame, pop: pd.DataFrame, partial_scope_iso3: set[str]) -> tuple[pd.DataFrame, list[dict]]:
    """Drop generation observations that fail a plausibility check.

    The country-reported series mix units and scopes (e.g. SDG values that are
    clearly kilograms labelled as tonnes, or batteries-only totals in both the
    SDG and OECD tables for one country).
    An observation is kept only if its implied generation per person is within
    PER_CAPITA_BOUNDS_KG. The highest national values in the Global E-waste
    Monitor 2024 are around 26 kg/person and the lowest well above 0.2 kg.
    Countries whose SDG footnotes state a partial scope (e.g. "covers only
    computers", "batteries and accumulators wastes") are dropped entirely.
    """
    df = obs.merge(pop, on=["iso3", "year"], how="left")
    implied = df["total_mt"] * 1000 / df["population"]
    lo, hi = PER_CAPITA_BOUNDS_KG
    bad_value = implied.notna() & ((implied < lo) | (implied > hi))
    bad_pc = df["per_capita_kg"].notna() & ((df["per_capita_kg"] < lo) | (df["per_capita_kg"] > hi))
    # A footnote stating a partial scope disqualifies the country's whole series
    # (the same national statistic often appears in both the SDG and OECD tables).
    scope_hit = df["footnote"].fillna("").str.contains(PARTIAL_SCOPE_PATTERN, case=False)
    partial_scope = set(df.loc[scope_hit, "iso3"]) | set(partial_scope_iso3)
    bad_scope = df["iso3"].isin(partial_scope)
    drop = bad_value | bad_pc | bad_scope
    excluded = []
    for iso3, g in df[drop].groupby("iso3"):
        excluded.append({
            "iso3": iso3,
            "years": sorted(int(y) for y in g["year"]),
            "reason": "partial scope per source footnote" if iso3 in partial_scope
            else f"implied generation outside {lo}-{hi} kg/person",
        })
    kept = df[~drop].copy()
    # Derive per capita from World Bank population where the source lacks it
    derived = kept["per_capita_kg"].isna() & kept["population"].notna()
    kept.loc[derived, "per_capita_kg"] = kept.loc[derived, "total_mt"] * 1000 / kept.loc[derived, "population"]
    return kept.drop(columns=["population", "footnote"]), excluded


def load_sdg(f: Fetcher, m49: pd.DataFrame) -> pd.DataFrame:
    m49_to_iso = dict(zip(m49["m49"], m49["iso3"]))
    frames = {}
    for code, col in [("EN_EWT_GENV", "total_mt"), ("EN_EWT_GENPCAP", "per_capita_kg"), ("EN_EWT_COLLR", "collection_pct")]:
        payload = json.loads(f.get(f"sdg_{code}.json", URLS["sdg"].format(code=code)))
        rows = []
        for r in payload["data"]:
            if r["attributes"].get("Nature") != "C":  # country data only, skip regional estimates
                continue
            iso3 = m49_to_iso.get(int(r["geoAreaCode"]))
            if iso3 is None or r["value"] in (None, "", "NaN"):
                continue
            row = {"iso3": iso3, "year": int(r["timePeriodStart"]), col: float(r["value"])}
            if col == "total_mt":
                row["footnote"] = " ".join(r.get("footnotes") or [])
            rows.append(row)
        frames[col] = pd.DataFrame(rows).drop_duplicates(["iso3", "year"])
    df = frames["total_mt"].merge(frames["per_capita_kg"], on=["iso3", "year"], how="outer")
    df = df.merge(frames["collection_pct"], on=["iso3", "year"], how="left")
    rate = df.pop("collection_pct") / 100.0
    df["formal_collection_rate"] = rate.where((rate >= 0) & (rate <= 1))  # >100% = scope mismatch
    df["source"] = "UN SDG 12.4.2 (UNITAR)"
    return df


def load_oecd(f: Fetcher, valid_iso3: set[str]) -> pd.DataFrame:
    raw = pd.read_csv(io.BytesIO(f.get("oecd_ewaste.csv", URLS["oecd_ewaste"])))
    raw = raw[(raw["PRODUCT_CATEGORIES"] == "EE6") & raw["REF_AREA"].isin(valid_iso3)]

    def pick(measure: str, unit: str, name: str) -> pd.DataFrame:
        s = raw[(raw["MEASURE"] == measure) & (raw["UNIT_MEASURE"] == unit)]
        mult = 10 ** s["UNIT_MULT"].fillna(0).astype(int)
        return pd.DataFrame({"iso3": s["REF_AREA"], "year": s["TIME_PERIOD"].astype(int), name: s["OBS_VALUE"] * mult})

    gen = pick("GEN", "T", "total_mt")
    pc = pick("GEN", "KG_PS", "per_capita_kg")
    col = pick("COL", "T", "collected_mt")
    df = gen.merge(pc, on=["iso3", "year"], how="left").merge(col, on=["iso3", "year"], how="left")
    rate = df.pop("collected_mt") / df["total_mt"]
    df["formal_collection_rate"] = rate.where((df["total_mt"] > 0) & (rate <= 1))
    df["source"] = "OECD DF_EWASTE"
    return df


def load_wb_income(f: Fetcher) -> pd.DataFrame:
    payload = json.loads(f.get("wb_countries.json", URLS["wb_countries"]))
    rows = []
    for c in payload[1]:
        inc = WB_INCOME_MAP.get(c["incomeLevel"]["id"])
        if inc:
            rows.append({"iso3": c["id"], "income_classification": inc})
    return pd.DataFrame(rows)


def load_wgi(f: Fetcher, valid_iso3: set[str]) -> pd.DataFrame:
    out = None
    for code, col in [("GOV_WGI_RL.EST", "rule_of_law"), ("GOV_WGI_GE.EST", "gov_effectiveness"), ("GOV_WGI_CC.EST", "control_of_corruption")]:
        payload = json.loads(f.get(f"wgi_{code}.json", URLS["wgi"].format(code=code, start=MIN_YEAR, end=MAX_YEAR)))
        rows = [
            {"iso3": r["countryiso3code"], "year": int(r["date"]), col: r["value"]}
            for r in payload[1]
            if r["countryiso3code"] in valid_iso3 and r["value"] is not None
        ]
        df = pd.DataFrame(rows)
        out = df if out is None else out.merge(df, on=["iso3", "year"], how="outer")
    return out


def _treaty_table(html: bytes) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(html.decode("utf-8", errors="replace")))
    t = next(x for x in tables if x.shape[0] > 30)
    t = t.iloc[1:].copy()  # first row is the header text
    last_col = t.columns[-1]  # ratification / accession / succession date
    t["participant"] = t[0].astype(str).str.replace(r"\s*\d+(,\s*\d+)*$", "", regex=True).str.strip()
    t["action"] = t[last_col]
    return t


def load_basel(f: Fetcher, m49: pd.DataFrame) -> pd.DataFrame:
    name_to_iso = dict(zip(m49["name"], m49["iso3"]))
    name_to_iso.update(TREATY_NAME_ALIASES)

    def parse(key: str) -> dict[str, int]:
        t = _treaty_table(f.get(key + ".html", URLS[key]))
        res = {}
        for _, row in t.iterrows():
            m = re.search(r"(\d{4})", str(row["action"]))
            iso3 = name_to_iso.get(row["participant"])
            if m and iso3:
                res[iso3] = int(m.group(1))
            elif m and row["participant"] != "European Union":
                log.warning("Basel %s: unmatched participant %r", key, row["participant"])
        return res

    parties = parse("basel")
    ban = parse("ban")
    iso = sorted(set(parties) | set(ban))
    return pd.DataFrame({
        "iso3": iso,
        "basel_signatory": [i in parties for i in iso],
        "ratification_year": [parties.get(i) for i in iso],
        "basel_ban_ratified": [i in ban for i in iso],
        "ban_ratification_year": [ban.get(i) for i in iso],
    })


# ─── Transformations (ported dbt SQL) ────────────────────────────────────────

GENERATION_FILLED_SQL = f"""
-- Port of dbt/models/intermediate/int_generation_filled.sql
with observed as (
    select iso3, year, total_mt, per_capita_kg, formal_collection_rate, source,
           'reported' as confidence_tier
    from observed_raw
),
all_years as (select range as year from range({MIN_YEAR}, {MAX_YEAR + 1})),
countries as (select distinct iso3 from observed),
with_gaps as (
    select c.iso3, y.year, o.total_mt, o.per_capita_kg, o.formal_collection_rate, o.confidence_tier
    from countries c cross join all_years y
    left join observed o on o.iso3 = c.iso3 and o.year = y.year
),
w as (
    select *,
        last_value(total_mt ignore nulls) over (partition by iso3 order by year rows between unbounded preceding and current row) as prev_total_mt,
        first_value(total_mt ignore nulls) over (partition by iso3 order by year rows between current row and unbounded following) as next_total_mt,
        last_value(case when total_mt is not null then year end ignore nulls) over (partition by iso3 order by year rows between unbounded preceding and current row) as prev_year,
        first_value(case when total_mt is not null then year end ignore nulls) over (partition by iso3 order by year rows between current row and unbounded following) as next_year,
        last_value(per_capita_kg ignore nulls) over (partition by iso3 order by year rows between unbounded preceding and current row) as prev_pc,
        first_value(per_capita_kg ignore nulls) over (partition by iso3 order by year rows between current row and unbounded following) as next_pc,
        last_value(formal_collection_rate ignore nulls) over (partition by iso3 order by year rows between unbounded preceding and current row) as prev_fcr,
        first_value(formal_collection_rate ignore nulls) over (partition by iso3 order by year rows between current row and unbounded following) as next_fcr,
        max(case when total_mt is not null then year end) over (partition by iso3) as latest_observed_year
    from with_gaps
),
interp as (
    select iso3, year,
        case when total_mt is not null then total_mt
             when prev_total_mt is not null and next_total_mt is not null
                then prev_total_mt + (year - prev_year) * (next_total_mt - prev_total_mt) / nullif(next_year - prev_year, 0)
             when prev_total_mt is not null then prev_total_mt
             when next_total_mt is not null then next_total_mt end as total_mt,
        case when per_capita_kg is not null then per_capita_kg
             when prev_pc is not null and next_pc is not null
                then prev_pc + (year - prev_year) * (next_pc - prev_pc) / nullif(next_year - prev_year, 0)
             when prev_pc is not null then prev_pc
             when next_pc is not null then next_pc end as per_capita_kg,
        case when formal_collection_rate is not null then formal_collection_rate
             when prev_fcr is not null and next_fcr is not null
                then greatest(0, least(1, prev_fcr + (year - prev_year) * (next_fcr - prev_fcr) / nullif(next_year - prev_year, 0)))
             when prev_fcr is not null then prev_fcr
             when next_fcr is not null then next_fcr end as formal_collection_rate,
        case when total_mt is not null then coalesce(confidence_tier, 'reported') else 'interpolated' end as confidence_tier,
        (total_mt is null) as is_interpolated,
        latest_observed_year as data_vintage_year
    from w
)
select * from interp where total_mt is not null
"""

GOVERNANCE_SQL = """
-- Port of dbt/models/staging/stg_wb_governance.sql (enforcement_score_normalized)
select iso3, year,
    (coalesce(rule_of_law, 0) + coalesce(gov_effectiveness, 0) + coalesce(control_of_corruption, 0))
      / nullif((rule_of_law is not null)::int + (gov_effectiveness is not null)::int + (control_of_corruption is not null)::int, 0)
      as composite,
    ((rule_of_law is not null)::int + (gov_effectiveness is not null)::int + (control_of_corruption is not null)::int) / 3.0
      as data_completeness
from wgi_raw
where year between {min_year} and {max_year}
  and (rule_of_law is not null or gov_effectiveness is not null or control_of_corruption is not null)
"""

PRS_SQL = f"""
-- Port of dbt/models/intermediate/int_prs_components.sql (v1).
-- Comtrade import volumes are unavailable in the static snapshot, so
-- import_volume_mt = 0 and capacity_score falls to formal_collection_rate,
-- exactly the branch the dbt model takes when a country has no imports.
with governance as (
    select iso3, year, greatest(0, least(1, composite / 5.0 + 0.5)) as enforcement_score
    from governance
),
joined as (
    select g.iso3, g.year, g.enforcement_score,
        gen.formal_collection_rate, gen.total_mt as generation_mt,
        0.0 as import_volume_mt,
        ci.income_classification,
        coalesce(iw.prs_income_score, 5) / 10.0 as income_score,
        lf.flag_level as literature_flag_level,
        coalesce(lf.prs_literature_score, 0) / 10.0 as literature_score
    from governance g
    left join generation_filled gen on gen.iso3 = g.iso3 and gen.year = g.year
    left join countries ci on ci.iso3 = g.iso3
    left join income_weights iw on iw.income_classification = ci.income_classification
    left join lit_flags lf on lf.country_iso3 = g.iso3
),
comp as (
    select *,
        case when formal_collection_rate is not null then formal_collection_rate else null end as capacity_score,
        coalesce(enforcement_score, 0.5) as enforcement_used
    from joined
)
select iso3, year, capacity_score, enforcement_used as enforcement_score, income_score, literature_score,
    literature_flag_level, income_classification, generation_mt,
    round(10.0 * ({W_CAPACITY} * (1 - coalesce(capacity_score, 0.5))
                + {W_ENFORCEMENT} * (1 - enforcement_used)
                + {W_INCOME} * income_score
                + {W_LITERATURE} * literature_score), 2) as prs_score,
    ((capacity_score is not null)::int + (enforcement_score is not null)::int
     + (income_classification is not null)::int + (literature_flag_level is not null)::int) / 4.0 as data_completeness,
    {PRS_METHODOLOGY_VERSION} as methodology_version
from comp
"""


# ─── Build ───────────────────────────────────────────────────────────────────


def _num(v, nd=None):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return round(float(v), nd) if nd is not None else float(v)


def build(out_dir: Path, cache_dir: Path, refresh: bool) -> None:
    f = Fetcher(cache_dir, refresh)
    m49 = load_m49(f)
    valid = set(m49["iso3"])

    pop = load_population(f, valid)
    oecd = load_oecd(f, valid)
    oecd = oecd[oecd["total_mt"].notna()]
    oecd["footnote"] = ""
    sdg = load_sdg(f, m49)
    # One source per country keeps each country's time series internally consistent:
    # prefer OECD's harmonised dataset, fill other countries from the SDG series.
    sdg_only = sdg[~sdg["iso3"].isin(set(oecd["iso3"]))]
    observed = pd.concat([oecd, sdg_only], ignore_index=True)
    observed = observed[observed["total_mt"].notna()]
    sdg_scope = sdg["footnote"].fillna("").str.contains(PARTIAL_SCOPE_PATTERN, case=False)
    observed, excluded = screen_observations(observed, pop, set(sdg.loc[sdg_scope, "iso3"]))
    for e in excluded:
        log.warning("Plausibility screen dropped %s %s (%s)", e["iso3"], e["years"], e["reason"])
    country_source = observed.groupby("iso3")["source"].first().to_dict()
    log.info("Generation: %d observations, %d countries (%s)",
             len(observed), observed["iso3"].nunique(), observed.groupby("source")["iso3"].nunique().to_dict())

    income = load_wb_income(f)
    basel = load_basel(f, m49)
    wgi = load_wgi(f, valid)

    countries = m49.merge(income, on="iso3", how="left").merge(basel, on="iso3", how="left")
    countries["basel_signatory"] = countries["basel_signatory"].fillna(False).astype(bool)
    countries["basel_ban_ratified"] = countries["basel_ban_ratified"].fillna(False).astype(bool)
    oecd_members = set(re.findall(r"\('([A-Z]{3})'\)", (HERE.parent / "dbt/models/marts/mart_countries.sql").read_text()))
    countries["is_oecd_member"] = countries["iso3"].isin(oecd_members)

    con = duckdb.connect()
    con.register("observed_raw", observed)
    con.register("wgi_raw", wgi)
    con.register("countries", countries)
    con.register("income_weights", pd.read_csv(SEEDS / "income_class_prs_weights.csv"))
    con.register("lit_flags", pd.read_csv(SEEDS / "literature_flags.csv"))
    gen = con.execute(GENERATION_FILLED_SQL).df()
    con.register("generation_filled", gen)
    con.execute("create table governance as " + GOVERNANCE_SQL.format(min_year=MIN_YEAR, max_year=MAX_YEAR))
    prs = con.execute(PRS_SQL).df()
    prs = prs[prs["prs_score"].notna()]
    log.info("Generation filled: %d rows; PRS: %d rows, %d countries", len(gen), len(prs), prs["iso3"].nunique())

    # ── Write files ──────────────────────────────────────────────────────────
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "choropleth").mkdir(parents=True)
    (out_dir / "country").mkdir(parents=True)

    def dump(path: Path, obj) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))

    name_of = dict(zip(countries["iso3"], countries["name"]))

    # /api/v1/countries
    dump(out_dir / "countries.json", [
        {
            "iso3": r.iso3, "name": r.name, "region": r.region, "subregion": r.subregion,
            "income_classification": r.income_classification if isinstance(r.income_classification, str) else None,
            "basel_signatory": bool(r.basel_signatory), "basel_ban_ratified": bool(r.basel_ban_ratified),
            "is_oecd_member": bool(r.is_oecd_member),
        }
        for r in countries.sort_values("name").itertuples()
    ])

    # /api/v1/map/choropleth?metric=&year=  (mart_choropleth_cache semantics)
    gen_by_year = {y: g for y, g in gen.groupby("year")}
    prs_by_year = {y: g for y, g in prs.groupby("year")}
    tier_of = {(r.iso3, r.year): (r.confidence_tier, r.data_vintage_year) for r in gen.itertuples()}
    for year in range(MIN_YEAR, MAX_YEAR + 1):
        g = gen_by_year.get(year, gen.iloc[0:0])
        p = prs_by_year.get(year, prs.iloc[0:0])
        cols = {
            "generation": (g, "total_mt", 2),
            "per_capita": (g, "per_capita_kg", 3),
            "formal_collection": (g, "formal_collection_rate", 4),
            "prs": (p, "prs_score", 2),
        }
        for metric, (df, col, nd) in cols.items():
            rows = []
            for r in df.sort_values("iso3").itertuples():
                val = _num(getattr(r, col), nd)
                tier, vintage = tier_of.get((r.iso3, year), (None, None))
                rows.append({
                    "iso3": r.iso3, "name": name_of.get(r.iso3, r.iso3), "value": val,
                    "confidence_tier": tier, "data_vintage_year": int(vintage) if vintage is not None and not pd.isna(vintage) else None,
                    "is_missing": val is None,
                })
            dump(out_dir / "choropleth" / metric / f"{year}.json", {"year": year, "metric": metric, "countries": rows})

    # /api/v1/country/{iso3}/profile
    latest_prs = prs.sort_values("year").groupby("iso3").tail(1).set_index("iso3")
    gen_by_country = {k: v.sort_values("year") for k, v in gen.groupby("iso3")}
    for r in countries.itertuples():
        series = gen_by_country.get(r.iso3)
        points = []
        if series is not None:
            for s in series.tail(10).itertuples():
                points.append({
                    "year": int(s.year), "total_mt": _num(s.total_mt, 2), "per_capita_kg": _num(s.per_capita_kg, 3),
                    "formal_collection_rate": _num(s.formal_collection_rate, 4), "confidence_tier": s.confidence_tier,
                    "data_vintage_year": int(s.data_vintage_year), "is_interpolated": bool(s.is_interpolated),
                })
        lp = latest_prs.loc[r.iso3] if r.iso3 in latest_prs.index else None
        dump(out_dir / "country" / f"{r.iso3}.json", {
            "iso3": r.iso3, "name": r.name, "region": r.region, "subregion": r.subregion,
            "income_classification": r.income_classification if isinstance(r.income_classification, str) else None,
            "basel_signatory": bool(r.basel_signatory), "basel_ban_ratified": bool(r.basel_ban_ratified),
            "is_oecd_member": bool(r.is_oecd_member),
            "prs_score": _num(lp["prs_score"], 2) if lp is not None else None,
            "prs_methodology_version": PRS_METHODOLOGY_VERSION if lp is not None else None,
            "prs_year": int(lp["year"]) if lp is not None else None,
            "prs_components": {
                "capacity_score": _num(lp["capacity_score"], 4),
                "enforcement_score": _num(lp["enforcement_score"], 4),
                "income_score": _num(lp["income_score"], 4),
                "literature_score": _num(lp["literature_score"], 4),
                "data_completeness": _num(lp["data_completeness"], 2),
            } if lp is not None else None,
            "literature_flag_level": lp["literature_flag_level"] if lp is not None and isinstance(lp["literature_flag_level"], str) else None,
            "generation_source": country_source.get(r.iso3),
            "generation_series": points,
            "top_exports": [],
            "top_imports": [],
        })

    meta = {
        "snapshot_date": dt.date.today().isoformat(),
        "year_range": [MIN_YEAR, MAX_YEAR],
        "available_metrics": AVAILABLE_METRICS,
        "unavailable_metrics": UNAVAILABLE_METRICS,
        "unavailable_reason": "Needs UN Comtrade bilateral trade data (API key) and the full backend.",
        "counts": {
            "countries": int(len(countries)),
            "countries_with_generation": int(observed["iso3"].nunique()),
            "generation_observations": int(len(observed)),
            "countries_with_prs": int(prs["iso3"].nunique()),
        },
        "notes": [
            "Generation values are country-reported figures; one source per country (OECD DF_EWASTE preferred, UN SDG 12.4.2 otherwise).",
            f"Observations whose implied generation is outside {PER_CAPITA_BOUNDS_KG[0]}-{PER_CAPITA_BOUNDS_KG[1]} kg/person, or from countries whose source footnote states a partial scope, are excluded (see 'excluded').",
            "Collection rates above 100% are treated as missing (scope mismatch between collected and generated figures).",
            "Per capita values missing from the SDG series are derived from World Bank population (SP.POP.TOTL).",
            "Years without an observation are filled by the pipeline's linear interpolation / edge carry and are flagged 'interpolated'.",
            "PRS v1 is computed without Comtrade import volumes: the capacity component uses the formal collection rate only (0.5 when unknown).",
            "Income classification is the current World Bank classification applied to all years.",
        ],
        "sources": SOURCES,
        "excluded": excluded,
    }
    dump(out_dir / "meta.json", meta)
    log.info("Wrote snapshot to %s", out_dir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("frontend/public/static-data"))
    ap.add_argument("--cache", type=Path, default=Path(".snapshot-cache"))
    ap.add_argument("--refresh", action="store_true", help="Re-download sources even if cached")
    args = ap.parse_args()
    build(args.out, args.cache, args.refresh)
