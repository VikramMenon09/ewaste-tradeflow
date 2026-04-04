{{
  config(
    materialized='table',
    description='UN Monitor generation data with gaps filled via linear interpolation. For each country, years with missing data are interpolated between the nearest observed values using window functions. Interpolated rows are flagged with is_interpolated = TRUE.'
  )
}}

/*
  Gap-filling strategy:
  1. Start with stg_un_monitor (observed data only)
  2. Cross-join every country with every year in the configured range
  3. For years with no observed data, interpolate linearly between the
     nearest observed values (prev/next non-null via LAG/LEAD)
  4. If no surrounding values exist (gap at start or end), carry the
     nearest edge value forward/backward (LOCF / BOCF)
  5. Flag all filled rows with is_interpolated = TRUE
*/

with observed as (

    select
        iso3,
        country_name,
        year,
        total_mt,
        per_capita_kg,
        formal_collection_rate,
        documentation_rate,
        confidence_tier,
        false as is_interpolated

    from {{ ref('stg_un_monitor') }}

),

-- All country-year combinations we need to cover
all_years as (
    select generate_series({{ var('min_year') }}, {{ var('max_year') }}) as year
),

countries as (
    select distinct iso3, country_name
    from observed
),

-- Full grid: every observed country × every year in range
full_grid as (
    select
        c.iso3,
        c.country_name,
        y.year
    from countries c
    cross join all_years y
),

-- Join observed data onto the full grid (nulls = gaps)
with_gaps as (

    select
        g.iso3,
        g.country_name,
        g.year,
        o.total_mt,
        o.per_capita_kg,
        o.formal_collection_rate,
        o.documentation_rate,
        o.confidence_tier,
        o.is_interpolated

    from full_grid g
    left join observed o
        on g.iso3 = o.iso3
        and g.year = o.year

),

-- For each gap, find the surrounding observed values via window functions
with_surrounding as (

    select
        *,

        -- Previous observed total_mt
        last_value(total_mt ignore nulls) over (
            partition by iso3
            order by year
            rows between unbounded preceding and current row
        ) as prev_total_mt,

        -- Next observed total_mt
        first_value(total_mt ignore nulls) over (
            partition by iso3
            order by year
            rows between current row and unbounded following
        ) as next_total_mt,

        -- Previous/next year where total_mt was observed
        last_value(case when total_mt is not null then year end ignore nulls) over (
            partition by iso3
            order by year
            rows between unbounded preceding and current row
        ) as prev_year,

        first_value(case when total_mt is not null then year end ignore nulls) over (
            partition by iso3
            order by year
            rows between current row and unbounded following
        ) as next_year,

        -- Per-capita: same pattern
        last_value(per_capita_kg ignore nulls) over (
            partition by iso3
            order by year
            rows between unbounded preceding and current row
        ) as prev_per_capita,

        first_value(per_capita_kg ignore nulls) over (
            partition by iso3
            order by year
            rows between current row and unbounded following
        ) as next_per_capita,

        -- Formal collection rate: same pattern
        last_value(formal_collection_rate ignore nulls) over (
            partition by iso3
            order by year
            rows between unbounded preceding and current row
        ) as prev_fcr,

        first_value(formal_collection_rate ignore nulls) over (
            partition by iso3
            order by year
            rows between current row and unbounded following
        ) as next_fcr

    from with_gaps

),

-- Apply linear interpolation for gaps; LOCF/BOCF for edge gaps
interpolated as (

    select
        iso3,
        country_name,
        year,

        -- total_mt: linear interpolation between prev and next observed values
        case
            when total_mt is not null
                then total_mt
            when prev_total_mt is not null and next_total_mt is not null
                -- Linear interpolation: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
                then prev_total_mt + (year - prev_year)::numeric
                    * (next_total_mt - prev_total_mt)
                    / nullif(next_year - prev_year, 0)
            when prev_total_mt is not null
                then prev_total_mt   -- carry last known value forward
            when next_total_mt is not null
                then next_total_mt   -- backfill with first known value
            else null
        end as total_mt,

        -- per_capita_kg: same interpolation
        case
            when per_capita_kg is not null
                then per_capita_kg
            when prev_per_capita is not null and next_per_capita is not null
                then prev_per_capita + (year - prev_year)::numeric
                    * (next_per_capita - prev_per_capita)
                    / nullif(next_year - prev_year, 0)
            when prev_per_capita is not null
                then prev_per_capita
            when next_per_capita is not null
                then next_per_capita
            else null
        end as per_capita_kg,

        -- formal_collection_rate: interpolate but clamp to [0, 1]
        case
            when formal_collection_rate is not null
                then formal_collection_rate
            when prev_fcr is not null and next_fcr is not null
                then greatest(0, least(1,
                    prev_fcr + (year - prev_year)::numeric
                    * (next_fcr - prev_fcr)
                    / nullif(next_year - prev_year, 0)
                ))
            when prev_fcr is not null
                then prev_fcr
            when next_fcr is not null
                then next_fcr
            else null
        end as formal_collection_rate,

        documentation_rate,

        -- Confidence tier: interpolated rows are downgraded
        case
            when total_mt is not null then coalesce(confidence_tier, 'reported')
            else 'interpolated'
        end as confidence_tier,

        -- Flag: true for any row that was not directly observed
        (total_mt is null) as is_interpolated,

        -- Keep track of data vintage
        {{ var('max_year') }} as data_vintage_year

    from with_surrounding

),

-- Drop country-years where we could not fill any data at all
final as (

    select *
    from interpolated
    where total_mt is not null

)

select * from final
