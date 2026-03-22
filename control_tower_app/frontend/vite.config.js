import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Proxy /api calls to FastAPI during dev so CORS is never an issue
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
