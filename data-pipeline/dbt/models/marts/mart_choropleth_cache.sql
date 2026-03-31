{{
  config(
    materialized='table',
    description='Pre-aggregated choropleth data. One row per (country, year, metric). Queried directly by the /api/v1/map/choropleth endpoint. Refreshed nightly by dbt.',
    post_hook='ANALYZE {{ this }}'
  )
}}

/*
  Metrics pre-computed for the choropleth layer:
    - total_generation_mt        : total e-waste generated (UN Monitor)
    - per_capita_kg              : per capita generation in kg (UN Monitor)
    - formal_collection_rate     : fraction formally collected/recycled (UN Monitor)
    - net_trade_mt               : imports - exports (positive = net importer)
    - export_volume_mt           : total exports (Comtrade/OECD)
    - import_volume_mt           : total imports (Comtrade/OECD)
    - prs_score                  : Processing Risk Score (modeled)
    - export_intensity           : exports as a fraction of total generation
    - compliance_rate            : fraction of export routes that are Basel-compliant
*/

with generation as (

    select
        country_iso3,
        year,
        sum(total_mt)             as total_generation_mt,
        max(per_capita_kg)        as per_capita_kg,         -- max across categories = all-category row
        max(formal_collection_rate) as formal_collection_rate,
        max(confidence_tier)      as generation_confidence_tier,
        max(data_vintage_year)    as data_vintage_year

    from {{ ref('mart_ewaste_generation') }}
    where category_code = 0  -- all-categories combined row
    group by 1, 2

),

trade as (

    select
        year,
        exporter_iso3,
        importer_iso3,
        estimated_ewaste_volume_mt

    from {{ ref('mart_trade_flows') }}
    where mapping_confidence != 'UNKNOWN'

),

exports_agg as (
    select year, exporter_iso3 as country_iso3, sum(estimated_ewaste_volume_mt) as export_volume_mt
    from trade
    group by 1, 2
),

imports_agg as (
    select year, importer_iso3 as country_iso3, sum(estimated_ewaste_volume_mt) as import_volume_mt
    from trade
    group by 1, 2
),

compliance_agg as (
    select
        year,
        exporter_iso3 as country_iso3,
        count(*) as total_export_routes,
        sum(case when coalesce(basel_compliant, true) then 1 else 0 end) as compliant_routes
    from {{ ref('mart_trade_flows') }}
    group by 1, 2
),

prs as (
    select country_iso3, year, prs_score
    from {{ ref('mart_processing_risk_scores') }}
),

countries as (
    select iso3 as country_iso3, name as country_name, region, subregion
    from {{ ref('mart_countries') }}
),

-- Pivot to long format: one row per (country, year, metric)
unpivoted as (

    select
        c.country_iso3,
        c.country_name,
        c.region,
        c.subregion,
        coalesce(g.year, e.year, i.year, p.year) as year,

        -- Metric values
        g.total_generation_mt,
        g.per_capita_kg,
        g.formal_collection_rate,
        coalesce(i.import_volume_mt, 0) - coalesce(e.export_volume_mt, 0) as net_trade_mt,
        coalesce(e.export_volume_mt, 0) as export_volume_mt,
        coalesce(i.import_volume_mt, 0) as import_volume_mt,
        p.prs_score,

        -- Derived metrics
        case
            when g.total_generation_mt > 0
            then coalesce(e.export_volume_mt, 0) / g.total_generation_mt
            else null
        end as export_intensity,

        case
            when ca.total_export_routes > 0
            then ca.compliant_routes::float / ca.total_export_routes
            else null
        end as compliance_rate,

        -- Data quality metadata
        g.generation_confidence_tier,
        g.data_vintage_year,

        -- NULL flags: important for the UI to show 'No Data' vs 0
        (g.total_generation_mt is null) as generation_missing,
        (e.export_volume_mt is null)    as exports_missing,
        (i.import_volume_mt is null)    as imports_missing,
        (p.prs_score is null)           as prs_missing

    from countries c
    -- Cross join with years to ensure every country has a row for every year
    cross join (
        select generate_series({{ var('min_year') }}, {{ var('max_year') }}) as year
    ) years
    left join generation g
        on c.country_iso3 = g.country_iso3 and years.year = g.year
    left join exports_agg e
        on c.country_iso3 = e.country_iso3 and years.year = e.year
    left join imports_agg i
        on c.country_iso3 = i.country_iso3 and years.year = i.year
    left join prs p
        on c.country_iso3 = p.country_iso3 and years.year = p.year
    left join compliance_agg ca
        on c.country_iso3 = ca.country_iso3 and years.year = ca.year

)

-- Only include rows where at least one metric has data
select * from unpivoted
where
    not (generation_missing and exports_missing and imports_missing and prs_missing)
