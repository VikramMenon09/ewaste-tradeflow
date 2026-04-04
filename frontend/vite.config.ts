import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import type { Connect } from 'vite'

// ── Mock API middleware (used when no real API is running) ────────────────────
// Intercepts /api/v1/* requests in dev and returns realistic fixture data so
// the report view and other data-dependent pages render without a backend.

const MOCK_COUNTRIES = [
  { iso3:'CHN', name:'China', region:'Asia', subregion:'Eastern Asia', income_classification:'upper_middle', basel_signatory:true, basel_ban_ratified:false, is_oecd_member:false },
  { iso3:'USA', name:'United States', region:'Americas', subregion:'Northern America', income_classification:'high', basel_signatory:false, basel_ban_ratified:false, is_oecd_member:true },
  { iso3:'IND', name:'India', region:'Asia', subregion:'Southern Asia', income_classification:'lower_middle', basel_signatory:true, basel_ban_ratified:false, is_oecd_member:false },
  { iso3:'DEU', name:'Germany', region:'Europe', subregion:'Western Europe', income_classification:'high', basel_signatory:true, basel_ban_ratified:true, is_oecd_member:true },
  { iso3:'JPN', name:'Japan', region:'Asia', subregion:'Eastern Asia', income_classification:'high', basel_signatory:true, basel_ban_ratified:true, is_oecd_member:true },
  { iso3:'NGA', name:'Nigeria', region:'Africa', subregion:'Western Africa', income_classification:'lower_middle', basel_signatory:true, basel_ban_ratified:false, is_oecd_member:false },
  { iso3:'GHA', name:'Ghana', region:'Africa', subregion:'Western Africa', income_classification:'lower_middle', basel_signatory:true, basel_ban_ratified:false, is_oecd_member:false },
  { iso3:'BRA', name:'Brazil', region:'Americas', subregion:'South America', income_classification:'upper_middle', basel_signatory:true, basel_ban_ratified:false, is_oecd_member:false },
]

