# SHELLFORGE

Plateforme d'apprentissage interactive de Bash/Linux : un backend **FastAPI** (missions,
progression, laboratoire Bash isolé) et une interface **React + Vite** avec terminal xterm.

## Architecture

```
backend/main.py            API FastAPI (SQLite, exécution des commandes du labo)
backend/database/init.sql   Schéma SQL de référence
docker-labs/level-01..07    Scripts d'exemple des missions
frontend/shellforge-app     Interface React (Vite, React Router, xterm)
tests/test_api_smoke.py     Tests de fumée de l'API
```

### API principale

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/modules` | Liste des modules |
| GET | `/api/modules/{id}/challenges` | Missions d'un module (sans les réponses) |
| GET | `/api/challenges/{id}` | Détail d'une mission + moteur pédagogique |
| POST | `/api/sessions` | Créer une session d'apprentissage |
| POST | `/api/submissions` | Valider une mission |
| POST | `/api/learning/progress` | Marquer une leçon comme terminée |
| GET | `/api/sessions/{id}/summary` | XP, niveau, progression par module |
| GET | `/api/labs/files` | Fichiers du workspace de mission |
| POST | `/api/labs/run` | Exécuter une commande Bash dans le workspace |
| POST | `/api/labs/reset` | Réinitialiser le workspace |

Documentation interactive : `http://localhost:8000/docs`.

## Démarrage rapide

### 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

La base SQLite est créée automatiquement au démarrage (`database/shellforge.db`,
chemin surchargeable avec `SHELLFORGE_DB_PATH`). Voir `.env.example`.

### 2. Frontend

```bash
cd frontend/shellforge-app
npm install
npm run dev        # http://localhost:5173
```

Le front appelle des URL relatives (`/api/...`) : Vite les proxifie vers
`http://127.0.0.1:8000` (surchargeable avec `VITE_API_PROXY_TARGET`). Il n'y a donc
aucun problème de CORS, y compris derrière un proxy de prévisualisation.
Pour appeler un backend distant, définir `VITE_API_URL`.

### 3. Tests

```bash
source .venv/bin/activate
pytest -q
```

## Configuration

| Variable | Défaut | Description |
|---|---|---|
| `SHELLFORGE_DB_DIR` | `./database` | Dossier de la base SQLite |
| `SHELLFORGE_DB_PATH` | `./database/shellforge.db` | Chemin exact de la base |
| `CORS_ALLOWED_ORIGINS` | localhost:5173-5175 | Origines CORS explicites |
| `CORS_ALLOWED_ORIGIN_REGEX` | localhost + `*.e2b.app` | Origines CORS par regex (prévisualisation) |
| `VITE_API_URL` | *(vide)* | Base d'URL de l'API côté front |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Cible du proxy Vite |

## Laboratoire Bash

Le labo crée un espace de travail par session dans
`$TMPDIR/shellforge-labs/<session_id>/<challenge_id>`, prérempli avec des fichiers
d'exercice, puis exécute la commande avec `bash -lc` (timeout 10 s, `HOME` redirigé).
Les chemins sont validés (pas de `..`, pas de liens symboliques) et quelques commandes
destructrices sont bloquées.

> ⚠️ Ce bac à sable logiciel ne remplace pas une isolation conteneur : pour un
> déploiement public, exécuter les commandes dans un conteneur jetable (rootless,
> réseau coupé, quota CPU/mémoire).

## Notes de maintenance

- `backend/main.py.bak`, `backend/init_db*.py`, `backend/setup_db.py`,
  `backend/fix_challenges.py`, `reinit_db.py`, `reinit_db2.py` sont des scripts
  historiques : le schéma et les données de départ sont désormais gérés par
  `init_db()` dans `backend/main.py`.
- `backend/database/init.sql` décrit un schéma plus ancien (colonne `validation_type`)
  que celui réellement utilisé (`validation`). À réaligner ou à supprimer.
