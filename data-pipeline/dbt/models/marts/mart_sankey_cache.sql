{{
  config(
    materialized='table',
    description='Pre-ranked trade routes for Sankey diagram rendering. Top N routes per year by estimated e-waste volume. Queried directly by /api/v1/map/flows/sankey. Refreshed nightly.',
    post_hook='ANALYZE {{ this }}'
  )
}}

with flows as (

    select
        year,
        exporter_iso3,
        importer_iso3,
        un_category_code,
        sum(estimated_ewaste_volume_mt) as volume_mt,
        sum(trade_value_usd)            as value_usd,
        max(data_source)                as data_source,
        max(confidence_tier)            as confidence_tier,
        max(mapping_confidence)         as mapping_confidence,
        bool_or(coalesce(basel_compliant, true) = false) as has_violation,  -- any non-compliant flow on this route
        bool_or(prs_risk_flag)                           as prs_risk_flag,
        max(importer_prs_score)                          as importer_prs_score,
        max(data_conflict)                               as data_conflict

    from {{ ref('mart_trade_flows') }}
    where
        estimated_ewaste_volume_mt >= {{ var('min_volume_mt_for_sankey') }}
        and mapping_confidence != 'UNKNOWN'

    group by 1, 2, 3, 4

),

-- Join country metadata for Sankey node labels
with_names as (

    select
        f.*,
        exp_c.name  as exporter_name,
        exp_c.region as exporter_region,
        exp_c.subregion as exporter_subregion,
        imp_c.name  as importer_name,
        imp_c.region as importer_region,
        imp_c.subregion as importer_subregion,

        -- Compliance color tier for Sankey link coloring (matches frontend constants)
        case
            when f.has_violation then 'red'       -- known Basel violation
            when f.prs_risk_flag then 'amber'      -- high-risk destination, no confirmed violation
            else 'green'                           -- compliant and low/medium PRS
        end as compliance_color,

        -- Rank within year: 1 = highest volume
        row_number() over (
            partition by f.year
            order by f.volume_mt desc
        ) as rank_by_volume,

        -- Rank within year filtered to non-compliant routes only
        case
            when f.has_violation
            then row_number() over (
                partition by f.year, f.has_violation
                order by f.volume_mt desc
            )
            else null
        end as violation_rank_by_volume

    from flows f
    left join {{ ref('mart_countries') }} exp_c on f.exporter_iso3 = exp_c.iso3
    left join {{ ref('mart_countries') }} imp_c on f.importer_iso3 = imp_c.iso3

)

-- Keep top N routes per year (the API can filter further)
select * from with_names
where rank_by_volume <= {{ var('sankey_top_n') }}
order by year, rank_by_volume
