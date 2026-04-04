{{
  config(
    materialized='view',
    description='Staging view for OECD ENV_WASTE_TRAN transboundary hazardous waste flow data. Normalizes to a consistent (exporter, importer, year, category, volume) schema compatible with stg_comtrade for reconciliation in int_trade_flows_unified.'
  )
}}

with raw as (

    select * from {{ source('raw', 'oecd_flows_raw') }}

),

cleaned as (

    select
        -- Year
        cast(year as integer) as year,

        -- Countries — already normalized to ISO3 by the ingestion source
        upper(trim(exporter_iso3)) as exporter_iso3,
        upper(trim(importer_iso3)) as importer_iso3,

        -- E-waste UN category code (0 = all categories, 1–6 = specific categories)
        coalesce(cast(ewaste_category_code as integer), 0) as ewaste_category_code,

        -- Volume in metric tons (normalized by ingestion source)
        coalesce(cast(volume_mt as numeric(18, 4)), 0) as volume_mt,

        -- Confidence tier: OECD-reported data is HIGH confidence for OECD-OECD flows
        coalesce(confidence_tier, 'HIGH') as confidence_tier,

        -- Source reference
        cast(source_id as integer) as source_id,

        -- Audit columns
        ingested_at

    from raw

    where
        -- Exclude rows with missing country codes
        exporter_iso3 is not null and exporter_iso3 != ''
        and importer_iso3 is not null and importer_iso3 != ''
        -- Exclude self-trade
        and upper(trim(exporter_iso3)) != upper(trim(importer_iso3))
        -- Exclude near-zero volumes
        and coalesce(cast(volume_mt as numeric), 0) >= 0.001
        -- Restrict to configured year range
        and cast(year as integer) between {{ var('min_year') }} and {{ var('max_year') }}

),

-- Deduplicate: keep highest-volume row per route+year+category
-- (occasionally OECD has duplicate rows for the same bilateral pair)
deduplicated as (

    select
        *,
        row_number() over (
            partition by year, exporter_iso3, importer_iso3, ewaste_category_code
            order by volume_mt desc
        ) as row_num

    from cleaned

)

select
    year,
    exporter_iso3,
    importer_iso3,
    ewaste_category_code,
    volume_mt,
    confidence_tier,
    source_id,
    ingested_at

from deduplicated
where row_num = 1
