import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// L'API FastAPI tourne sur le port 8000. En développement (et en prévisualisation),
// le front appelle des URL relatives (/api/...) et Vite les proxifie vers le backend.
const API_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: Number(process.env.PORT) || 5173,
    strictPort: false,
    // Autorise les hôtes de prévisualisation (ex: https://5173-xxxx.e2b.app)
    allowedHosts: true,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/docs': {
        target: API_TARGET,
        changeOrigin: true,
      },
      '/openapi.json': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    allowedHosts: true,
  },
})