// Base country list sorted largest→smallest by generation (index used to derive other metrics)
const MOCK_CHOROPLETH_BASE = [
  { iso3:'CHN', name:'China',          gen:11200000, tier:'reported',  pop:1412000 },
  { iso3:'USA', name:'United States',  gen:6900000,  tier:'reported',  pop:336000  },
  { iso3:'IND', name:'India',          gen:4200000,  tier:'reported',  pop:1429000 },
  { iso3:'JPN', name:'Japan',          gen:2800000,  tier:'reported',  pop:125000  },
  { iso3:'BRA', name:'Brazil',         gen:2100000,  tier:'reported',  pop:215000  },
  { iso3:'DEU', name:'Germany',        gen:1900000,  tier:'reported',  pop:84000   },
  { iso3:'RUS', name:'Russia',         gen:1700000,  tier:'estimated', pop:144000  },
  { iso3:'GBR', name:'United Kingdom', gen:1500000,  tier:'estimated', pop:68000   },
  { iso3:'FRA', name:'France',         gen:1300000,  tier:'reported',  pop:68000   },
  { iso3:'IDN', name:'Indonesia',      gen:1100000,  tier:'estimated', pop:278000  },
  { iso3:'NGA', name:'Nigeria',        gen:850000,   tier:'estimated', pop:223000  },
  { iso3:'KOR', name:'South Korea',    gen:820000,   tier:'reported',  pop:52000   },
  { iso3:'ITA', name:'Italy',          gen:780000,   tier:'reported',  pop:59000   },
  { iso3:'CAN', name:'Canada',         gen:720000,   tier:'reported',  pop:38000   },
  { iso3:'MEX', name:'Mexico',         gen:680000,   tier:'estimated', pop:128000  },
  { iso3:'ESP', name:'Spain',          gen:640000,   tier:'reported',  pop:47000   },
  { iso3:'AUS', name:'Australia',      gen:610000,   tier:'reported',  pop:26000   },
  { iso3:'TUR', name:'Turkey',         gen:590000,   tier:'estimated', pop:85000   },
  { iso3:'POL', name:'Poland',         gen:420000,   tier:'reported',  pop:38000   },
  { iso3:'ZAF', name:'South Africa',   gen:400000,   tier:'estimated', pop:60000   },
  { iso3:'ARG', name:'Argentina',      gen:370000,   tier:'estimated', pop:46000   },
  { iso3:'EGY', name:'Egypt',          gen:360000,   tier:'estimated', pop:105000  },
  { iso3:'NLD', name:'Netherlands',    gen:340000,   tier:'reported',  pop:17000   },
  { iso3:'BEL', name:'Belgium',        gen:280000,   tier:'reported',  pop:11000   },
  { iso3:'SWE', name:'Sweden',         gen:270000,   tier:'reported',  pop:10000   },
  { iso3:'CHE', name:'Switzerland',    gen:260000,   tier:'reported',  pop:8600    },
  { iso3:'THA', name:'Thailand',       gen:250000,   tier:'estimated', pop:72000   },
  { iso3:'PHL', name:'Philippines',    gen:240000,   tier:'estimated', pop:115000  },
  { iso3:'MYS', name:'Malaysia',       gen:230000,   tier:'estimated', pop:33000   },
  { iso3:'PAK', name:'Pakistan',       gen:220000,   tier:'estimated', pop:232000  },
  { iso3:'BGD', name:'Bangladesh',     gen:200000,   tier:'estimated', pop:171000  },
  { iso3:'COL', name:'Colombia',       gen:190000,   tier:'estimated', pop:52000   },
  { iso3:'VNM', name:'Vietnam',        gen:185000,   tier:'estimated', pop:98000   },
  { iso3:'IRN', name:'Iran',           gen:180000,   tier:'estimated', pop:88000   },
  { iso3:'NOR', name:'Norway',         gen:160000,   tier:'reported',  pop:5400    },
  { iso3:'DNK', name:'Denmark',        gen:155000,   tier:'reported',  pop:5900    },
  { iso3:'FIN', name:'Finland',        gen:140000,   tier:'reported',  pop:5500    },
  { iso3:'AUT', name:'Austria',        gen:138000,   tier:'reported',  pop:9000    },
  { iso3:'GHA', name:'Ghana',          gen:130000,   tier:'estimated', pop:33000   },
  { iso3:'ETH', name:'Ethiopia',       gen:125000,   tier:'estimated', pop:126000  },
  { iso3:'KEN', name:'Kenya',          gen:120000,   tier:'estimated', pop:55000   },
  { iso3:'CHL', name:'Chile',          gen:115000,   tier:'estimated', pop:19000   },
  { iso3:'PER', name:'Peru',           gen:105000,   tier:'estimated', pop:34000   },
  { iso3:'CZE', name:'Czech Republic', gen:100000,   tier:'reported',  pop:11000   },
  { iso3:'PRT', name:'Portugal',       gen:95000,    tier:'reported',  pop:10000   },
  { iso3:'GRC', name:'Greece',         gen:90000,    tier:'reported',  pop:11000   },
  { iso3:'HUN', name:'Hungary',        gen:85000,    tier:'reported',  pop:10000   },
  { iso3:'NZL', name:'New Zealand',    gen:80000,    tier:'reported',  pop:5100    },
  { iso3:'SGP', name:'Singapore',      gen:75000,    tier:'reported',  pop:5900    },
  { iso3:'ISR', name:'Israel',         gen:70000,    tier:'reported',  pop:9200    },
  { iso3:'UKR', name:'Ukraine',        gen:65000,    tier:'estimated', pop:44000   },
]

// High-income OECD set for compliance/collection heuristics
const OECD_SET = new Set(['USA','DEU','JPN','GBR','FRA','KOR','ITA','CAN','ESP','AUS','NLD','BEL','SWE','CHE','NOR','DNK','FIN','AUT','CZE','PRT','GRC','HUN','NZL','SGP','ISR'])

