#!/usr/bin/env python3
import sqlite3, os

DB_PATH = "/home/shadow/shellforge/database/shellforge.db"
if os.path.exists(DB_PATH): os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Create tables
c.execute("""CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY, title TEXT, description TEXT, level INTEGER, category TEXT,
    xp_reward INTEGER, difficulty TEXT DEFAULT 'medium', active BOOLEAN DEFAULT TRUE)""")

c.execute("""CREATE TABLE IF NOT EXISTS challenges (
    id TEXT PRIMARY KEY, module_id TEXT, title TEXT, description TEXT, command TEXT,
    expected_output TEXT, validation TEXT, points INTEGER DEFAULT 100, difficulty TEXT DEFAULT 'medium',
    hints TEXT, order_index INTEGER DEFAULT 0)""")

c.execute("""CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, user_id TEXT, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP, status TEXT DEFAULT 'active', score INTEGER DEFAULT 0, level INTEGER DEFAULT 1)""")

c.execute("""CREATE TABLE IF NOT EXISTS progress (
    id TEXT PRIMARY KEY, session_id TEXT, challenge_id TEXT, attempted BOOLEAN DEFAULT FALSE,
    correct BOOLEAN DEFAULT FALSE, attempts INTEGER DEFAULT 0, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP)""")

# --- Insert modules (7 modules) ---
modules = [
    ("m01", "Introduction au Shell", "Premiers pas dans Bash et le terminal Linux", 1, "basics", 100, "easy", True),
    ("m02", "Variables et Arguments", "Gérer les variables et les paramètres du script", 1, "basics", 150, "easy", True),
    ("m03", "Conditions et Logique", "Structures if/then/else et opérateurs de test", 1, "basics", 200, "medium", True),
    ("m04", "Boucles", "Boucles for, while et until pour automatiser les tâches", 1, "basics", 200, "medium", True),
    ("m05", "Redirections", "Manipuler stdout, stderr et pipes pour le flux de données", 2, "intermediate", 250, "medium", True),
    ("m06", "Fonctions", "Créer et utiliser des fonctions Bash pour modulariser le code", 2, "intermediate", 300, "hard", True),
    ("m07", "Expressions Régulières", "Utiliser grep et sed avec des patterns de recherche avancés", 3, "advanced", 350, "hard", True),
]

for m in modules:
    c.execute("INSERT OR IGNORE INTO modules VALUES (?,?,?,?,?,?,?,?)", m)

# --- Insert challenges (21 challenges - 3 par module) ---
challenges = [
    # Level 01: Introduction (c01-c03)
    ("c01", "m01", "Premier script Bash",
     "./hello.sh \"World\"", "Bonjour World!", "exact", 100, "easy", None, 1),
    ("c02", "m01", "Afficher l'aide",
     "help ls", "Usage: ls [OPTION]... [FICHIER]...", "contains", 100, "easy", None, 2),
    ("c03", "m01", "Chemin absolu vs relatif",
     "./paths.sh /home", "/home", "contains", 100, "easy", None, 3),

    # Level 02: Variables (c04-c06)
    ("c04", "m02", "Utiliser des variables",
     "./vars.sh arg1", "La valeur est: arg1", "exact", 150, "easy", None, 1),
    ("c05", "m02", "Définir une variable",
     "./varassign.sh", "Hello", "exact", 150, "easy", None, 2),
    ("c06", "m02", "Longueur de chaîne",
     "./length.sh Bonjour", "9", "exact", 150, "easy", None, 3),

    # Level 03: Conditions (c07-c09)
    ("c07", "m03", "Tester si un fichier existe",
     "./check.sh /etc/hosts", "/etc/hosts existe", "exact", 200, "medium", None, 1),
    ("c08", "m03", "Comparaison de nombres",
     "./compare.sh 10 5", "10 est plus grand que 5", "exact", 200, "medium", None, 2),
    ("c09", "m03", "Condition utilisateur",
     "./welcome.sh", "Bonjour [nom]", "contains", 200, "medium", None, 3),

    # Level 04: Boucles (c10-c12)
    ("c10", "m04", "Boucle for nombres",
     "./forloop.sh", "1\n2\n3\n4\n5", "exact", 200, "medium", None, 1),
    ("c11", "m04", "Boucle while compteur",
     "./whileloop.sh", "0\n1\n2\n3", "exact", 200, "medium", None, 2),
    ("c12", "m04", "Boucle until",
     "./untilloop.sh", "Compteur: 5", "exact", 200, "medium", None, 3),

    # Level 05: Redirections (c13-c15)
    ("c13", "m05", "Rediriger stdout vers fichier",
     "./redirect_std.sh > output.log", "[CONTENU]", "contains", 250, "medium", None, 1),
    ("c14", "m05", "Append dans un fichier en utilisant >>",
     "./append.sh >> errors.log", "[ERREUR]", "contains", 250, "medium", None, 2),
    ("c15", "m05", "Pipes basiques",
     "cat files.txt | wc -l", "3", "contains", 250, "medium", None, 3),

    # Level 06: Fonctions (c16-c18)
    ("c16", "m06", "Fonction addition",
     "./func_add.sh", "7", "exact", 300, "hard", None, 1),
    ("c17", "m06", "Fonction avec paramètres",
     "./func_len.sh test", "4", "exact", 300, "hard", None, 2),
    ("c18", "m06", "Fonction retour",
     "./func_ret.sh", "Exit code: 0", "contains", 300, "hard", None, 3),

    # Level 07: Expressions Régulières (c19-c21)
    ("c19", "m07", "Recherche grep basique",
     "grep -r ERROR /var/log/", "ligne(s) trouvées", "contains", 350, "hard", None, 1),
    ("c20", "m07", "Remplacer avec sed",
     "sed -i 's/old/new/g' text.txt", "Remplacement effectué", "contains", 350, "hard", None, 2),
    ("c21", "m07", "Pattern complexe grep",
     "grep -E '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}' emails.txt", "trouvé@domaine", "contains", 350, "hard", None, 3),
]

for ch in challenges:
    c.execute("INSERT OR IGNORE INTO challenges VALUES (?,?,?,?,?,?,?,?,?,?,?)", ch)

conn.commit()
conn.close()
print(f"Base de données initialisée avec succès : 7 modules, 21 challenges")