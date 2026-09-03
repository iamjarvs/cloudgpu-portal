import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-only proxy so the Vite dev server can talk to the FastAPI backend
// without CORS — production serves both from the same FastAPI process, so
// this proxy config is never used there.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ops': 'http://127.0.0.1:8000',
    },
  },
})
