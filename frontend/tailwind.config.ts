import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'ewaste-green': '#22c55e',
        'ewaste-amber': '#f59e0b',
        'ewaste-red': '#ef4444',
        // Neutral scale bound to the theme tokens in index.css, so utility
        // classes (bg-gray-900, text-gray-400, ...) follow light/dark mode.
        gray: {
          100: 'var(--c-text)',
          200: 'var(--c-text)',
          300: 'var(--c-text-2)',
          400: 'var(--c-text-2)',
          500: 'var(--c-text-3)',
          600: 'var(--c-text-3)',
          700: 'var(--c-border)',
          800: 'var(--c-raised)',
          900: 'var(--c-surface)',
          950: 'var(--c-bg)',
        },
        emerald: {
          300: 'var(--c-accent)',
          400: 'var(--c-accent)',
          500: 'var(--c-accent)',
          600: '#15803d',
          700: '#166534',
        },
      },
    },
  },
  plugins: [],
}

export default config