function buildChoropleth(metric: string, year: number) {
  const countries = MOCK_CHOROPLETH_BASE.map((c, i) => {
    const n = MOCK_CHOROPLETH_BASE.length
    const frac = i / (n - 1) // 0 = largest generator, 1 = smallest

    let value: number
    switch (metric) {
      case 'per_capita':
        // kg per 1000 population
        value = (c.gen / c.pop) * 1000
        break
      case 'exports':
        // Wealthier nations export more; developing import more
        value = OECD_SET.has(c.iso3) ? c.gen * (0.08 + (1 - frac) * 0.06) : c.gen * 0.03
        break
      case 'imports':
        value = !OECD_SET.has(c.iso3) ? c.gen * (0.12 + frac * 0.08) : c.gen * 0.02
        break
      case 'net_trade':
        value = OECD_SET.has(c.iso3) ? c.gen * (0.05 + (1 - frac) * 0.04) : -c.gen * (0.05 + frac * 0.05)
        break
      case 'prs':
        // OECD = low risk (1-3), others gradient up to 9
        value = OECD_SET.has(c.iso3) ? 1.2 + (1 - frac) * 1.5 : 4 + frac * 5
        break
      case 'formal_collection':
        value = OECD_SET.has(c.iso3) ? 0.45 + (1 - frac) * 0.45 : 0.03 + (1 - frac) * 0.18
        break
      case 'compliance_rate':
        value = OECD_SET.has(c.iso3) ? 0.72 + (1 - frac) * 0.25 : 0.15 + (1 - frac) * 0.35
        break
      case 'export_intensity':
        value = OECD_SET.has(c.iso3) ? 0.04 + (1 - frac) * 0.18 : 0.01 + frac * 0.04
        break
      default: // generation
        value = c.gen
    }

    return {
      iso3: c.iso3,
      name: c.name,
      value,
      confidence_tier: c.tier,
      data_vintage_year: year,
      is_missing: false,
    }
  })

  return { year, metric, countries }
}

const MOCK_SANKEY = {
  year: 2022,
  nodes: [
    {id:'CHN',name:'China',region:'Asia'},{id:'USA',name:'United States',region:'Americas'},
    {id:'DEU',name:'Germany',region:'Europe'},{id:'NGA',name:'Nigeria',region:'Africa'},
    {id:'IND',name:'India',region:'Asia'},{id:'GHA',name:'Ghana',region:'Africa'},
    {id:'JPN',name:'Japan',region:'Asia'},{id:'GBR',name:'United Kingdom',region:'Europe'},
  ],
  links: [
    {source:'CHN',target:'NGA',volume_mt:320000,value_usd:null,compliance_color:'red',has_violation:true,prs_risk_flag:true,importer_prs_score:8.2,data_conflict:false,confidence_tier:'reported',mapping_confidence:'HIGH'},
    {source:'USA',target:'GHA',volume_mt:210000,value_usd:null,compliance_color:'amber',has_violation:false,prs_risk_flag:true,importer_prs_score:7.1,data_conflict:false,confidence_tier:'reported',mapping_confidence:'HIGH'},
    {source:'DEU',target:'NGA',volume_mt:180000,value_usd:null,compliance_color:'red',has_violation:true,prs_risk_flag:true,importer_prs_score:8.2,data_conflict:false,confidence_tier:'reported',mapping_confidence:'HIGH'},
    {source:'JPN',target:'IND',volume_mt:150000,value_usd:null,compliance_color:'green',has_violation:false,prs_risk_flag:false,importer_prs_score:4.1,data_conflict:false,confidence_tier:'reported',mapping_confidence:'MEDIUM'},
    {source:'GBR',target:'GHA',volume_mt:95000,value_usd:null,compliance_color:'amber',has_violation:false,prs_risk_flag:true,importer_prs_score:7.1,data_conflict:false,confidence_tier:'estimated',mapping_confidence:'MEDIUM'},
  ],
}

