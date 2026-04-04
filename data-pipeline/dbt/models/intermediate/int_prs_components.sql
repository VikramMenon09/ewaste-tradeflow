{{
  config(
    materialized='table',
    description='Processing Risk Score (PRS) component breakdown per country-year. Joins World Bank governance indicators, UN Monitor formal collection rates, and income classification from the seed table. Output feeds mart_processing_risk_scores.'
  )
}}

/*
  PRS Formula (v1) — see docs/data/prs-methodology.md:
    PRS = w_capacity  * (1 - capacity_score)
        + w_enforce   * (1 - enforcement_score)
        + w_income    * income_score_normalized
        + w_lit       * literature_score_normalized

  Score is 0–10 (higher = higher informal processing risk).
  Weights are fixed per methodology v1:
    w_capacity    = 0.35
    w_enforcement = 0.35
    w_income      = 0.20
    w_literature  = 0.10

  Component sources:
    capacity_score     — formal collection rate (UN Monitor) vs import volume
    enforcement_score  — WB governance composite (stg_wb_governance)
    income_score       — from income_class_prs_weights seed (prs_income_score, 0-10)
    literature_score   — from literature_flags seed (prs_literature_score, 0-10)
*/

-- Fixed weights for methodology v1
{% set w_capacity    = 0.35 %}
{% set w_enforcement = 0.35 %}
{% set w_income      = 0.20 %}
{% set w_literature  = 0.10 %}

with governance as (

    select
        iso3,
        year,
        enforcement_score_normalized as enforcement_score,
        data_completeness            as governance_completeness

    from {{ ref('stg_wb_governance') }}

),

generation as (

    select
        iso3,
        year,
        formal_collection_rate,
        total_mt as generation_mt

    from {{ ref('int_generation_filled') }}

),

import_volumes as (

    select
        importer_iso3 as iso3,
        year,
        sum(estimated_ewaste_volume_mt) as import_volume_mt

    from {{ ref('int_trade_flows_unified') }}
    group by 1, 2

),

country_income as (

    select
        iso3,
        income_classification

    from {{ ref('mart_countries') }}
    where income_classification is not null

),

-- Income risk score from seed (raw 0-10 integer, higher = higher risk)
income_weights as (

    select
        income_classification,
        prs_income_score

    from {{ ref('income_class_prs_weights') }}

),

-- Literature-based risk flags from seed (raw 0-10 integer)
lit_flags as (

    select
        country_iso3 as iso3,
        flag_level,
        prs_literature_score

    from {{ ref('literature_flags') }}

),

joined as (

    select
        g.iso3,
        g.year,
        g.enforcement_score,
        g.governance_completeness,
        gen.formal_collection_rate,
        gen.generation_mt,
        coalesce(imp.import_volume_mt, 0) as import_volume_mt,
        ci.income_classification,
        -- Normalize income risk score: seed is 0-10 int → 0.0-1.0
        coalesce(iw.prs_income_score, 5) / 10.0  as income_score_normalized,
        lf.flag_level                             as literature_flag_level,
        -- Normalize literature score: seed is 0-10 int → 0.0-1.0
        coalesce(lf.prs_literature_score, 0) / 10.0 as literature_score_normalized

    from governance g
    left join generation gen
        on g.iso3 = gen.iso3 and g.year = gen.year
    left join import_volumes imp
        on g.iso3 = imp.iso3 and g.year = imp.year
    left join country_income ci
        on g.iso3 = ci.iso3
    left join income_weights iw
        on ci.income_classification = iw.income_classification
    left join lit_flags lf
        on g.iso3 = lf.iso3

),

with_components as (

    select
        iso3,
        year,
        income_classification,
        enforcement_score,
        governance_completeness,
        formal_collection_rate,
        generation_mt,
        import_volume_mt,
        literature_flag_level,
        income_score_normalized,
        literature_score_normalized,

        -- Capacity score: ratio of formal collection capacity to import demand
        case
            when formal_collection_rate is not null
                and generation_mt is not null
                and import_volume_mt > 0
            then least(1.0,
                (formal_collection_rate * generation_mt)
                / nullif(import_volume_mt, 0)
            )
            when formal_collection_rate is not null
            then formal_collection_rate
            else null
        end as capacity_score,

        -- Use normalized WB enforcement score (0 = poor, 1 = strong)
        coalesce(enforcement_score, 0.5) as enforcement_score_used

    from joined

),

final as (

    select
        iso3,
        year,
        income_classification,
        enforcement_score,
        governance_completeness,
        formal_collection_rate,
        generation_mt,
        import_volume_mt,
        literature_flag_level,
        capacity_score,
        enforcement_score_used    as enforcement_score_normalized,
        income_score_normalized   as income_score,
        literature_score_normalized as literature_score,

        -- PRS = weighted sum of risk components, scaled 0-10
        -- Components flip so that high capability/governance = low score
        round(cast(
            10.0 * (
                {{ w_capacity }}    * (1 - coalesce(capacity_score, 0.5))
                + {{ w_enforcement }} * (1 - enforcement_score_used)
                + {{ w_income }}      * income_score_normalized
                + {{ w_literature }}  * literature_score_normalized
            )
        as numeric), 2) as prs_score,

        -- Data completeness: fraction of 4 components with real data
        (
            (case when capacity_score is not null then 1 else 0 end)::numeric
            + (case when enforcement_score is not null then 1 else 0 end)::numeric
            + (case when income_classification is not null then 1 else 0 end)::numeric
            + (case when literature_flag_level is not null then 1 else 0 end)::numeric
        ) / 4.0 as data_completeness,

        {{ var('prs_methodology_version') }} as methodology_version

    from with_components

)

select * from final
