{{
  config(
    materialized='table',
    description='Central trade flow reconciliation model. Joins Comtrade and OECD data, applies HS-to-UN-category mapping, computes Basel compliance flags, and propagates PRS risk flags. All downstream trade flow analysis depends on this model.'
  )
}}

/*
  Source priority logic:
  - For flows between two OECD members: prefer OECD data (more reliable transboundary reporting)
  - For all other flows: prefer Comtrade data (broader coverage)
  - Where both sources report the same route and diverge by >20%: flag data_conflict = TRUE
*/

with comtrade as (

    select
        year,
        -- For exports: reporter = exporter, partner = importer
        -- For imports: reporter = importer, partner = exporter
        -- Normalize to a consistent (exporter, importer) perspective
        case
            when flow_code = 'X' then reporter_iso3
            else partner_iso3
        end as exporter_iso3,
        case
            when flow_code = 'X' then partner_iso3
            else reporter_iso3
        end as importer_iso3,
        hs_code,
        un_category_code,
        volume_mt,
        trade_value_usd,
        confidence_tier,
        mapping_confidence,
        waste_fraction_scalar,
        source_id,
        'comtrade' as data_source

    from {{ ref('stg_comtrade') }}
    where flow_code = 'X'   -- Use export-reported flows as primary to avoid double counting

),

oecd as (

    select
        year,
        exporter_iso3,
        importer_iso3,
        null::varchar    as hs_code,
        ewaste_category_code as un_category_code,
        volume_mt,
        null::numeric    as trade_value_usd,
        confidence_tier,
        'HIGH'           as mapping_confidence,
        1.0              as waste_fraction_scalar,
        source_id,
        'oecd' as data_source

    from {{ ref('stg_oecd_flows') }}

),

-- Identify which flows appear in both sources
combined as (

    select *, 'comtrade' as preferred_source
    from comtrade

    union all

    select *, 'oecd' as preferred_source
    from oecd

),

-- OECD member lookup for source preference logic
oecd_members as (
    select iso3
    from {{ ref('mart_countries') }}
    where is_oecd_member = true
),

-- Apply source priority: OECD preferred for OECD-to-OECD flows
deduplicated as (

    select
        c.year,
        c.exporter_iso3,
        c.importer_iso3,
        c.hs_code,
        c.un_category_code,
        c.volume_mt,
        c.trade_value_usd,
        c.confidence_tier,
        c.mapping_confidence,
        c.waste_fraction_scalar,
        c.source_id,
        c.data_source,

        -- Flag if both sources reported this route
        count(*) over (
            partition by c.year, c.exporter_iso3, c.importer_iso3, c.un_category_code
        ) > 1 as has_dual_source,

        -- Flag data conflict: both sources reported but diverge by >20%
        case
            when count(*) over (
                partition by c.year, c.exporter_iso3, c.importer_iso3, c.un_category_code
            ) > 1
            then abs(
                c.volume_mt - avg(c.volume_mt) over (
                    partition by c.year, c.exporter_iso3, c.importer_iso3, c.un_category_code
                )
            ) / nullif(avg(c.volume_mt) over (
                partition by c.year, c.exporter_iso3, c.importer_iso3, c.un_category_code
            ), 0) > 0.20
            else false
        end as data_conflict,

        -- Row rank: for deduplication, OECD wins for OECD-OECD flows
        row_number() over (
            partition by c.year, c.exporter_iso3, c.importer_iso3, c.un_category_code
            order by
                case
                    when c.data_source = 'oecd'
                        and c.exporter_iso3 in (select iso3 from oecd_members)
                        and c.importer_iso3 in (select iso3 from oecd_members)
                    then 1   -- OECD preferred for OECD-OECD flows
                    when c.data_source = 'comtrade' then 2
                    else 3
                end
        ) as source_rank

    from combined c

),

-- Keep only the preferred source row per route
preferred as (

    select * from deduplicated
    where source_rank = 1

),

-- Join Basel Convention status for compliance flagging
with_basel as (

    select
        p.*,

        exp_c.basel_signatory            as exporter_basel_signatory,
        exp_c.basel_ban_ratified         as exporter_ban_ratified,
        imp_c.basel_signatory            as importer_basel_signatory,
        imp_c.basel_ban_ratified         as importer_ban_ratified,
        imp_c.income_classification      as importer_income_class

    from preferred p
    left join {{ ref('mart_countries') }} exp_c on p.exporter_iso3 = exp_c.iso3
    left join {{ ref('mart_countries') }} imp_c on p.importer_iso3 = imp_c.iso3

),

-- Compute Basel compliance flag
with_compliance as (

    select
        *,

        -- basel_compliant = TRUE only when:
        --   - Both exporter and importer are Basel signatories, AND
        --   - The flow does NOT violate the Basel Ban Amendment
        -- Basel Ban Amendment: prohibits OECD→non-OECD exports of hazardous waste
        -- (applies when exporter is OECD/EU and importer is non-OECD and ban-covered)
        case
            -- If we don't have treaty data for either country, mark as unknown (null)
            when exporter_basel_signatory is null or importer_basel_signatory is null
                then null::boolean

            -- Non-signatory importer: always flag
            when importer_basel_signatory = false
                then false

            -- Ban Amendment violation: OECD-listed exporter → non-OECD importer
            -- for waste categories covered by the Ban
            when exporter_ban_ratified = true
                and importer_ban_ratified = false
                and importer_income_class in ('low', 'lower_middle')
                and un_category_code in (0, 1, 2, 3, 4, 5, 6)
                then false

            else true
        end as basel_compliant

    from with_basel

),

-- Join PRS scores for risk flagging
final as (

    select
        wc.year,
        wc.exporter_iso3,
        wc.importer_iso3,
        wc.hs_code,
        wc.un_category_code,
        wc.volume_mt,
        wc.trade_value_usd,
        wc.confidence_tier,
        wc.mapping_confidence,
        wc.waste_fraction_scalar,
        wc.source_id,
        wc.data_source,
        wc.has_dual_source,
        wc.data_conflict,
        wc.exporter_basel_signatory,
        wc.exporter_ban_ratified,
        wc.importer_basel_signatory,
        wc.importer_ban_ratified,
        wc.importer_income_class,
        wc.basel_compliant,

        -- PRS risk flag: importer has PRS >= 7 (high or severe risk)
        coalesce(prs.prs_score >= 7, false) as prs_risk_flag,
        prs.prs_score as importer_prs_score,

        -- Adjusted volume accounting for waste fraction (for MEDIUM/LOW confidence codes)
        wc.volume_mt * wc.waste_fraction_scalar as estimated_ewaste_volume_mt,

        false as informal_estimate  -- reserved for future informal flow modeling

    from with_compliance wc
    left join {{ ref('mart_processing_risk_scores') }} prs
        on wc.importer_iso3 = prs.country_iso3
        and wc.year = prs.year

)

select * from final
