/**
 * EmbedButton — lets authenticated users generate an embeddable iframe snippet
 * for the current map/Sankey view in one click (PRD US-05).
 *
 * Clicking "Embed" creates a scoped embed token via the API and immediately
 * shows the ready-to-paste <div> + <script> snippet.
 */

import { useState } from 'react'
import { useFilterStore } from '@/shared/stores/filterStore'
import { api } from '@/lib/api-client'

export default function EmbedButton() {
  const { year, metric, activeView } = useFilterStore()
  const [open, setOpen] = useState(false)
  const [snippet, setSnippet] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function handleOpen() {
    setOpen(true)
    if (snippet) return // already generated

    setLoading(true)
    setError(null)
    try {
      const res = await api.createEmbedToken({
        label: `${metric} map — ${year}`,
        default_filters: { year, metric, view: activeView },
      })

      const apiUrl = import.meta.env.VITE_API_URL ?? 'https://api.ewaste-tradeflow.vercel.app'
      const cdnUrl = import.meta.env.VITE_EMBED_CDN_URL ?? 'https://cdn.ewaste-tradeflow.vercel.app/ewaste-embed.js'

      const code = [
        `<!-- EWasteTradeFlow embed -->`,
        `<div`,
        `  id="ewaste-embed"`,
        `  data-year="${year}"`,
        `  data-metric="${metric}"`,
        `  data-view="${activeView}"`,
        `  data-token="${res.token}"`,
        `  data-api-url="${apiUrl}"`,
        `  style="min-height:480px"`,
        `></div>`,
        `<script src="${cdnUrl}" async></script>`,
      ].join('\n')

      setSnippet(code)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate embed token')
    } finally {
      setLoading(false)
    }
  }

  function handleCopy() {
    if (!snippet) return
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function handleClose() {
    setOpen(false)
  }

  return (
    <>
      <button
        onClick={handleOpen}
        className="flex items-center gap-1.5 px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
        title="Get embeddable iframe code for this view"
      >
        {/* Embed icon */}
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
        Embed
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={handleClose}
        >
          <div
            className="relative bg-gray-900 border border-gray-700 rounded-lg shadow-2xl w-full max-w-lg mx-4 p-5"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">Embed this view</h2>
              <button
                onClick={handleClose}
                className="text-gray-500 hover:text-white transition-colors"
                aria-label="Close"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p className="text-xs text-gray-400 mb-4">
              Paste this snippet into any HTML page. No login required for viewers. The embed shows
              the <strong className="text-gray-300">{metric}</strong> view for{' '}
              <strong className="text-gray-300">{year}</strong>.
            </p>

            {loading && (
              <div className="flex items-center gap-2 text-xs text-gray-400 py-6 justify-center">
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating embed token…
              </div>
            )}

            {error && (
              <div className="text-xs text-red-400 bg-red-900/20 border border-red-800 rounded px-3 py-2 mb-3">
                {error}
              </div>
            )}

            {snippet && !loading && (
              <>
                <pre className="text-xs bg-gray-950 border border-gray-800 rounded p-3 overflow-x-auto whitespace-pre text-emerald-300 font-mono leading-relaxed mb-3">
                  {snippet}
                </pre>
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={handleCopy}
                    className="px-3 py-1.5 text-xs rounded bg-emerald-700 hover:bg-emerald-600 text-white transition-colors"
                  >
                    {copied ? 'Copied!' : 'Copy snippet'}
                  </button>
                  <button
                    onClick={handleClose}
                    className="px-3 py-1.5 text-xs rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
                  >
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
