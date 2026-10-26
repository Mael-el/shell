import { apiUrl } from './config'

const SESSION_KEY = 'shellforge_session_id'

export const getSessionId = () => localStorage.getItem(SESSION_KEY)

export const resetSession = () => localStorage.removeItem(SESSION_KEY)

export async function ensureSession() {
  const existing = getSessionId()
  if (existing) {
    // La base peut avoir été réinitialisée (session inconnue) : on vérifie avant usage.
    try {
      const check = await fetch(apiUrl(`/api/sessions/${encodeURIComponent(existing)}`))
      if (check.ok) return existing
      localStorage.removeItem(SESSION_KEY)
    } catch (err) {
      if (err instanceof TypeError) throw new Error('API injoignable : vérifie que le backend est démarré')
    }
  }
  const response = await fetch(apiUrl('/api/sessions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: 'shellforge-user' }),
  })
  if (!response.ok) throw new Error('Impossible de créer une session')
  const data = await response.json()
  localStorage.setItem(SESSION_KEY, data.session_id)
  return data.session_id
}

export async function api(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Requête refusée par le serveur'
    throw new Error(detail)
  }
  return data
}

export const withSession = (path, sessionId) =>
  `${path}${path.includes('?') ? '&' : '?'}session_id=${encodeURIComponent(sessionId)}`

export const difficultyLabel = {
  easy: 'Facile',
  medium: 'Moyen',
  hard: 'Difficile',
  expert: 'Expert',
}
