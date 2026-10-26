/**
 * Test de fumée de l'interface : monte l'application React complète dans jsdom,
 * avec un vrai backend, et vérifie que les vues principales se rendent sans erreur.
 *
 * Pré-requis : API joignable sur SHELLFORGE_API (par défaut http://127.0.0.1:8000).
 * Usage : npm run test:ui
 */

import { JSDOM } from 'jsdom'
import { createServer } from 'vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const API = process.env.SHELLFORGE_API || 'http://127.0.0.1:8000'
const realFetch = globalThis.fetch

function setupDom() {
  const dom = new JSDOM('<!doctype html><html><body><div id="app"></div></body></html>', {
    url: 'http://localhost:5173/',
    pretendToBeVisual: true,
  })
  const win = dom.window
  global.window = win
  global.document = win.document
  Object.defineProperty(globalThis, 'navigator', { value: win.navigator, configurable: true })
  global.HTMLElement = win.HTMLElement
  global.HTMLTextAreaElement = win.HTMLTextAreaElement
  global.Node = win.Node
  global.Event = win.Event
  global.MutationObserver = win.MutationObserver
  global.getComputedStyle = win.getComputedStyle
  global.requestAnimationFrame = (callback) => setTimeout(callback, 0)
  global.cancelAnimationFrame = (handle) => clearTimeout(handle)

  const store = new Map()
  const localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
  }
  Object.defineProperty(globalThis, 'localStorage', { value: localStorage, configurable: true })
  Object.defineProperty(win, 'localStorage', { value: localStorage, configurable: true })

  global.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : input.url
    return realFetch(url.startsWith('http') ? url : `${API}${url}`, init)
  }

  return dom
}

async function waitFor(predicate, label, timeout = 8000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    if (predicate()) return
    await new Promise((resolve) => setTimeout(resolve, 50))
  }
  const seen = (document.body.textContent || '').replace(/\s+/g, ' ').slice(0, 400)
  throw new Error(`Délai dépassé en attendant : ${label}\n  Page affichée : ${seen}`)
}

async function ensureApi() {
  try {
    const response = await realFetch(`${API}/api/health`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
  } catch (error) {
    throw new Error(
      `API injoignable sur ${API} (${error.message}).\n` +
        'Démarre-la avec : .venv/bin/uvicorn main:app --app-dir backend --port 8000',
    )
  }
}

async function main() {
  await ensureApi()
  const dom = setupDom()
  const server = await createServer({
    root: ROOT,
    logLevel: 'error',
    appType: 'custom',
    server: { middlewareMode: true },
  })

  try {
    const React = (await import('react')).default
    const { createRoot } = await import('react-dom/client')
    const { MemoryRouter } = await import('react-router-dom')
    const { default: App } = await server.ssrLoadModule('/src/App.jsx')

    const mounting = createRoot(document.getElementById('app'))
    const errors = []
    const originalError = console.error
    console.error = (...args) => {
      errors.push(args.join(' '))
      originalError(...args)
    }

    const checks = []
    let route = '/'

    const clickButton = (label) => {
      const target = [...document.querySelectorAll('button')].find((button) =>
        (button.textContent || '').trim().startsWith(label),
      )
      if (!target) throw new Error(`Bouton introuvable sur ${route} : « ${label} »`)
      target.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
    }

    const waitText = async (text) => {
      await waitFor(() => document.body.textContent.includes(text), `${route} → « ${text} »`)
      checks.push(`${route} · ${text}`)
    }

    const visit = async (path, steps) => {
      route = path
      mounting.render(
        React.createElement(
          MemoryRouter,
          { initialEntries: [path], key: path },
          React.createElement(App),
        ),
      )
      for (const step of steps) {
        if (typeof step === 'string') await waitText(step)
        else if (step.click) clickButton(step.click)
      }
    }

    // Scénario « base réinitialisée » : le navigateur garde une session qui n'existe plus.
    const staleId = 'session-perimee-0001'
    localStorage.setItem('shellforge_session_id', staleId)
    await visit('/', ['SHELLFORGE', 'Fondations', 'missions validées'])
    const recovered = localStorage.getItem('shellforge_session_id')
    if (!recovered || recovered === staleId) {
      throw new Error('Session périmée non remplacée par une session valide')
    }
    checks.push(`session périmée (${staleId}) → nouvelle session`)
    await visit('/niveau/1', ['Niveau 1', 'missions'])
    await visit('/module/m01', ['Cartographier un serveur inconnu'])
    await visit('/mission/m01-01', [
      'Le cours',
      'Marquer comme lu',
      'Laboratoire',
      { click: 'Laboratoire' },
      'Vérifier mes preuves',
      'Le laboratoire',
      { click: 'Fichiers' },
      'Espace de travail',
    ])
    await visit('/progression', ['Ta progression', 'Activité récente'])

    console.error = originalError

    const content = document.body.textContent
    if (!content.includes('Ta progression')) throw new Error('Navigation inter-écrans incohérente')
    if (errors.length > 0) {
      throw new Error(`Erreurs console pendant le rendu :\n${errors.join('\n')}`)
    }

    console.log(`UI OK — ${checks.length} assertions sur 5 écrans`)
    for (const check of checks) console.log(`  ✓ ${check}`)
    mounting.unmount()
  } finally {
    await server.close()
    dom.window.close()
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
