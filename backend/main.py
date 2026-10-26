#!/usr/bin/env python3
"""SHELLFORGE Backend - FastAPI Application for Bash Learning Platform"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


for env_path in (BASE_DIR / '.env', BASE_DIR / 'backend' / '.env'):
    _load_env_file(env_path)

DATABASE_DIR = Path(os.getenv('SHELLFORGE_DB_DIR', str(BASE_DIR / 'database'))).expanduser()
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv('SHELLFORGE_DB_PATH', str(DATABASE_DIR / 'shellforge.db'))).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = (BASE_DIR / DB_PATH).resolve()


def _parse_origins(raw: str):
    if not raw:
        return []
    parts = [item.strip() for item in raw.split(',') if item.strip()]
    return [item for item in parts if item]


DEFAULT_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'http://localhost:5175',
    'http://127.0.0.1:5175',
]
ALLOWED_ORIGINS = _parse_origins(os.getenv('CORS_ALLOWED_ORIGINS', ','.join(DEFAULT_ALLOWED_ORIGINS))) or DEFAULT_ALLOWED_ORIGINS

app = FastAPI(
    title="SHELLFORGE API",
    description="Plateforme d'apprentissage interactive de Bash/Linux",
    version="1.0.0"
)

# CORS pour accès local
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def exec_sql(conn, sql, params=None):
    """Execute SQL with optional parameters, commit and return cursor."""
    c = conn.cursor()
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    conn.commit()
    return c


def get_db():
    """Obtenir une connexion à la base de données (nouvelle connexion par requête)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@app.on_event("startup")
