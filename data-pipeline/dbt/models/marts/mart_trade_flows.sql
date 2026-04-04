{{
  config(
    materialized='table',
    description='Final trade flows mart. A materialized, indexed alias of int_trade_flows_unified enriched with country names for API query performance. Queried by mart_choropleth_cache, mart_sankey_cache, and the /trade-flows API endpoint.',
    post_hook='ANALYZE {{ this }}'
  )
}}

with flows as (

    select
        year,
        exporter_iso3,
        importer_iso3,
        hs_code,
        un_category_code            as ewaste_category_code,
        volume_mt,
        trade_value_usd             as value_usd,
        volume_mt * waste_fraction_scalar as estimated_ewaste_volume_mt,
        confidence_tier,
        mapping_confidence,
        data_source,
        has_dual_source,
        data_conflict,
        exporter_basel_signatory,
        exporter_ban_ratified,
        importer_basel_signatory,
        importer_ban_ratified,
        importer_income_class,
        basel_compliant,
        prs_risk_flag,
        importer_prs_score,
        informal_estimate,
        source_id

    from {{ ref('int_trade_flows_unified') }}

),

-- Join country names for convenience (avoids joins in API queries)
with_names as (

    select
        f.*,
        exp_c.name  as exporter_name,
        imp_c.name  as importer_name,
        exp_c.region as exporter_region,
        imp_c.region as importer_region

    from flows f
    left join {{ ref('mart_countries') }} exp_c on f.exporter_iso3 = exp_c.iso3
    left join {{ ref('mart_countries') }} imp_c on f.importer_iso3 = imp_c.iso3

)

select * from with_names
