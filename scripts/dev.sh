#!/usr/bin/env bash
# Démarre le backend (FastAPI) et le frontend (Vite) en une commande.
# Usage : ./scripts/dev.sh   ·   Ctrl-C arrête les deux processus.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${SHELLFORGE_API_PORT:-8000}"
WEB_PORT="${SHELLFORGE_WEB_PORT:-5173}"

if [[ -x "$ROOT/.venv/bin/uvicorn" ]]; then
  UVICORN="$ROOT/.venv/bin/uvicorn"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  UVICORN="$ROOT/.venv/bin/python -m uvicorn"
else
  UVICORN="$(command -v uvicorn || echo 'python3 -m uvicorn')"
fi

if [[ ! -d "$ROOT/frontend/shellforge-app/node_modules" ]]; then
  echo "→ installation des dépendances front (npm install)"
  (cd "$ROOT/frontend/shellforge-app" && npm install)
fi

cleanup() {
  trap - INT TERM EXIT
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "→ API         http://0.0.0.0:$API_PORT  (docs : /docs)"
$UVICORN main:app --app-dir "$ROOT/backend" --host 0.0.0.0 --port "$API_PORT" \
  --reload --reload-dir "$ROOT/backend" --reload-dir "$ROOT/scripts" &
API_PID=$!

for _ in $(seq 1 40); do
  curl -fsS "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1 && break
  sleep 0.5
done

echo "→ Frontend    http://0.0.0.0:$WEB_PORT"
(cd "$ROOT/frontend/shellforge-app" && npm run dev -- --host 0.0.0.0 --port "$WEB_PORT") &
WEB_PID=$!

wait -n "$API_PID" "$WEB_PID"
