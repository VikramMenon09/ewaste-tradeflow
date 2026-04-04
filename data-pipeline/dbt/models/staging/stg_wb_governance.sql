{{
  config(
    materialized='view',
    description='Staging view for World Bank Governance Indicators. Normalizes Rule of Law, Government Effectiveness, and Control of Corruption to a consistent schema. Used by int_prs_components to compute the enforcement component of the Processing Risk Score.'
  )
}}

with raw as (

    select * from {{ source('raw', 'wb_governance_raw') }}

),

cleaned as (

    select
        -- ISO3 country code (already normalized by ingestion source)
        upper(trim(country_iso3)) as iso3,

        -- Year
        cast(year as integer) as year,

        -- Governance indicators (range -2.5 to +2.5; higher = better governance)
        cast(rule_of_law as numeric(6, 4))           as rule_of_law,
        cast(gov_effectiveness as numeric(6, 4))     as gov_effectiveness,
        cast(control_of_corruption as numeric(6, 4)) as control_of_corruption,

        -- Fraction of 3 indicators that are non-null (0.0–1.0)
        cast(data_completeness as numeric(4, 3)) as data_completeness,

        -- Always 'reported' for WBI data
        confidence_tier,

        ingested_at

    from raw

    where
        country_iso3 is not null
        and country_iso3 != ''
        and cast(year as integer) between {{ var('min_year') }} and {{ var('max_year') }}
        -- Only include rows with at least one non-null indicator
        and (
            rule_of_law is not null
            or gov_effectiveness is not null
            or control_of_corruption is not null
        )

),

-- Compute composite governance index (simple average of available indicators)
-- Higher score = better governance = lower enforcement risk
with_composite as (

    select
        *,
        (
            coalesce(rule_of_law, 0) +
            coalesce(gov_effectiveness, 0) +
            coalesce(control_of_corruption, 0)
        ) / nullif(
            (case when rule_of_law is not null then 1 else 0 end) +
            (case when gov_effectiveness is not null then 1 else 0 end) +
            (case when control_of_corruption is not null then 1 else 0 end),
            0
        )                                as composite_governance_index,

        -- Normalized 0–1 enforcement score: higher = better enforcement
        -- Map from [-2.5, +2.5] range → [0, 1]
        greatest(0, least(1,
            (
                coalesce(rule_of_law, 0) +
                coalesce(gov_effectiveness, 0) +
                coalesce(control_of_corruption, 0)
            ) / nullif(
                (case when rule_of_law is not null then 1 else 0 end) +
                (case when gov_effectiveness is not null then 1 else 0 end) +
                (case when control_of_corruption is not null then 1 else 0 end),
                0
            ) / 5.0 + 0.5
        ))                               as enforcement_score_normalized

    from cleaned

),

-- Keep the most recent available year for each country when multiple years exist
-- (in case the source has data for years outside our range)
deduplicated as (

    select
        *,
        row_number() over (
            partition by iso3, year
            order by data_completeness desc, ingested_at desc
        ) as row_num

    from with_composite

)

select
    iso3,
    year,
    rule_of_law,
    gov_effectiveness,
    control_of_corruption,
    composite_governance_index,
    enforcement_score_normalized,
    data_completeness,
    confidence_tier,
    ingested_at

from deduplicated
where row_num = 1
