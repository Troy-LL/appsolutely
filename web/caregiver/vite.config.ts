import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The hub (brain/server.py) serves /ws, /questions, /media and /health.
// In dev we proxy those to the hub so the page and the socket share one origin,
// which is what web/fake-feed's openHubFeed() expects when the URL has ?feed=hub.
const HUB = process.env.HUB || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  base: '/caregiver/',
  server: {
    host: true,
    port: 5173,
    // lets us import ../fake-feed/index.js and ../../brain/seed.json
    fs: { allow: ['../..'] },
    proxy: {
      '/ws': { target: HUB, ws: true, changeOrigin: true },
      '/questions': { target: HUB, changeOrigin: true },
      '/media': { target: HUB, changeOrigin: true },
      '/health': { target: HUB, changeOrigin: true },
    },
  },
})
