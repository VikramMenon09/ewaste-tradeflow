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
      },
    },
  },
  plugins: [],
}

export default config
