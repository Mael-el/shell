// Par défaut, on utilise des URL relatives : le front est servi par Vite (ou par un
// reverse proxy) qui redirige /api vers le backend FastAPI. Cela évite les problèmes
// de CORS et fonctionne aussi bien en local qu'en prévisualisation.
// Définir VITE_API_URL (ex: http://localhost:8000) pour appeler un backend distant.
const rawBaseUrl = import.meta.env.VITE_API_URL || ''

export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '')

export const apiUrl = (path = '') => {
  if (!path) return API_BASE_URL
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}
