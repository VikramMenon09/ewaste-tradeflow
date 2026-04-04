{{
  config(
    materialized='table',
    description='Final Processing Risk Score mart. Selects the most recent methodology version of PRS scores per country-year from int_prs_components. Queried by int_trade_flows_unified, mart_choropleth_cache, and the /country/{iso3}/profile API endpoint.',
    post_hook='ANALYZE {{ this }}'
  )
}}

with prs as (

    select
        iso3            as country_iso3,
        year,
        prs_score,
        capacity_score,
        enforcement_score_normalized    as enforcement_score,
        income_score,
        literature_score,
        generation_mt                   as formal_capacity_mt,
        import_volume_mt,

        -- capacity_ratio: import demand vs formal collection capacity
        case
            when formal_collection_rate is not null
                and generation_mt is not null
                and generation_mt > 0
            then round(cast(
                import_volume_mt
                / nullif(formal_collection_rate * generation_mt, 0)
            as numeric), 4)
            else null
        end                             as capacity_ratio,

        enforcement_score_normalized    as enforcement_index,
        income_classification,
        literature_flag_level,
        data_completeness,
        methodology_version,

        -- Rank so we keep latest methodology run per (country, year)
        row_number() over (
            partition by iso3, year
            order by methodology_version desc
        ) as row_num

    from {{ ref('int_prs_components') }}

)

select
    country_iso3,
    year,
    prs_score,
    capacity_score,
    enforcement_score,
    income_score,
    literature_score,
    formal_capacity_mt,
    import_volume_mt,
    capacity_ratio,
    enforcement_index,
    income_classification,
    literature_flag_level,
    data_completeness,
    methodology_version

from prs
where row_num = 1
  and prs_score is not null
