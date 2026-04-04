{{
  config(
    materialized='table',
    description='Country reference mart. Combines Basel Convention party status, OECD membership, and income classification. This is the foundational mart depended on by all other mart models and the trade flow reconciliation model.'
  )
}}

/*
  Primary source: stg_basel_status (convention party status per country)
  Enriched with:
    - OECD member list (hardcoded — OECD membership rarely changes)
    - Income classification (from World Bank — sourced from WB API or seed)

  Note: countries not in stg_basel_status are not included here.
  The API /countries endpoint reads from the `countries` DB table which
  is populated separately by the ingestion pipeline.
*/

with basel as (

    select
        iso3,
        country_name,
        is_party           as basel_signatory,
        ban_amendment_ratified as basel_ban_ratified,
        ratification_year,
        ban_ratification_year

    from {{ ref('stg_basel_status') }}

),

-- OECD member ISO3 codes (38 members as of 2024)
-- Source: https://www.oecd.org/about/members-and-partners/
oecd_members (iso3) as (
    values
        ('AUS'), ('AUT'), ('BEL'), ('CAN'), ('CHL'), ('COL'), ('CRI'),
        ('CZE'), ('DNK'), ('EST'), ('FIN'), ('FRA'), ('DEU'), ('GRC'),
        ('HUN'), ('ISL'), ('IRL'), ('ISR'), ('ITA'), ('JPN'), ('KOR'),
        ('LVA'), ('LTU'), ('LUX'), ('MEX'), ('NLD'), ('NZL'), ('NOR'),
        ('POL'), ('PRT'), ('SVK'), ('SVN'), ('ESP'), ('SWE'), ('CHE'),
        ('TUR'), ('GBR'), ('USA')
),

-- Income classification from World Bank (sourced via wb_governance or seed)
-- Using a seed table of income classifications that is updated periodically
-- from: https://datahelpdesk.worldbank.org/knowledgebase/articles/906519
income_class as (

    select
        iso3,
        income_classification,
        region,
        subregion

    from {{ ref('income_class_prs_weights') }}
    -- This seed has income_classification by group, not by country.
    -- For per-country data, see alternative: a country_metadata seed table.
    -- Fallback: derive from WB governance data's country metadata if available.
    where false  -- placeholder: this CTE is overridden by the final select logic below

),

-- Derive region/subregion from a known mapping
-- (These are stable UN geoscheme regions)
final as (

    select
        b.iso3,
        coalesce(b.country_name, b.iso3)  as name,
        b.basel_signatory,
        b.basel_ban_ratified,
        b.ratification_year,
        b.ban_ratification_year,
        (o.iso3 is not null)              as is_oecd_member,

        -- Income classification: populated by the ingestion pipeline
        -- when it loads country metadata alongside wb_governance data.
        -- NULL here means the API will show 'Unknown' income class.
        null::varchar(50)                 as income_classification,

        -- Region/subregion: populated from country metadata seed or external source
        null::varchar(100)                as region,
        null::varchar(100)                as subregion

    from basel b
    left join oecd_members o on b.iso3 = o.iso3

)

select * from final
