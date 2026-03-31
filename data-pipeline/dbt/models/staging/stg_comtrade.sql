{{
  config(
    materialized='view',
    description='Staging model for UN Comtrade trade flow data. Applies type casting, ISO3 normalization, and confidence tier tagging. One row per bilateral trade flow per HS code per year.'
  )
}}

with raw as (

    -- Read from the PostgreSQL table populated by the ingestion pipeline.
    -- The ingestion script uploads Parquet to S3, then a COPY command loads it here.
    select * from {{ source('raw', 'comtrade_raw') }}

),

cleaned as (

    select
        -- Year
        cast(period as integer) as year,

        -- Reporter (exporting/importing country)
        upper(trim(reporter_iso3)) as reporter_iso3,

        -- Partner country
        upper(trim(partner_iso3)) as partner_iso3,

        -- Flow direction: 'X' = export, 'M' = import
        upper(trim(flow_code)) as flow_code,

        -- HS code (4-digit)
        trim(hs_code) as hs_code,

        -- Volume normalized to metric tons (done in Python parse step)
        coalesce(cast(volume_mt as numeric(18, 4)), 0) as volume_mt,

        -- Trade value in USD
        coalesce(cast(trade_value_usd as numeric(18, 2)), 0) as trade_value_usd,

        -- Confidence tier: Comtrade officially reported data = tier 1
        'reported' as confidence_tier,

        -- Source reference
        cast(source_id as integer) as source_id,

        -- Ingestion audit columns
        ingested_at

    from raw

    where
        -- Exclude aggregate rows (already filtered in Python but belt-and-suspenders)
        is_aggregate = false
        -- Exclude rows with missing country codes
        and reporter_iso3 is not null and reporter_iso3 != ''
        and partner_iso3 is not null and partner_iso3 != ''
        -- Exclude self-trade
        and reporter_iso3 != partner_iso3
        -- Exclude near-zero volumes
        and coalesce(cast(volume_mt as numeric), 0) >= 0.001
        -- Restrict to configured year range
        and cast(period as integer) between {{ var('min_year') }} and {{ var('max_year') }}
        -- Restrict to e-waste HS codes
        and trim(hs_code) in (
            '8548', '8549',
            '8471', '8472', '8473',
            '8474', '8475', '8476', '8477', '8478', '8479'
        )

),

-- Apply mapping confidence from the HS category seed
with_confidence as (

    select
        c.*,
        coalesce(h.mapping_confidence, 'UNKNOWN') as mapping_confidence,
        coalesce(h.waste_fraction_scalar, 1.0) as waste_fraction_scalar,
        coalesce(h.un_category_code, 0) as un_category_code,
        coalesce(h.un_category_name, 'Unknown') as un_category_name

    from cleaned c
    left join {{ ref('hs_to_ewaste_category') }} h
        on c.hs_code = h.hs_code

)

select * from with_confidence
