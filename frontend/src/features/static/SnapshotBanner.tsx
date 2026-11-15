import { useState } from 'react'
import { useSnapshotMeta } from '@/lib/static-data'

/** Thin notice shown in static-data mode: snapshot date, sources, caveats. */
export default function SnapshotBanner() {
  const { data: meta } = useSnapshotMeta()
  const [open, setOpen] = useState(false)

  if (!meta) return null

  const shortSources = 'OECD e-waste statistics, UN SDG 12.4.2 (UNITAR), World Bank WGI, UN Treaty Collection (Basel)'

  return (
    <div
      className="text-xs px-4 py-1"
      style={{ background: 'var(--c-raised)', borderBottom: '1px solid var(--c-border)', color: 'var(--c-text-2)' }}
      role="note"
      aria-label="Data snapshot notice"
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
        <span>
          <strong style={{ color: 'var(--c-text)' }}>Data snapshot as of {meta.snapshot_date}</strong>; sources: {shortSources}.
        </span>
        <span style={{ color: 'var(--c-text-3)' }}>
          Trade-flow metrics and the Sankey diagram need the full stack (UN Comtrade).
        </span>
        <button
          onClick={() => setOpen((o) => !o)}
          className="underline"
          style={{ color: 'var(--c-accent)' }}
          aria-expanded={open}
        >
          {open ? 'Hide details' : 'Details'}
        </button>
      </div>

      {open && (
        <div className="mt-2 mb-1 grid gap-3 md:grid-cols-2" style={{ lineHeight: 1.5 }}>
          <div>
            <p className="font-semibold mb-1" style={{ color: 'var(--c-text)' }}>Sources</p>
            <ul className="list-disc pl-4">
              {meta.sources.map((s) => (
                <li key={s.name}>
                  <a href={s.url} target="_blank" rel="noreferrer" className="underline">{s.name}</a>
                  <span style={{ color: 'var(--c-text-3)' }}> · {s.used_for}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold mb-1" style={{ color: 'var(--c-text)' }}>How this snapshot was built</p>
            <ul className="list-disc pl-4">
              {meta.notes.map((n) => <li key={n}>{n}</li>)}
              <li>
                Coverage: {meta.counts.countries_with_generation} countries with generation data,{' '}
                {meta.counts.countries_with_prs} with a PRS.
              </li>
              {meta.excluded.length > 0 && (
                <li>
                  Excluded as implausible: {meta.excluded.map((e) => e.iso3).join(', ')}.
                </li>
              )}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
