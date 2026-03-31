{{
  config(
    materialized='view',
    description='Staging model for UN Global E-waste Monitor data. Covers e-waste generation, formal collection rates, and regional summaries at country level.'
  )
}}

with raw as (

    select * from {{ source('raw', 'un_monitor_raw') }}

),

cleaned as (

    select
        upper(trim(country_iso3))             as country_iso3,
        cast(year as integer)                  as year,

        -- UN Monitor uses 6 e-waste categories (0 = all categories combined)
        coalesce(cast(category_code as integer), 0) as category_code,
        coalesce(trim(category_name), 'All categories') as category_name,

        -- Total waste generated in metric tons
        cast(total_mt as numeric(18, 2))       as total_mt,

        -- Per capita in kilograms
        cast(per_capita_kg as numeric(10, 3))  as per_capita_kg,

        -- Formally documented collection (metric tons)
        cast(formal_collection_mt as numeric(18, 2)) as formal_collection_mt,

        -- Formal collection rate as a fraction (0.0 to 1.0)
        -- Null means the data was not reported, not that the rate is 0
        case
            when formal_collection_rate_pct is null then null
            else cast(formal_collection_rate_pct as numeric(6, 4)) / 100.0
        end as formal_collection_rate,

        -- Is this an interpolated value (gap-filled between UN Monitor vintages)?
        -- Set by the ingestion script based on whether the source file reported it
        coalesce(cast(is_interpolated as boolean), false) as is_interpolated,

        -- The UN Monitor publication year (distinct from the observation year)
        cast(data_vintage_year as integer) as data_vintage_year,

        -- Confidence tier: UN Monitor official data = tier 1; estimates = tier 2
        case
            when coalesce(cast(is_interpolated as boolean), false) then 'interpolated'
            when trim(confidence_tier) = 'estimated' then 'estimated'
            else 'reported'
        end as confidence_tier,

        cast(source_id as integer) as source_id,
        ingested_at

    from raw

    where
        country_iso3 is not null and trim(country_iso3) != ''
        and cast(year as integer) between {{ var('min_year') }} and {{ var('max_year') }}
        -- Exclude regional aggregates (these have non-ISO3 region codes)
        and length(trim(country_iso3)) = 3

)

select * from cleaned
