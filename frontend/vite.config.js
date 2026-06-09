import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8765',
      '/whoop': 'http://localhost:8765',
      '/garmin': 'http://localhost:8765',
      '/strava': 'http://localhost:8765',
    },
  },
})
