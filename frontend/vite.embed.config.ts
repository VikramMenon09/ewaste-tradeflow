import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist/embed',
    lib: {
      entry: path.resolve(__dirname, 'src/embed/main.tsx'),
      name: 'EWasteEmbed',
      fileName: 'ewaste-embed',
      formats: ['iife'],
    },
    rollupOptions: {
      output: {
        // No code splitting for embed — single bundle
        inlineDynamicImports: true,
      },
    },
  },
})
