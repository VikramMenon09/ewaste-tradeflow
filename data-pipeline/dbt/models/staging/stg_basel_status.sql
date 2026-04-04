{{
  config(
    materialized='view',
    description='Staging view for Basel Convention party and Ban Amendment ratification status. Static reference data — one row per country. Used by mart_countries and int_trade_flows_unified for Basel compliance flagging.'
  )
}}

with raw as (

    select * from {{ source('raw', 'basel_status_raw') }}

),

cleaned as (

    select
        upper(trim(iso3))                           as iso3,
        trim(country_name)                          as country_name,
        coalesce(cast(is_party as boolean), false)  as is_party,

        -- Ban Amendment: prohibits OECD→non-OECD exports of hazardous waste
        coalesce(cast(ban_amendment_ratified as boolean), false) as ban_amendment_ratified,

        -- Ratification years (may be null for non-parties or missing data)
        cast(ratification_year as integer)          as ratification_year,
        cast(ban_ratification_year as integer)      as ban_ratification_year

    from raw

    where
        iso3 is not null
        and trim(iso3) != ''

),

-- Deduplicate on ISO3 — keep is_party=true rows if duplicates exist
deduplicated as (

    select
        *,
        row_number() over (
            partition by iso3
            order by
                is_party desc,          -- prefer Party rows
                ban_amendment_ratified desc,
                ratification_year asc nulls last
        ) as row_num

    from cleaned

)

select
    iso3,
    country_name,
    is_party,
    ban_amendment_ratified,
    ratification_year,
    ban_ratification_year

from deduplicated
where row_num = 1
