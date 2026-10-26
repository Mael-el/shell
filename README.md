# SHELLFORGE

Parcours d'apprentissage **offensif et défensif**, du premier `ls` au rapport de pentest :
chaque mission associe un **cours**, un **laboratoire équipé** et des **preuves vérifiées
automatiquement** par le serveur. On apprend une notion, on l'applique immédiatement, on
prouve qu'elle est maîtrisée, puis on monte d'un cran.

```
Fondations → Fiabilité → Administration Linux → Reconnaissance → Pentest → Ingénierie → Applications
```

**36 missions · 18 modules · 7 niveaux · 12 130 XP**

| Niveau | Contenu | Missions |
|---|---|---|
| 1 · Fondations | arborescence, permissions/SUID, grep sur logs, sed/awk, scripts et codes de sortie | 6 |
| 2 · Ingénierie de la fiabilité | sauvegarde vérifiable, idempotence + cron, diagnostic de saturation, systemd durci | 4 |
| 3 · Administration Linux | comptes/sudo/SSH, audit des privilèges, SUID/umask, chiffrement au repos, exposition réseau, pare-feu nftables | 6 |
| 4 · Reconnaissance | OSINT DNS, fuites applicatives, corrélation de scan, énumération de services | 4 |
| 5 · Pentest | injection SQL, XSS/CSRF, secrets et JWT, élévation de privilèges, post-exploitation, rapport + re-test | 6 |
| 6 · Ingénierie de production | IaC + CI sécurité, SLO/observabilité/postmortem, audit final de bout en bout | 4 |
| 7 · Applications | sur une même application (FactuAPI) : cartographie de la surface, IDOR, injection de commandes, téléversements, en-têtes/CSP, passerelle de sécurité en CI | 6 |

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

Le niveau 7 pousse la pratique plus loin : chaque mission livre un morceau d'application
réel (Python), une **suite de tests qui échoue**, et demande de corriger le code jusqu'au
vert — puis de documenter l'impact. `python3 run_tests.py` joue la suite comme la CI, et
les contrôles vérifient à la fois le code, les tests (toujours présents) et le rapport.

Les laboratoires sont **réinitialisables** : le bouton « réinitialiser l'espace » restaure
l'état de départ (fichiers, dossiers et permissions d'origine).

## CyberDev Dojo — le plan de 12 semaines

SHELLFORGE ne remplace pas les plateformes externes : il les **orchestre**. La page
`/dojo` tient le plan d'entraînement, avec 6 niveaux, 24 tâches vérifiables et 1 610 XP :

| Niveaux | Semaines | Contenu |
|---|---|---|
| 1 · Fondations | 1–2 | Bandit, 15 exercices Bash, 10 exercices Python, IP/DNS/HTTP/TCP |
| 2 · Programmation | 3–4 | 3 scripts utiles, SQL Murder Mystery, Git, outil CLI |
| 3 · Cybersécurité | 5–6 | parcours TryHackMe, 10 challenges picoCTF, Wireshark/Nmap, 2 rapports |
| 4 · Web | 7–8 | petite API, Juice Shop local, 5 labs PortSwigger, corrections |
| 5 · Blue Team | 9–10 | journaux Linux, 3 enquêtes CyberDefenders, analyseur Python, Docker |
| 6 · Projet final | 11–12 | laboratoire perso, outil documenté, CTF débutant, portfolio GitHub |

Chaque tâche est cochable : l'XP n'est attribué qu'une fois, les badges (un par niveau, plus
mi-parcours et dojo accompli) se débloquent automatiquement, et un catalogue de
**38 ressources** (laboratoires, programmation, auto-hébergement, jeux) est accessible depuis
la même page. Un bandeau sur l'accueil rappelle l'avancement.

La page rappelle aussi la méthode de travail en cinq temps (comprendre, chercher, consulter,
terminer, refaire sans aide) : l'IA sert de mentor, pas de solution immédiate. Aucune
plateforme externe n'est automatisée — c'est l'apprenant qui coche, l'app calcule.

### Des données réelles, pas des étiquettes inventées

Chaque ressource porte son **accès** (gratuit / freemium / payant), son **fournisseur** et,
quand elle est payante, son **prix vérifié**. Pour les dépôts GitHub, l'API est interrogée
directement : étoiles, licence, dernière mise à jour, archivage.

```bash
python3 scripts/check_resources.py              # rafraîchit + teste la joignabilité
python3 scripts/check_resources.py --only-github  # sans test HTTP (réseau restreint)
```