const MOCK_COUNTRY_PROFILE = {
  iso3:'DEU', name:'Germany', region:'Europe', subregion:'Western Europe',
  income_classification:'high', basel_signatory:true, basel_ban_ratified:true, is_oecd_member:true,
  prs_score:1.8, prs_methodology_version:1,
  generation_series:[
    {year:2015,total_mt:1540000,per_capita_kg:18.9,formal_collection_rate:0.41,confidence_tier:'reported',is_interpolated:false},
    {year:2016,total_mt:1580000,per_capita_kg:19.2,formal_collection_rate:0.43,confidence_tier:'reported',is_interpolated:false},
    {year:2017,total_mt:1620000,per_capita_kg:19.5,formal_collection_rate:0.44,confidence_tier:'reported',is_interpolated:false},
    {year:2018,total_mt:1680000,per_capita_kg:20.1,formal_collection_rate:0.45,confidence_tier:'reported',is_interpolated:false},
    {year:2019,total_mt:1730000,per_capita_kg:20.7,formal_collection_rate:0.46,confidence_tier:'interpolated',is_interpolated:true},
    {year:2020,total_mt:1780000,per_capita_kg:21.3,formal_collection_rate:0.47,confidence_tier:'interpolated',is_interpolated:true},
    {year:2021,total_mt:1840000,per_capita_kg:21.9,formal_collection_rate:0.48,confidence_tier:'estimated',is_interpolated:false},
    {year:2022,total_mt:1900000,per_capita_kg:22.6,formal_collection_rate:0.49,confidence_tier:'reported',is_interpolated:false},
  ],
  top_exports:[
    {partner_iso3:'NGA',partner_name:'Nigeria',volume_mt:180000,value_usd:null,prs_risk_flag:true,compliance_color:'red',basel_compliant:false},
    {partner_iso3:'IND',partner_name:'India',volume_mt:95000,value_usd:null,prs_risk_flag:false,compliance_color:'green',basel_compliant:true},
    {partner_iso3:'POL',partner_name:'Poland',volume_mt:72000,value_usd:null,prs_risk_flag:false,compliance_color:'green',basel_compliant:true},
  ],
  top_imports:[
    {partner_iso3:'CHN',partner_name:'China',volume_mt:45000,value_usd:null,prs_risk_flag:false,compliance_color:'green'},
    {partner_iso3:'USA',partner_name:'United States',volume_mt:32000,value_usd:null,prs_risk_flag:false,compliance_color:'amber'},
  ],
}

function mockApiMiddleware(): Connect.HandleFunction {
  return (req, res, next) => {
    const url = req.url ?? ''

    if (!url.startsWith('/api/v1')) { next(); return }

    res.setHeader('Content-Type', 'application/json')
    res.setHeader('Access-Control-Allow-Origin', '*')
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Authorization,Content-Type')

    if (req.method === 'OPTIONS') { res.statusCode = 204; res.end(); return }

    const json = (data: unknown) => { res.statusCode = 200; res.end(JSON.stringify(data)) }

    if (url.includes('/map/choropleth')) {
      const params = new URLSearchParams(url.split('?')[1] ?? '')
      const metric = params.get('metric') ?? 'generation'
      const year = parseInt(params.get('year') ?? '2022', 10)
      return json(buildChoropleth(metric, year))
    }
    if (url.includes('/map/flows/sankey')) return json(MOCK_SANKEY)
    if (url.includes('/countries')) return json(MOCK_COUNTRIES)
    if (url.match(/\/country\/([A-Z]{3})\/profile/)) {
      const iso3Match = url.match(/\/country\/([A-Z]{3})\/profile/)
      const iso3 = iso3Match?.[1]
      if (iso3 && iso3 !== 'DEU') {
        return json({
          iso3, name: iso3 === 'NGA' ? 'Nigeria' : iso3 === 'CHN' ? 'China' : iso3 === 'USA' ? 'United States' : iso3,
          region: iso3 === 'NGA' ? 'Africa' : iso3 === 'CHN' ? 'Asia' : 'Americas',
          subregion: iso3 === 'NGA' ? 'Western Africa' : iso3 === 'CHN' ? 'Eastern Asia' : 'Northern America',
          income_classification: iso3 === 'NGA' ? 'lower_middle' : iso3 === 'CHN' ? 'upper_middle' : 'high',
          basel_signatory: true, basel_ban_ratified: false, is_oecd_member: false,
          prs_score: iso3 === 'NGA' ? 8.2 : 6.1, prs_methodology_version: 1,
          generation_series: MOCK_COUNTRY_PROFILE.generation_series.map(s => ({ ...s, total_mt: Math.round(s.total_mt * 0.3) })),
          top_exports: [], top_imports: [],
        })
      }
      return json(MOCK_COUNTRY_PROFILE)
    }
    if (url.includes('/generation/')) return json({ iso3:'DEU', series: MOCK_COUNTRY_PROFILE.generation_series })
    if (url.includes('/health')) return json({ status:'ok', env:'development' })

    // Unhandled — pass to real backend if available, otherwise 404
    next()
  }
}

const mockApiPlugin = {
  name: 'mock-api',
  configureServer(server: { middlewares: { use: (fn: Connect.HandleFunction) => void } }) {
    server.middlewares.use(mockApiMiddleware())
  },
}

export default defineConfig({
  plugins: [react(), mockApiPlugin],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
  },
  server: {
    port: 5173,
  },
})
