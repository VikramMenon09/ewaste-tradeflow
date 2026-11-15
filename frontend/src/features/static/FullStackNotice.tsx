import { useSnapshotMeta } from '@/lib/static-data'

/** Placeholder for views that cannot run from the static snapshot. */
export default function FullStackNotice({ feature }: { feature: string }) {
  const { data: meta } = useSnapshotMeta()
  return (
    <div className="flex items-center justify-center h-full p-6">
      <div
        className="max-w-md text-sm rounded p-5"
        style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)', color: 'var(--c-text-2)' }}
      >
        <p className="font-semibold mb-2" style={{ color: 'var(--c-text)' }}>
          {feature} needs the full stack
        </p>
        <p style={{ lineHeight: 1.55 }}>
          {meta?.unavailable_reason ?? 'Needs UN Comtrade bilateral trade data (API key) and the full backend.'}{' '}
          This public demo is a static snapshot, so it shows e-waste generation, collection rates and the
          Processing Risk Score only. See the README for running the full pipeline.
        </p>
      </div>
    </div>
  )
}