def init_db():
    """Initialiser la base de données sans réinitialiser les données existantes."""
    conn = get_db()

    exec_sql(conn, """CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT DEFAULT 'active',
        score INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1
    )""")

    exec_sql(conn, """CREATE TABLE IF NOT EXISTS modules (
        id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        level INTEGER,
        category TEXT,
        xp_reward INTEGER,
        difficulty TEXT DEFAULT 'medium',
        active BOOLEAN DEFAULT TRUE
    )""")

    exec_sql(conn, """CREATE TABLE IF NOT EXISTS challenges (
        id TEXT PRIMARY KEY,
        module_id TEXT,
        title TEXT,
        description TEXT,
        command TEXT,
        expected_output TEXT,
        validation TEXT,
        points INTEGER DEFAULT 100,
        difficulty TEXT DEFAULT 'medium',
        hint TEXT,
        theory TEXT
    )""")

    challenge_columns = conn.execute("PRAGMA table_info(challenges)").fetchall()
    existing_columns = {column[1] for column in challenge_columns}
    for column_name, column_type in [("hint", "TEXT"), ("theory", "TEXT")]:
        if column_name not in existing_columns:
            exec_sql(conn, f"ALTER TABLE challenges ADD COLUMN {column_name} {column_type}")

    exec_sql(conn, """CREATE TABLE IF NOT EXISTS progress (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        challenge_id TEXT,
        attempted BOOLEAN DEFAULT FALSE,
        correct BOOLEAN DEFAULT FALSE,
        attempts INTEGER DEFAULT 0,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )""")

    exec_sql(conn, """CREATE TABLE IF NOT EXISTS lesson_progress (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        challenge_id TEXT,
        lesson_id TEXT,
        status TEXT DEFAULT 'not_started',
        score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    exec_sql(conn, """CREATE TABLE IF NOT EXISTS mission_progress (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        challenge_id TEXT,
        stage TEXT DEFAULT 'in_progress',
        completed_lessons INTEGER DEFAULT 0,
        progress_percent INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    default_modules = [
        ("m01", "Introduction au Shell", "Premiers pas dans Bash", 1, "basics", 100, "easy", True),
        ("m02", "Variables et Arguments", "Gérer les variables et les paramètres", 1, "basics", 150, "easy", True),
        ("m03", "Conditions et Logique", "Structures if/then/else et tests", 1, "basics", 200, "medium", True),
        ("m04", "Boucles", "Boucles for, while et until", 1, "basics", 200, "medium", True),
        ("m05", "Redirections", "Manipuler stdout, stderr et pipes", 2, "intermediate", 250, "medium", True),
        ("m06", "Fonctions", "Créer et utiliser des fonctions Bash", 2, "intermediate", 300, "hard", True),
        ("m07", "Expressions Régulières", "Utiliser grep et sed avec regex", 3, "advanced", 350, "hard", True),
        ("m08", "Permissions et Utilisateurs", "Manipuler chmod, chown et les droits Unix", 3, "linux-admin", 400, "medium", True),
        ("m09", "Réseaux Linux", "Vérifier les services, les ports et la résolution DNS", 3, "network", 450, "hard", True),
        ("m10", "Automatisation et Sauvegarde", "Planifier des tâches et sécuriser les archives", 4, "automation", 500, "hard", True),
    ]

    for module in default_modules:
        exec_sql(conn,
            "INSERT OR IGNORE INTO modules (id, title, description, level, category, xp_reward, difficulty, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            module)

    default_challenges = [
        ("c01", "m01", "Premier script Bash", "Créer votre premier script Bash", "./hello.sh \"World\"", "Bonjour World!", "contains", 100, "easy", "Créez un script Bash qui affiche un texte simple, puis exécutez-le avec un argument.", "Les scripts Bash lisent les instructions de haut en bas et peuvent afficher du texte avec echo."),
        ("c02", "m01", "Afficher l'aide", "Voir l'aide de la commande ls", "help ls", "Usage: ls", "contains", 100, "easy", "Utilisez la commande de secours pour afficher l’aide intégrée de ls.", "La plupart des commandes GNU disposent d’un mode d’aide pour expliquer leurs options."),
        ("c03", "m01", "Chemin absolu vs relatif", "Déterminer le type de chemin", "./paths.sh /home", "/home", "contains", 100, "easy", "Le script doit afficher le chemin d’entrée tel quel, sans le transformer.", "Un chemin absolu part de la racine et commence par /. Un chemin relatif dépend du dossier courant."),
        ("c04", "m02", "Utiliser des variables", "Utiliser une variable d'argument", "./vars.sh arg1", "La valeur est: arg1", "exact", 150, "easy", "Passez un paramètre au script puis affichez-le dans une variable.", "Les arguments passés à un script sont accessibles via $1, $2, …"),
        ("c05", "m02", "Définir une variable", "Définir et afficher une variable", "./varassign.sh", "Hello", "exact", 150, "easy", "Déclarez une variable et affichez sa valeur sans apostrophes.", "Une variable Bash se déclare avec NOM=valeur et s’affiche avec $NOM."),
        ("c06", "m02", "Longueur de chaîne", "Mesurer la longueur d'une chaîne", "./length.sh Bonjour", "7", "exact", 150, "easy", "Utilisez la variable du premier argument et calculez sa longueur.", "Le symbole ${#var} donne la longueur d’une chaîne en Bash."),
        ("c07", "m03", "Tester si un fichier existe", "Vérifier l'existence d'un fichier", "./check.sh /etc/hosts", "/etc/hosts existe", "exact", 200, "medium", "Testez la présence du fichier avant de l’afficher.", "Le test [ -e fichier ] permet de vérifier si un fichier existe."),
        ("c08", "m03", "Comparaison de nombres", "Comparer deux nombres", "./compare.sh 10 5", "10 est plus grand que 5", "exact", 200, "medium", "Comparez les deux valeurs numériques et affichez le bon message.", "Bash utilise -gt pour comparer si un nombre est supérieur à un autre."),
        ("c09", "m03", "Condition utilisateur", "Condition de bienvenue", "./welcome.sh", "Bonjour [nom]", "exact", 200, "medium", "Le script doit saluer l’utilisateur en fonction d’une condition simple.", "Les conditions if/then/else permettent de choisir une branche selon une condition logique."),
        ("c10", "m04", "Boucle for nombres", "Afficher une boucle for", "./forloop.sh", "1\n2\n3\n4\n5", "exact", 200, "medium", "Générez une boucle qui itère sur une liste de nombres.", "for i in 1 2 3; do ...; done permet de répéter une action plusieurs fois."),
        ("c11", "m04", "Boucle while compteur", "Compter avec while", "./whileloop.sh", "0\n1\n2\n3", "exact", 200, "medium", "Créez un compteur et augmentez-le à chaque tour de boucle.", "while [ $compteur -lt 4 ]; do ...; done répète tant qu’une condition est vraie."),
        ("c12", "m04", "Boucle until", "S'arrêter avec until", "./untilloop.sh", "Compteur: 5", "exact", 200, "medium", "Utilisez until pour continuer jusqu’à ce que la condition soit vraie.", "until [ $compteur -ge 5 ]; do ... ; done s’arrête quand la condition devient vraie."),
        ("c13", "m05", "Rediriger stdout vers fichier", "Rediriger la sortie standard vers un fichier", "./redirect_std.sh > output.log", "[CONTENU]", "contains", 250, "medium", "Enregistrez la sortie dans un fichier avec le symbole >.", "> redirige la sortie standard vers un fichier, écrasant son contenu s’il existe."),
        ("c14", "m05", "Append dans un fichier", "Append dans un fichier de errors", "./append.sh >> errors.log", "[ERREUR]", "contains", 250, "medium", "Ajoutez du texte sans écraser le contenu existant.", " >> ajoute à la fin d’un fichier au lieu de le remplacer."),
        ("c15", "m05", "Pipes basiques", "Utiliser un pipe entre commandes", "cat test.txt | wc -l", "3", "contains", 250, "medium", "Comptez les lignes produites par un fichier grâce à un pipe.", "| envoie la sortie d’une commande dans l’entrée d’une autre."),
        ("c16", "m06", "Fonction addition", "Créer une fonction d'addition", "./func_add.sh", "add 3 4", "exact", 300, "hard", "Déclarez une fonction qui prend deux paramètres et retourne le calcul.", "Les fonctions Bash regroupent des instructions réutilisables et peuvent accepter des arguments."),
        ("c17", "m06", "Fonction avec paramètres", "Fonction avec paramètres", "./func_len.sh test", "4", "exact", 300, "hard", "Calculez la taille d’une chaîne reçue en argument dans une fonction.", "Au sein d’une fonction, $1 représente le premier argument fourni à l’appel."),
        ("c18", "m06", "Fonction retour", "Fonction avec résultat de retour", "./func_ret.sh", "Resultat: 7", "exact", 300, "hard", "Retournez un calcul depuis la fonction et affichez-le ensuite.", "echo ou return peuvent être utilisés selon le besoin; le message final vient de l’appel de la fonction."),
        ("c19", "m07", "Recherche grep basique", "Rechercher avec grep", "grep -r ERROR /var/log/", "ligne(s) trouvées", "contains", 350, "hard", "Cherchez des lignes contenant un mot-clé dans un dossier.", "grep permet de filtrer les lignes correspondantes à un motif, récursivement ou non."),
        ("c20", "m07", "Remplacer avec sed", "Remplacer des texte avec sed", "sed -i 's/old/new/g' text.txt", "Remplacement effectué", "contains", 350, "hard", "Remplacez un mot dans un fichier sans le modifier manuellement.", "sed -i permet d’éditer un fichier en place en utilisant des expressions de substitution."),
        ("c21", "m07", "Pattern complexe grep", "Pattern grep avancé avec extended regex", "grep -E user@domain emails.txt", "trouvé@domaine", "contains", 350, "hard", "Utilisez un motif régulier pour repérer un email valide dans une liste.", "grep -E utilise les expressions régulières étendues pour cibler plusieurs motifs."),
        ("c22", "m08", "Permissions basics", "Afficher les droits du fichier passwd", "ls -l /etc/passwd", "root", "contains", 400, "medium", "Le fichier passwd est souvent détenu par root et lisible par les autres utilisateurs.", "Les permissions Unix se lisent en trois groupes: propriétaire, groupe et autres."),
        ("c23", "m08", "Chown pratique", "Changer le propriétaire d’un fichier", "chown nobody /tmp/demo.txt", "nobody", "contains", 400, "medium", "Utilisez chown pour transferer la propriété d’un fichier à un autre utilisateur.", "chown change le propriétaire d’un fichier et peut aussi modifier le groupe associé."),
        ("c24", "m08", "Mode binaire", "Vérifier le mode de permissions d'un script", "stat -c '%a %n' script.sh", "755 script.sh", "contains", 400, "medium", "Le mode octal 755 donne lecture, écriture et exécution aux propriétaires.", "Le mode octal résume les droits dans un format compact et lisible par machine."),
        ("c25", "m09", "Test de port", "Vérifier si un port écoute", "ss -lnt | grep 22", "LISTEN", "contains", 450, "hard", "Le port 22 est souvent utilisé par SSH et doit apparaître dans les sockets en écoute.", "ss affiche les sockets TCP/UDP et permet de vérifier les ports ouverts localement."),
        ("c26", "m09", "DNS lookup", "Résoudre un nom de domaine", "getent hosts example.com", "93.184.216.34", "contains", 450, "hard", "Utilisez un outil de résolution de noms pour obtenir l’adresse IP associée.", "DNS convertit un nom de domaine en adresse IP afin de localiser un service sur le réseau."),
        ("c27", "m09", "Connexion HTTP", "Vérifier un endpoint local", "curl -I http://localhost", "HTTP/1.1", "contains", 450, "hard", "La commande curl permet de récupérer les en-têtes HTTP d’un service web.", "curl -I ne télécharge pas le corps de réponse, seulement les métadonnées de la requête."),
        ("c28", "m10", "Script de sauvegarde", "Créer une archive compressée", "tar -czf backup.tar.gz /etc", "backup.tar.gz", "contains", 500, "hard", "Créer une archive compressée d’un dossier pour une sauvegarde simple.", "tar archive un dossier et gzip la compresse pour limiter la taille du fichier."),
        ("c29", "m10", "Planification cron", "Afficher la crontab utilisateur", "crontab -l", "0 2 * * *", "contains", 500, "hard", "Les tâches planifiées sont listées dans la crontab de l’utilisateur.", "cron exécute automatiquement des tâches selon un calendrier défini par le système."),
        ("c30", "m10", "Surveillance de processus", "Lister les processus actifs", "ps aux | grep bash", "bash", "contains", 500, "hard", "ps aux permet de repérer les processus actifs sur le système.", "Les processus sont les programmes réellement en cours d’exécution par le noyau."),
    ]

    for index, challenge in enumerate(default_challenges):
        assert len(challenge) == 11, f"Challenge {challenge[0]} has {len(challenge)} values, expected 11 (index {index})"
        exec_sql(conn,
            "INSERT OR IGNORE INTO challenges (id, module_id, title, description, command, expected_output, validation, points, difficulty, hint, theory) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            challenge)
        exec_sql(conn,
            "UPDATE challenges SET hint = COALESCE(hint, ?), theory = COALESCE(theory, ?) WHERE id = ?",
            (challenge[9], challenge[10], challenge[0]))

    exec_sql(conn, "INSERT OR IGNORE INTO sessions (id, user_id) VALUES (?, ?)", ("session-001", "shellforge-user"))
    conn.close()


# --- Modèles Pydantic ---

class SessionCreate(BaseModel):
    user_id: str


class ChallengeSubmission(BaseModel):
    session_id: str
    challenge_id: str
    output: str
    command: str | None = None


class LabRunRequest(BaseModel):
    session_id: str
    command: str
    working_dir: str | None = None


class LabResetRequest(BaseModel):
    session_id: str
    working_dir: str | None = None


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


LAB_FIXTURES = {
    "c01": {
        "scripts/hello.sh": "#!/usr/bin/env bash\necho \"Bonjour ${1:-Shellforge}\"\n",
        "data/messages.txt": "Bonjour\nBienvenue dans le laboratoire Shellforge\n",
    },
    "c02": {
        "data/ls-help.txt": "Usage: ls [OPTION]... [FILE]...\n-l  use a long listing format\n-a  do not ignore entries starting with .\n",
    },
    "c03": {
        "data/paths.txt": "./scripts/hello.sh\n../shared/notes.txt\n/home/student\n",
    },
    "c04": {
        "data/arguments.txt": "alpha\nbeta\ngamma\n",
        "scripts/args.sh": "#!/usr/bin/env bash\nvalue=\"$1\"\necho \"La valeur est: $value\"\n",
    },
    "c05": {
        "data/greeting.txt": "Hello\n",
    },
    "c06": {
        "data/words.txt": "Bonjour\nShellforge\npermissions\n",
    },
    "c07": {
        "data/targets.txt": "data/app.conf\ndata/greeting.txt\nmissing.txt\n",
        "data/app.conf": "APP_NAME=Shellforge\nAPP_ENV=training\n",
    },
    "c08": {
        "data/numbers.csv": "first,second\n10,5\n3,8\n",
    },
    "c09": {
        "data/users.csv": "name,role\nAlice,admin\nKarim,student\nMina,student\n",
    },
    "c10": {
        "data/numbers.txt": "1\n2\n3\n4\n5\n",
    },
    "c11": {
        "data/counter.txt": "start=0\nlimit=4\n",
    },
    "c12": {
        "data/targets.txt": "3\n4\n5\n",
    },
    "c13": {
        "data/report-source.txt": "Rapport de formation Shellforge\nExercices terminés: 3\n",
    },
    "c14": {
        "logs/errors.log": "WARN configuration par défaut\nERROR connexion interrompue\n",
    },
    "c15": {
        "data/test.txt": "alpha\nbeta\ngamma\n",
        "logs/events.log": "INFO démarrage\nWARN attente\nINFO prêt\n",
    },
    "c16": {
        "data/operations.csv": "left,right\n3,4\n10,5\n",
    },
    "c17": {
        "data/words.txt": "test\nShellforge\nautomation\n",
    },
    "c18": {
        "data/expected-results.txt": "addition=7\n",
    },
    "c19": {
        "logs/app.log": "INFO service démarré\nERROR fichier introuvable\nWARN nouvelle tentative\nERROR délai dépassé\n",
    },
    "c20": {
        "data/text.txt": "old status\nold value\nkeep this line\n",
    },
    "c21": {
        "data/emails.txt": "alice@example.com\ninvalid-address\nsupport@shellforge.test\n",
    },
    "c22": {
        "permissions/passwd.sample": "root:x:0:0:root:/root:/bin/bash\nstudent:x:1000:1000:Student:/home/student:/bin/bash\n",
        "permissions/report.txt": "Fichier de démonstration des permissions\n",
    },
    "c23": {
        "permissions/demo.txt": "Fichier local pour pratiquer les propriétaires et groupes.\n",
    },
    "c24": {
        "permissions/script.sh": "#!/usr/bin/env bash\necho 'Script de démonstration'\n",
    },
    "c25": {
        "data/services.txt": "ssh 22/tcp LISTEN\nhttp 80/tcp CLOSED\ntraining 8080/tcp LISTEN\n",
    },
    "c26": {
        "data/hosts.txt": "192.0.2.10 training.example.test\n192.0.2.11 docs.example.test\n",
    },
    "c27": {
        "data/response-headers.txt": "HTTP/1.1 200 OK\nContent-Type: text/plain\nX-Training: shellforge\n",
    },
    "c28": {
        "backup/source/config.ini": "[app]\nname=Shellforge\nmode=training\n",
        "backup/source/notes.txt": "Données d'exemple à archiver.\n",
    },
    "c29": {
        "data/crontab.sample": "0 2 * * * /home/student/backup.sh\n*/15 * * * * /home/student/healthcheck.sh\n",
    },
    "c30": {
        "data/processes.sample": "PID USER COMMAND\n101 student bash\n202 student python training.py\n",
    },
}


def validate_lab_segment(value: str, field_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise HTTPException(status_code=400, detail=f"{field_name} invalide")
    return value


def seed_lab_workspace(target: Path, challenge_id: str | None = None) -> None:
    """Create useful starter directories/files without overwriting learner work."""
    target.mkdir(parents=True, exist_ok=True)
    workspace_root = target.resolve()
    common_files = {
        "README.txt": (
            "SHELLFORGE - laboratoire local\n"
            "Les fichiers de data/, logs/, permissions/ et backup/ sont des exemples d'exercice.\n"
            "Tu peux les explorer et les modifier depuis le terminal.\n"
        ),
        "data/notes.txt": "Bienvenue dans ton espace de travail Shellforge.\n",
        "logs/training.log": "INFO laboratoire prêt\nWARN exemple de journal\n",
        "scripts/solution.sh": "#!/usr/bin/env bash\n# Écris ta solution ici.\n",
    }
    starter_files = {**common_files, **LAB_FIXTURES.get(challenge_id or "", {})}
    for relative_path, content in starter_files.items():
        file_path = workspace_root
        safe_parent = True
        for part in Path(relative_path).parts[:-1]:
            file_path = file_path / part
            if file_path.is_symlink():
                safe_parent = False
                break
            file_path.mkdir(exist_ok=True)
            if not file_path.is_dir():
                safe_parent = False
                break
        if not safe_parent:
            continue
        file_path = file_path / Path(relative_path).name
        if not file_path.is_symlink() and not file_path.exists():
            file_path.write_text(content, encoding="utf-8")


def build_lab_dir(session_id: str, working_dir: str | None = None) -> str:
    validate_lab_segment(session_id, "session_id")
    root = (Path(tempfile.gettempdir()) / "shellforge-labs").resolve()
    root.mkdir(parents=True, exist_ok=True)
    session_dir = root / session_id
    if session_dir.is_symlink():
        raise HTTPException(status_code=400, detail="Répertoire de session invalide")
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir = session_dir.resolve()
    if not session_dir.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Répertoire de session invalide")
    if working_dir:
        validate_lab_segment(working_dir, "working_dir")
        target = session_dir / working_dir
        if target.is_symlink():
            raise HTTPException(status_code=400, detail="Répertoire de mission invalide")
        seed_lab_workspace(target, working_dir)
        resolved_target = target.resolve()
        if not resolved_target.is_relative_to(session_dir):
            raise HTTPException(status_code=400, detail="Répertoire de mission invalide")
        return str(resolved_target)
    seed_lab_workspace(session_dir)
    return str(session_dir)


def serialize_challenge(challenge_row, include_expected_output: bool = False):
    data = dict(challenge_row)
    if not include_expected_output:
        data.pop("expected_output", None)
    return data


def calculate_level_from_xp(xp_points: int) -> int:
    """Calcule un niveau simple à partir de l'XP accumulé."""
    if xp_points <= 0:
        return 1
    return 1 + (xp_points // 250)


def build_learning_progress_state(session_id: str, challenge_id: str, learning_engine: dict):
    """Calcule l'état de progression pédagogique d'une mission pour une session."""
    sections = learning_engine.get("sections", []) or []
    lesson_ids = [section.get("id") for section in sections if section.get("id")]
    if not lesson_ids:
        return {
            "total_sections": 0,
            "completed_sections": 0,
            "progress_percent": 0,
            "sections": [],
        }

    conn = get_db()
    rows = conn.execute(
        "SELECT lesson_id, status FROM lesson_progress WHERE session_id = ? AND challenge_id = ?",
        (session_id, challenge_id),
    ).fetchall()
    lesson_status = {row["lesson_id"]: row["status"] for row in rows}

    completed_sections = 0
    section_states = []
    for section in sections:
        lesson_id = section.get("id")
        status = lesson_status.get(lesson_id, "not_started")
        if status == "completed":
            completed_sections += 1
        section_states.append({
            "id": lesson_id,
            "name": section.get("name", lesson_id),
            "status": status,
        })

    progress_percent = round((completed_sections / len(sections)) * 100) if sections else 0
    return {
        "total_sections": len(sections),
        "completed_sections": completed_sections,
        "progress_percent": progress_percent,
        "sections": section_states,
    }


class LearningProgressRequest(BaseModel):
    session_id: str
    challenge_id: str
    lesson_id: str
    status: str = "completed"


def build_learning_engine(challenge_id: str):
    """Retourne le moteur d'apprentissage associé à une mission."""
    base_engine = {
        "title": "Apprendre en pratiquant",
        "summary": "Découvrez la commande, comprenez son rôle, testez-la dans le terminal et appliquez-la dans un mini-exercice.",
        "objectives": [
            "Comprendre la commande et son but",
            "Tester plusieurs cas d'usage",
            "Appliquer la commande dans un mini-exercice"
        ],
        "prerequisites": ["Base Bash", "Terminal Linux"],
        "sections": [
            {
                "id": "intro",
                "name": "Introduction",
                "content": "La commande est la pierre angulaire de l'automatisation en Bash. En l'observant, en l'appliquant et en la testant, l'apprenant construit une vraie compréhension pratique.",
            },
            {
                "id": "syntax",
                "name": "Syntaxe",
                "content": "La bonne syntaxe permet d'éviter les erreurs et de comprendre rapidement les effets de la commande.",
            },
            {
                "id": "examples",
                "name": "Exemples",
                "content": "Les exemples concrets aident à mémoriser le comportement et à transférer la connaissance à d'autres commandes.",
            },
            {
                "id": "challenge",
                "name": "Mini-exercice",
                "content": "Une fois que la commande est comprise, passez à l'application avec un petit exercice guidé.",
            }
        ],
        "command_reference": [
            {
                "command": "echo 'Bonjour'",
                "role": "Afficher du texte",
                "example": "echo 'Bonjour Shellforge'"
            }
        ],
        "exercises": [
            {
                "prompt": "Écris une commande Bash qui affiche le message Bonjour Shellforge.",
                "expected": "echo 'Bonjour Shellforge'",
                "hint": "Utilise echo pour afficher du texte directement dans le terminal."
            }
        ]
    }

    challenge_overrides = {
        "c01": {
            "title": "Premiers pas avec Bash",
            "summary": "Découvre comment afficher un texte et l'exécuter dans un script simple.",
            "objectives": [
                "Créer un script minimal",
                "Afficher un message texte",
                "Valider le résultat dans le terminal"
            ],
            "prerequisites": ["Notions de terminal Linux"],
            "sections": [
                {
                    "id": "intro",
                    "name": "Introduction",
                    "content": "Un script Bash est juste une suite d'instructions exécutées de haut en bas. La commande echo affiche rapidement une chaîne de caractères."
                },
                {
                    "id": "syntax",
                    "name": "Syntaxe",
                    "content": "echo 'texte' affiche exactement le texte donné. En Bash, on peut ajouter des variables, des arguments et des guillemets selon le besoin."
                },
                {
                    "id": "examples",
                    "name": "Exemples",
                    "content": "echo 'Salut' affiche Salut. echo \"Bonjour $USER\" affiche un message personnalisé."
                },
                {
                    "id": "challenge",
                    "name": "Mini-exercice",
                    "content": "Créez un script qui affiche Hello World et vérifiez sa sortie dans le terminal."
                }
            ],
            "command_reference": [
                {"command": "echo 'Bonjour'", "role": "Afficher une ligne de texte", "example": "echo 'Bonjour'"},
                {"command": "echo \"Bonjour $USER\"", "role": "Afficher du texte avec variable", "example": "echo \"Bonjour $USER\""}
            ],
            "exercises": [
                {
                    "prompt": "Écris la commande qui affiche Bonjour World !",
                    "expected": "echo 'Bonjour World!'",
                    "hint": "Le mot-clé echo suffit pour afficher une chaîne de caractères."
                }
            ]
        },
        "c02": {
            "title": "Lister l'aide de ls",
            "summary": "Comprenez comment utiliser l’aide intégré des commandes GNU pour découvrir les options disponibles.",
            "objectives": ["Trouver les options utiles", "Lire l’aide intégrée d’une commande", "Tester une commande sans risque"],
            "prerequisites": ["Commandes Linux basiques"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "La plupart des commandes Linux exposent une aide intégrée pour documenter leurs options."},
                {"id": "syntax", "name": "Syntaxe", "content": "help ls affiche l’aide de la commande shell. ls --help affiche le manuel de la commande."},
                {"id": "examples", "name": "Exemples", "content": "help ls ; ls --help ; man ls"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Récupérez une courte aide sur ls et identifiez au moins une option utile."}
            ],
            "command_reference": [
                {"command": "help ls", "role": "Aide Bash intégrée", "example": "help ls"},
                {"command": "ls --help", "role": "Aide GNU de ls", "example": "ls --help"}
            ],
            "exercises": [
                {"prompt": "Écris la commande qui affiche l’aide de ls.", "expected": "help ls", "hint": "La commande help est une aide native du shell."}
            ]
        },
        "c03": {
            "title": "Chemins relatifs et absolus",
            "summary": "Comprenez la différence entre un chemin absolu et un chemin relatif pour naviguer correctement en Bash.",
            "objectives": ["Différencier les chemins", "Utiliser le répertoire courant", "Éviter les erreurs de localisation"],
            "prerequisites": ["Navigation dans le terminal"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "Les chemins décrivent où se trouve un fichier ou un dossier. Les chemins absolus partent de / et les relatifs dépendent du dossier courant."},
                {"id": "syntax", "name": "Syntaxe", "content": "./script.sh appelle un script dans le répertoire courant, tandis que /etc/hosts pointe directement vers un fichier absolu."},
                {"id": "examples", "name": "Exemples", "content": "./script.sh ; /etc/passwd ; ../mon_projet"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Identifiez quel chemin est absolu et lequel est relatif dans un script simple."}
            ],
            "command_reference": [
                {"command": "./script.sh", "role": "Exécuter un script local", "example": "./script.sh"},
                {"command": "/etc/hosts", "role": "Chemin absolu vers un fichier système", "example": "/etc/hosts"}
            ],
            "exercises": [
                {"prompt": "Écris un chemin absolu vers le dossier /home.", "expected": "/home", "hint": "Un chemin absolu commence toujours par /."}
            ]
        },
        "c04": {
            "title": "Variables et arguments",
            "summary": "Apprenez à stocker les paramètres fournis au script dans une variable pour les réutiliser.",
            "objectives": ["Récupérer un argument", "Le stocker dans une variable", "L'afficher proprement"],
            "prerequisites": ["Script Bash minimal"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "Quand un script est lancé, ses arguments sont accessibles via $1, $2 et ainsi de suite."},
                {"id": "syntax", "name": "Syntaxe", "content": "nom_var=$1 ; echo \"La valeur est: $nom_var\" ;"},
                {"id": "examples", "name": "Exemples", "content": "./script.sh hello ; ./script.sh 'Iris'"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Chargez le premier argument dans une variable puis affichez-la avec un message explicite."}
            ],
            "command_reference": [
                {"command": "$1", "role": "Premier argument du script", "example": "$1"},
                {"command": "echo \"Valeur: $1\"", "role": "Afficher une variable d'argument", "example": "echo \"Valeur: $1\""}
            ],
            "exercises": [
                {"prompt": "Écris la commande qui affiche La valeur est: arg1.", "expected": "echo \"La valeur est: $1\"", "hint": "Utilise $1 pour le premier argument."}
            ]
        },
        "c05": {
            "title": "Définir des variables",
            "summary": "Comprenez la déclaration de variables, un concept central pour écrire des scripts lisibles et réutilisables.",
            "objectives": ["Déclarer une variable", "La lire à l'intérieur du script", "Afficher sa valeur"],
            "prerequisites": ["Syntaxe de base Bash"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "Une variable permet de stocker une valeur afin de la réutiliser plusieurs fois dans un script."},
                {"id": "syntax", "name": "Syntaxe", "content": "message=Bonjour ; echo $message ;"},
                {"id": "examples", "name": "Exemples", "content": "nom=Alice ; echo \"Bonjour $nom\" ;"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Créez une variable nommée message et affichez-la sans ajouter de guillemets autour de la variable."}
            ],
            "command_reference": [
                {"command": "message=Hello", "role": "Définir une variable", "example": "message=Hello"},
                {"command": "echo $message", "role": "Afficher la valeur d'une variable", "example": "echo $message"}
            ],
            "exercises": [
                {"prompt": "Écris la commande qui définit la variable message à Hello puis l'affiche.", "expected": "message=Hello\necho $message", "hint": "La variable reçoit la valeur sans espace avant ou après le signe égal."}
            ]
        },
        "c06": {
            "title": "Taille d'une chaîne",
            "summary": "Mesurez la taille d'une chaîne pour contrôler le comportement de vos scripts.",
            "objectives": ["Calculer la longueur d'une chaîne", "Utiliser la syntaxe Bash native", "Préparer une validation sûre"],
            "prerequisites": ["Variables et paramètres"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "${#var} est une syntaxe Bash très utile pour savoir combien de caractères contient une chaîne."},
                {"id": "syntax", "name": "Syntaxe", "content": "echo ${#nom_var} ;"},
                {"id": "examples", "name": "Exemples", "content": "mot=Bonjour ; echo ${#mot} ;"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Calculez la longueur du premier argument et affichez uniquement le nombre obtenu."}
            ],
            "command_reference": [
                {"command": "${#var}", "role": "Longueur d'une variable", "example": "${#texte}"},
                {"command": "echo ${#1}", "role": "Longueur du premier argument", "example": "echo ${#1}"}
            ],
            "exercises": [
                {"prompt": "Écris la commande qui affiche la longueur de la variable texte.", "expected": "echo ${#texte}", "hint": "Le symbole # mesure la longueur d'une chaîne."}
            ]
        },
        "c07": {
            "title": "Tester l'existence d'un fichier",
            "summary": "Vérifiez si un fichier ou dossier existe avant de l'utiliser dans votre script.",
            "objectives": ["Tester un chemin", "Prévenir les erreurs", "Étendre les scripts"],
            "prerequisites": ["Conditions Bash"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "Avant d'ouvrir ou d'utiliser un fichier, il vaut mieux vérifier qu'il existe réellement."},
                {"id": "syntax", "name": "Syntaxe", "content": "if [ -e fichier ]; then ...; fi"},
                {"id": "examples", "name": "Exemples", "content": "if [ -e /etc/hosts ]; then echo 'OK'; fi"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Vérifiez qu'un chemin existe et affichez un message en conséquence."}
            ],
            "command_reference": [
                {"command": "[ -e fichier ]", "role": "Teste l'existence d'un fichier", "example": "[ -e /etc/hosts ]"},
                {"command": "[ -d dossier ]", "role": "Teste l'existence d'un dossier", "example": "[ -d /etc ]"}
            ],
            "exercises": [
                {"prompt": "Écris la condition qui vérifie si le fichier /etc/hosts existe.", "expected": "[ -e /etc/hosts ]", "hint": "Le test -e détermine l'existence d'un chemin."}
            ]
        },
        "c10": {
            "title": "Les boucles for",
            "summary": "Répétez une action sur plusieurs valeurs avec une structure de boucle claire et lisible.",
            "objectives": ["Simplifier la répétition", "Parcourir une liste de valeurs", "Automatiser un workflow"],
            "prerequisites": ["Conditions Bash", "Variables"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "Les boucles permettent d'appliquer la même action à plusieurs éléments sans recopier le code."},
                {"id": "syntax", "name": "Syntaxe", "content": "for item in liste; do commande; done"},
                {"id": "examples", "name": "Exemples", "content": "for i in 1 2 3; do echo $i; done"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Affichez les nombres 1 à 5 avec une seule boucle for."}
            ],
            "command_reference": [
                {"command": "for i in 1 2 3; do echo $i; done", "role": "Boucle simple sur une liste", "example": "for i in 1 2 3; do echo $i; done"},
                {"command": "for f in *.txt; do echo $f; done", "role": "Traiter plusieurs fichiers", "example": "for f in *.txt; do echo $f; done"}
            ],
            "exercises": [
                {"prompt": "Écris une boucle for qui affiche les nombres 1, 2 et 3.", "expected": "for i in 1 2 3; do echo $i; done", "hint": "La liste de valeurs est écrite directement entre in et ; do."}
            ]
        },
        "c19": {
            "title": "Recherche de motifs avec grep",
            "summary": "Filtrez les lignes pertinentes d'un fichier ou d'un arbre de fichiers à l'aide de grep.",
            "objectives": ["Rechercher un terme", "Limiter le résultat", "Comprendre la sortie grep"],
            "prerequisites": ["Fichiers texte", "Terminal Linux"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "grep est l'outil de base pour chercher des motifs dans du texte, qu'il s'agisse de logs, de fichiers de configuration ou d'archives."},
                {"id": "syntax", "name": "Syntaxe", "content": "grep [options] motif fichier"},
                {"id": "examples", "name": "Exemples", "content": "grep -n 'ERROR' journal.log ; grep -r 'admin' /var/log"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Utilisez grep pour trouver un motif précis dans un fichier texte."}
            ],
            "command_reference": [
                {"command": "grep 'ERROR' fichier.log", "role": "Chercher un motif simple", "example": "grep 'ERROR' fichier.log"},
                {"command": "grep -r 'admin' /var/log", "role": "Recherche récursive", "example": "grep -r 'admin' /var/log"}
            ],
            "exercises": [
                {"prompt": "Écris la commande qui recherche ERROR dans un fichier journal.", "expected": "grep 'ERROR' journal.log", "hint": "Le premier paramètre est le motif, le second est le fichier."}
            ]
        },
        "c22": {
            "title": "Permissions Linux",
            "summary": "Les permissions des fichiers contrôlent qui peut lire, modifier ou exécuter un élément.",
            "objectives": ["Lire les permissions", "Interpréter les bits Unix", "Comprendre le rôle du propriétaire"],
            "prerequisites": ["Aide de ls", "Droits de fichier"],
            "sections": [
                {"id": "intro", "name": "Introduction", "content": "ls -l affiche les permissions sous la forme rwxrwxr-x. Ces bits sont lus par groupe : propriétaire, groupe et autres."},
                {"id": "syntax", "name": "Syntaxe", "content": "ls -l fichier ; chmod 755 script.sh ; chown user fichier"},
                {"id": "examples", "name": "Exemples", "content": "ls -l /etc/passwd ; chmod 755 script.sh ; chown student script.sh"},
                {"id": "challenge", "name": "Mini-exercice", "content": "Visualisez les permissions d'un fichier système et interprétez les droits affichés."}
            ],
            "command_reference": [
                {"command": "ls -l /etc/passwd", "role": "Afficher les permissions", "example": "ls -l /etc/passwd"},
                {"command": "chmod 755 script.sh", "role": "Modifier les droits d'exécution", "example": "chmod 755 script.sh"}
            ],
            "exercises": [
                {"prompt": "Écris la commande qui affiche les droits du fichier /etc/passwd.", "expected": "ls -l /etc/passwd", "hint": "ls -l affiche le détail des permissions et du propriétaire."}
            ]
        }
    }

    override = challenge_overrides.get(challenge_id)
    if override:
        merged = base_engine.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key] = value
            else:
                merged[key] = value
        return merged
    return base_engine


# --- Routes API ---

@app.get("/")
async def root():
    return {"message": "Bienvenue sur SHELLFORGE API", "version": "1.0.0"}


@app.get("/api/modules")
async def list_modules(db=Depends(get_db)):
    """Lister tous les modules disponibles."""
    c = db.cursor()
    c.execute("SELECT * FROM modules WHERE active = TRUE ORDER BY level ASC")
    modules = c.fetchall()
    return {"modules": [dict(m) for m in modules]}


@app.get("/api/modules/{module_id}/challenges")
async def list_challenges(module_id: str, db=Depends(get_db)):
    """Lister les défis d'un module sans exposer les réponses attendues."""
    c = db.cursor()
    c.execute("SELECT * FROM challenges WHERE module_id = ? ORDER BY difficulty ASC, points ASC", (module_id,))
    challenges = c.fetchall()
    return {"challenges": [serialize_challenge(ch) for ch in challenges]}


@app.get("/api/challenges/{challenge_id}")
async def get_challenge(challenge_id: str, db=Depends(get_db)):
    """Retourner le détail complet d’un défi, y compris les métadonnées pédagogiques et la réponse attendue pour l’interface de validation."""
    c = db.cursor()
    c.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
    challenge = c.fetchone()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge introuvable")
    payload = serialize_challenge(challenge, include_expected_output=True)
    payload["learning_engine"] = build_learning_engine(challenge_id)
    return payload


@app.get("/api/challenges/{challenge_id}/learning-progress")
async def get_challenge_learning_progress(challenge_id: str, session_id: str, db=Depends(get_db)):
    """Retourne la progression pédagogique d'une mission pour une session."""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id requis")

    challenge = db.execute("SELECT id FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge introuvable")

    engine = build_learning_engine(challenge_id)
    progress = build_learning_progress_state(session_id, challenge_id, engine)
    return {"challenge_id": challenge_id, "session_id": session_id, **progress}


@app.post("/api/learning/progress")
async def update_learning_progress(payload: LearningProgressRequest, db=Depends(get_db)):
    """Met à jour la progression pédagogique d'une leçon dans une mission."""
    if not payload.session_id or not payload.challenge_id or not payload.lesson_id:
        raise HTTPException(status_code=400, detail="session_id, challenge_id et lesson_id requis")

    challenge = db.execute("SELECT id FROM challenges WHERE id = ?", (payload.challenge_id,)).fetchone()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge introuvable")

    if payload.status not in {"not_started", "in_progress", "completed"}:
        raise HTTPException(status_code=400, detail="status invalide")

    lesson_id = payload.lesson_id
    now = datetime.utcnow().isoformat(timespec="seconds")
    row_id = f"{payload.session_id}:{payload.challenge_id}:{lesson_id}"
    exec_sql(
        db,
        """
        INSERT INTO lesson_progress (id, session_id, challenge_id, lesson_id, status, score, updated_at)
        VALUES (?, ?, ?, ?, ?, 10, ?)
        ON CONFLICT(id) DO UPDATE SET status = excluded.status, score = excluded.score, updated_at = excluded.updated_at
        """,
        (row_id, payload.session_id, payload.challenge_id, lesson_id, payload.status, now),
    )

    engine = build_learning_engine(payload.challenge_id)
    progress = build_learning_progress_state(payload.session_id, payload.challenge_id, engine)
    return {"challenge_id": payload.challenge_id, "session_id": payload.session_id, **progress}


@app.post("/api/sessions")
async def create_session(session: SessionCreate, db=Depends(get_db)):
    """Créer une nouvelle session d'apprentissage."""
    session_id = str(uuid.uuid4())
    c = db.cursor()
    exec_sql(db, "INSERT INTO sessions (id, user_id) VALUES (?, ?)", (session_id, session.user_id))
    return {"session_id": session_id, "message": "Session créée avec succès"}


@app.post("/api/submissions")
async def submit_challenge(submission: ChallengeSubmission, db=Depends(get_db)):
    """Valider une réponse utilisateur en exigeant la commande réelle et en empêchant les récompenses dupliquées."""
    session_id = submission.session_id
    challenge_id = submission.challenge_id
    output = submission.output
    command = submission.command

    c = db.cursor()
    c.execute("SELECT * FROM challenges WHERE id = ?", (challenge_id,))
    challenge = c.fetchone()

    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge introuvable")

    if not command or not command.strip():
        raise HTTPException(status_code=400, detail="Une commande de validation est requise pour soumettre une mission.")

    if normalize_command(command) != normalize_command(challenge["command"]):
        raise HTTPException(status_code=400, detail="La commande soumise ne correspond pas à la mission demandée.")

    c.execute("SELECT * FROM progress WHERE session_id = ? AND challenge_id = ? ORDER BY started_at DESC LIMIT 1", (session_id, challenge_id))
    existing = c.fetchone()
    if existing and existing["correct"]:
        return {
            "challenge_id": challenge_id,
            "correct": True,
            "points_earned": 0,
            "message": "Défi déjà validé pour cette session."
        }

    is_correct = False
    if challenge["validation"] == "exact":
        is_correct = output.strip() == challenge["expected_output"].strip()
    elif challenge["validation"] == "contains":
        is_correct = challenge["expected_output"] in output
    else:
        is_correct = output.strip() == challenge["expected_output"].strip()

    if existing:
        exec_sql(db, "UPDATE progress SET attempted = TRUE, correct = ?, attempts = attempts + 1, completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END WHERE session_id = ? AND challenge_id = ?",
            (int(is_correct), int(is_correct), session_id, challenge_id))
    else:
        if is_correct:
            exec_sql(db, "INSERT INTO progress (id, session_id, challenge_id, attempted, correct, attempts, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (str(uuid.uuid4()), session_id, challenge_id, True, 1, 1))
        else:
            exec_sql(db, "INSERT INTO progress (id, session_id, challenge_id, attempted, correct, attempts, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)",
                (str(uuid.uuid4()), session_id, challenge_id, True, 0, 1))

    if is_correct:
        c.execute("SELECT COUNT(*) AS already_awarded FROM progress WHERE session_id = ? AND challenge_id = ? AND correct = 1", (session_id, challenge_id))
        awarded_rows = c.fetchone()
        if awarded_rows and awarded_rows["already_awarded"] <= 1:
            exec_sql(db, "UPDATE sessions SET score = score + ? WHERE id = ?", (challenge["points"], session_id))

    db.commit()
    db.close()

    return {
        "challenge_id": challenge_id,
        "correct": is_correct,
        "points_earned": challenge["points"] if is_correct else 0,
        "message": "Mission validée." if is_correct else "Mission non validée."
    }


@app.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: str, db=Depends(get_db)):
    """Récupérer la progression d'une session."""
    c = db.cursor()
    c.execute("""SELECT p.*, ch.title as challenge_title, ch.points as challenge_points
        FROM progress p
        JOIN challenges ch ON p.challenge_id = ch.id
        WHERE p.session_id = ?
        ORDER BY p.started_at DESC""", (session_id,))
    progress = c.fetchall()
    return {"progress": [dict(p) for p in progress]}


@app.get("/api/sessions/{session_id}/stats")
async def get_stats(session_id: str, db=Depends(get_db)):
    """Statistiques de session."""
    c = db.cursor()
    c.execute("""SELECT
        COUNT(*) as total,
        SUM(CASE WHEN correct THEN 1 ELSE 0 END) as correct,
        SUM(CASE WHEN NOT correct THEN 1 ELSE 0 END) as incorrect,
        AVG(attempts) as avg_attempts
        FROM progress WHERE session_id = ?""", (session_id,))
    stats = c.fetchone()
    return {"stats": dict(stats) if stats else {"total": 0, "correct": 0, "incorrect": 0, "avg_attempts": 0}}


@app.get("/api/sessions/{session_id}/summary")
async def get_session_summary(session_id: str, db=Depends(get_db)):
    """Retourne le résumé global de la progression d'une session, module par module."""
    c = db.cursor()
    c.execute("SELECT score, level FROM sessions WHERE id = ?", (session_id,))
    session = c.fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")

    c.execute("""SELECT COALESCE(SUM(ch.points), 0) AS xp_earned
        FROM progress p
        JOIN challenges ch ON ch.id = p.challenge_id
        WHERE p.session_id = ? AND p.correct = 1""", (session_id,))
    xp_result = c.fetchone()
    xp_earned = int(xp_result["xp_earned"]) if xp_result else 0
    calculated_level = calculate_level_from_xp(xp_earned)
    exec_sql(db, "UPDATE sessions SET score = ?, level = ? WHERE id = ?", (xp_earned, calculated_level, session_id))

    c.execute("""SELECT m.id, m.title, m.level, m.xp_reward,
        COUNT(ch.id) AS total_challenges,
        SUM(CASE WHEN p.correct = 1 THEN 1 ELSE 0 END) AS completed_challenges,
        COALESCE(SUM(CASE WHEN p.correct = 1 THEN ch.points ELSE 0 END), 0) AS earned_xp
        FROM modules m
        LEFT JOIN challenges ch ON ch.module_id = m.id
        LEFT JOIN progress p ON p.challenge_id = ch.id AND p.session_id = ?
        WHERE m.active = TRUE
        GROUP BY m.id, m.title, m.level, m.xp_reward
        ORDER BY m.level, m.id""", (session_id,))
    module_rows = c.fetchall()

    modules = []
    for row in module_rows:
        total = int(row["total_challenges"] or 0)
        completed = int(row["completed_challenges"] or 0)
        modules.append({
            "id": row["id"],
            "title": row["title"],
            "level": row["level"],
            "xp_reward": row["xp_reward"],
            "total_challenges": total,
            "completed_challenges": completed,
            "percentage": round((completed / total) * 100, 0) if total else 0,
            "earned_xp": int(row["earned_xp"] or 0),
            "unlocked": True,
        })

    for idx, module in enumerate(modules):
        if idx == 0:
            module["unlocked"] = True
            continue
        previous = modules[idx - 1]
        module["unlocked"] = previous["completed_challenges"] >= previous["total_challenges"] and previous["total_challenges"] > 0

    total_challenges = sum(item["total_challenges"] for item in modules)
    total_completed = sum(item["completed_challenges"] for item in modules)
    overall_percentage = round((total_completed / total_challenges) * 100, 1) if total_challenges else 0

    return {
        "session_id": session_id,
        "score": xp_earned,
        "level": calculated_level,
        "xp_earned": int(xp_earned),
        "completed_challenges": total_completed,
        "total_challenges": total_challenges,
        "overall_percentage": overall_percentage,
        "modules": modules,
    }


@app.post("/api/labs/reset")
async def reset_lab(payload: LabResetRequest):
    """Réinitialiser le workspace d'un laboratoire pour une session donnée."""
    validate_lab_segment(payload.session_id, "session_id")
    labs_root = (Path(tempfile.gettempdir()) / "shellforge-labs").resolve()
    root = labs_root / payload.session_id
    if root.is_symlink():
        raise HTTPException(status_code=400, detail="Répertoire de session invalide")
    target = root
    if payload.working_dir:
        validate_lab_segment(payload.working_dir, "working_dir")
        target = root / payload.working_dir

    if target.is_symlink():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    if payload.working_dir:
        seed_lab_workspace(target, payload.working_dir)
    else:
        seed_lab_workspace(root)

    return {
        "session_id": payload.session_id,
        "cwd": str(target),
        "message": "Le laboratoire a été réinitialisé.",
    }


@app.get("/api/labs/files")
async def list_lab_files(session_id: str, working_dir: str):
    """Lister les fichiers d'exercice et leur contenu dans le workspace de la mission."""
    root = Path(build_lab_dir(session_id, working_dir)).resolve()
    entries = []
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current_root)
        directory_names[:] = sorted(
            name for name in directory_names
            if not (current_path / name).is_symlink()
        )
        for name in directory_names:
            path = current_path / name
            entries.append({
                "path": path.relative_to(root).as_posix() + "/",
                "type": "directory",
            })
        for name in sorted(file_names):
            path = current_path / name
            if path.is_symlink():
                continue
            relative_path = path.relative_to(root).as_posix()
            size = path.stat().st_size
            entry = {"path": relative_path, "type": "file", "size": size}
            if size <= 65536:
                entry["content"] = path.read_text(encoding="utf-8", errors="replace")
            entries.append(entry)
            if len(entries) >= 200:
                break
        if len(entries) >= 200:
            break

    entries.sort(key=lambda item: (item["path"].count("/"), item["path"]))
    return {"session_id": session_id, "working_dir": working_dir, "entries": entries}


@app.post("/api/labs/run")
async def run_lab_command(payload: LabRunRequest):
    """Exécuter une commande Bash dans un dossier d'exercice isolé pour une session."""
    if not payload.command or not payload.command.strip():
        raise HTTPException(status_code=400, detail="Command is required")

    blocked = ["rm -rf /", "sudo ", "chmod 777 /", "mkfs", "dd if=/dev/zero", "> /dev/"]
    lowered = payload.command.lower()
    if any(token in lowered for token in blocked):
        raise HTTPException(status_code=400, detail="Cette commande est interdite dans le laboratoire Safeguard.")

    working_dir = build_lab_dir(payload.session_id, payload.working_dir)
    try:
        process = subprocess.run(
            ["bash", "-lc", payload.command],
            cwd=working_dir,
            env={**os.environ, "HOME": working_dir},
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="La commande a dépassé le temps autorisé dans le laboratoire.") from exc

    return {
        "session_id": payload.session_id,
        "cwd": working_dir,
        "exit_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)