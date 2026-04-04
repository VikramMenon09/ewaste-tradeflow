{{
  config(
    materialized='table',
    description='Final e-waste generation metrics mart. Materialized from int_generation_filled with category_code=0 (all-category combined) rows. Queried by the choropleth mart and the /generation API endpoint.',
    post_hook='ANALYZE {{ this }}'
  )
}}

/*
  The UN Monitor data is at the country level (not by UN e-waste category).
  We store these as category_code = 0 (all categories combined), matching
  the ORM model expectation.

  Category-level splits would require supplementary data sources — flagged
  as a future enhancement in the methodology documentation.
*/

with generation as (

    select
        iso3                     as country_iso3,
        year,
        0                        as category_code,   -- all categories combined
        round(cast(total_mt as numeric), 2)          as total_mt,
        round(cast(per_capita_kg as numeric), 3)     as per_capita_kg,
        -- formal_collection_mt is not provided by UN Monitor directly;
        -- derive from rate × total generation
        case
            when formal_collection_rate is not null and total_mt is not null
            then round(cast(formal_collection_rate * total_mt as numeric), 2)
            else null
        end                      as formal_collection_mt,
        round(cast(formal_collection_rate as numeric), 4) as formal_collection_rate,
        is_interpolated,
        data_vintage_year,
        confidence_tier

    from {{ ref('int_generation_filled') }}
    where total_mt is not null

)

select * from generation
