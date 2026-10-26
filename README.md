# SHELLFORGE

Parcours d'apprentissage **offensif et défensif**, du premier `ls` au rapport de pentest :
chaque mission associe un **cours**, un **laboratoire équipé** et des **preuves vérifiées
automatiquement** par le serveur. On apprend une notion, on l'applique immédiatement, on
prouve qu'elle est maîtrisée, puis on monte d'un cran.

```
Fondations → Fiabilité → Administration Linux → Reconnaissance → Pentest → Ingénierie
```

**30 missions · 15 modules · 6 niveaux · 9 580 XP**

| Niveau | Contenu | Missions |
|---|---|---|
| 1 · Fondations | arborescence, permissions/SUID, grep sur logs, sed/awk, scripts et codes de sortie | 6 |
| 2 · Ingénierie de la fiabilité | sauvegarde vérifiable, idempotence + cron, diagnostic de saturation, systemd durci | 4 |
| 3 · Administration Linux | comptes/sudo/SSH, audit des privilèges, SUID/umask, chiffrement au repos, exposition réseau, pare-feu nftables | 6 |
| 4 · Reconnaissance | OSINT DNS, fuites applicatives, corrélation de scan, énumération de services | 4 |
| 5 · Pentest | injection SQL, XSS/CSRF, secrets et JWT, élévation de privilèges, post-exploitation, rapport + re-test | 6 |
| 6 · Ingénierie de production | IaC + CI sécurité, SLO/observabilité/postmortem, audit final de bout en bout | 4 |

## Comment fonctionne une mission

1. **Cours** — sections courtes (marquables comme lues), références de commandes, pièges,
   et une note « vision défensive » pour chaque technique offensive.
2. **Laboratoire** — un espace de travail isolé par session et par mission, prérempli de
   fichiers réalistes (journaux, configurations, code vulnérable, scans, snapshots proc).
   On y écrit des scripts avec une console intégrée.
3. **Preuves** — le bouton « Vérifier mes preuves » exécute côté serveur une série de
   contrôles (`file_exists`, `file_contains`, `file_mode`, `run`) et renvoie le détail
   passé/échoué. Les points ne sont attribués qu'une fois, à la première validation.
4. **Déblocage** — un niveau s'ouvre quand 70 % du précédent est validé. La mission suivante
   est proposée automatiquement après chaque succès.

Les laboratoires sont **réinitialisables** : le bouton « réinitialiser l'espace » restaure
l'état de départ (fichiers, dossiers et permissions d'origine).

## Architecture

```
backend/
  main.py                 API FastAPI (sessions, progression, laboratoires, vérification)
  curriculum.py           chargement + validation + sérialisation du contenu
  curriculum/level-*.json contenu pédagogique (6 fichiers, 30 missions)
frontend/shellforge-app/  React 19 + Vite (parcours, mission, console, progression)
scripts/selfcheck_curriculum.py  auto-contrôle : joue chaque solution et vérifie les preuves
tests/test_api_smoke.py   tests de l'API et du moteur de laboratoire
```

### Ajouter une mission

1. Ajouter un objet mission dans le module concerné (`backend/curriculum/level-*.json`).
2. Fournir `lesson` (sections, références, pièges), `lab` (`files`, `dirs`, `modes`,
   `task`, `steps`, `hints`, `checks`, `solution`) et `remediation`.
3. Lancer `python3 scripts/selfcheck_curriculum.py <mission-id>` : la solution de référence
   doit valider tous les contrôles, sinon le curriculum est refusé au démarrage.

### API principale

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/levels?session_id=` | niveaux, progression, verrouillage |
| GET | `/api/modules?session_id=` | modules + missions + état |
| GET | `/api/modules/{id}` | détail d'un module |
| GET | `/api/missions/{id}?session_id=` | cours, consignes, indices, contrôles |
| POST | `/api/missions/{id}/verify` | exécute les contrôles de preuves |
| POST | `/api/learning/progress` | marque une section comme lue |
| POST | `/api/sessions` | crée une session d'apprentissage |
| GET | `/api/sessions/{id}/summary` | XP, niveau, progression par niveau/module |
| GET/POST | `/api/labs/files`, `/api/labs/run`, `/api/labs/reset` | espace de travail et console |
| GET | `/api/health` | sonde de disponibilité |

Documentation interactive : `http://localhost:8000/docs`.

## Démarrage

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (autre terminal)
cd frontend/shellforge-app
npm install
npm run dev          # http://localhost:5173
```

Le front appelle des URL relatives (`/api/...`) : Vite les proxifie vers
`http://127.0.0.1:8000`. Aucun problème de CORS, y compris derrière un proxy de
prévisualisation. Pour appeler un backend distant, définir `VITE_API_URL`.

### Tests

```bash
source .venv/bin/activate
pytest -q                                    # API + laboratoire (8 tests)
python3 scripts/selfcheck_curriculum.py      # les 30 missions, solutions comprises
```

## Isolation des laboratoires

Chaque commande s'exécute dans `$TMPDIR/shellforge-labs/<session>/<mission>` avec :

- validation stricte des segments de chemin (`[A-Za-z0-9_-]`) et refus des `..` ;
- refus des liens symboliques sortant de l'espace de travail ;
- `HOME` redirigé vers le laboratoire, timeout de 20 s, sorties tronquées ;
- liste noire des commandes destructrices (`rm -rf /`, `mkfs`, `dd if=/dev/zero`…).

> ⚠️ **Limite assumée** : c'est un bac à sable *logiciel*, pas une isolation conteneur.
> Pour un déploiement public, exécuter chaque commande dans un conteneur jetable
> (rootless, réseau coupé, quotas CPU/mémoire, système de fichiers en lecture seule).

## Configuration

| Variable | Défaut | Description |
|---|---|---|
| `SHELLFORGE_DB_PATH` | `./database/shellforge.db` | base SQLite |
| `SHELLFORGE_LAB_ROOT` | `$TMPDIR/shellforge-labs` | racine des laboratoires |
| `SHELLFORGE_LAB_TIMEOUT` | `20` | délai max d'une commande (s) |
| `CORS_ALLOWED_ORIGINS` | localhost:5173-5175 | origines explicites |
| `CORS_ALLOWED_ORIGIN_REGEX` | localhost + `*.e2b.app` | origines par regex (prévisualisation) |
| `VITE_API_URL` | *(vide)* | base d'URL de l'API côté front |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | cible du proxy Vite |

## Éthique et périmètre

Les techniques offensives (injection, XSS, élévation de privilèges, post-exploitation) sont
pratiquées **uniquement sur des artefacts fictifs fournis dans les laboratoires**. Chaque
mission rappelle le cadre : autorisation écrite, périmètre explicite, minimisation des
données, aucune exfiltration. Les missions de reconnaissance insistent sur la distinction
entre information publique et exploitation.
