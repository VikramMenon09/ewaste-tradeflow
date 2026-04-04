import { useState } from 'react'
import { useFilterStore } from '@/shared/stores/filterStore'
import { encodeFilters } from '@/lib/url-codec'
import Tooltip from '@/shared/components/Tooltip'

export default function ShareButton() {
  const [copied, setCopied] = useState(false)
  const filterState = useFilterStore()

  function handleCopy() {
    const params = encodeFilters(filterState)
    const url = `${window.location.origin}${window.location.pathname}?${params.toString()}`
    void navigator.clipboard.writeText(url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <Tooltip content={copied ? 'Copied!' : 'Copy shareable link'} placement="bottom">
      <button
        onClick={handleCopy}
        className="flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors"
        style={{ color: 'var(--c-text-2)' }}
        aria-label="Share current view"
      >
        {copied ? (
          <span style={{ color: '#166534' }}>✓ Copied</span>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            Share
          </>
        )}
      </button>
    </Tooltip>
  )
}