Le résultat est écrit dans `backend/curriculum/resources-verified.json` et affiché dans
l'interface avec la date de vérification. Le script distingue honnêtement trois états :
métadonnées GitHub récupérées, URL joignable, ou **non vérifiée** quand l'environnement n'a
pas de sortie réseau — jamais « valide » par défaut.

L'XP du dojo est réelle elle aussi : elle s'ajoute au score de la session et au niveau
(`xp_missions`, `xp_dojo` et `score` sont exposés séparément par l'API).

## Architecture

```
backend/
  main.py                 API FastAPI (sessions, progression, laboratoires, vérification)
  curriculum.py           chargement + validation + sérialisation du contenu
  roadmap.py              plan d'entraînement 12 semaines (6 niveaux, 24 tâches)
  curriculum/level-*.json contenu pédagogique (7 fichiers, 36 missions)
  curriculum/roadmap-12-semaines.json  plan du dojo + catalogue de ressources
  curriculum/resources-verified.json   métadonnées vérifiées (étoiles, licence, dates)
frontend/shellforge-app/  React 19 + Vite (parcours, mission, console, progression)
  src/index.css           jetons de design (palette terminal, typographie mono)
  src/App.css             composants : panneaux, console, vérification, badges
scripts/selfcheck_curriculum.py  auto-contrôle : joue chaque solution et vérifie les preuves
scripts/check_resources.py       rafraîchit les métadonnées réelles des ressources (GitHub API)
scripts/dev.sh            démarre backend + frontend en une commande
tests/test_api_smoke.py   tests de l'API et du moteur de laboratoire
frontend/shellforge-app/tests/ui-smoke.mjs  fumée UI (jsdom, 5 écrans, contre l'API réelle)
.github/workflows/ci.yml  CI : pytest, selfcheck 36/36, lint, build, fumée UI
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
| GET | `/api/sessions/{id}` | valide une session (404 si la base a été réinitialisée) |
| GET | `/api/sessions/{id}/summary` | XP, niveau, progression par niveau/module |
| GET | `/api/sessions/{id}/progress`, `/stats` | progression détaillée, statistiques |
| GET/POST | `/api/labs/files`, `/api/labs/run`, `/api/labs/reset` | espace de travail et console |
| GET | `/api/roadmap?session_id=` | plan 12 semaines, avancement, badges |
| POST | `/api/roadmap/progress` | coche/décoche une tâche du dojo (XP une seule fois) |
| GET | `/api/resources` | catalogue de ressources externes |
| GET | `/api/health` | sonde de disponibilité |

Documentation interactive : `http://localhost:8000/docs`.

Le front mémorise l'identifiant de session dans `localStorage`, mais le revalide au
chargement (`GET /api/sessions/{id}`) : si la base a été réinitialisée, la session est
oubliée et une nouvelle est créée automatiquement. Si l'API est injoignable, un message
explicite s'affiche au lieu d'une page blanche.

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

ou, plus simple, les deux d'un coup :

```bash
./scripts/dev.sh     # API :8000 + Vite :5173, Ctrl-C pour tout arrêter
```

Le front appelle des URL relatives (`/api/...`) : Vite les proxifie vers
`http://127.0.0.1:8000`. Aucun problème de CORS, y compris derrière un proxy de
prévisualisation. Pour appeler un backend distant, définir `VITE_API_URL`.

### Tests

```bash
source .venv/bin/activate
pytest -q                                    # API + laboratoire + dojo (14 tests)
python3 scripts/selfcheck_curriculum.py      # les 36 missions, solutions comprises
cd frontend/shellforge-app
npm run lint                                 # oxlint
npm run build                                # build de production
npm run test:ui                              # fumée UI (API requise sur :8000)
```

`npm run test:ui` monte la vraie application React dans jsdom via le serveur Vite, visite
`/`, `/niveau/1`, `/niveau/7`, `/module/m01`, `/mission/m01-01` (cours, laboratoire,
fichiers) et `/progression`, et échoue sur toute erreur console. Un scénario dédié vérifie aussi qu'une
session devenue invalide (base réinitialisée) est remplacée sans écran d'erreur.
La CI GitHub Actions (`.github/workflows/ci.yml`) rejoue ces vérifications à chaque push
sur `main` et sur chaque pull request.

## Isolation des laboratoires

Chaque commande s'exécute dans `$TMPDIR/shellforge-labs/<session>/<mission>` : chaque
session (et donc chaque apprenant) dispose de son propre répertoire, jamais partagé avec
les autres, avec :

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
