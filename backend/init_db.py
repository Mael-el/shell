#!/usr/bin/env python3
import sqlite3, os

DB_PATH = "/home/shadow/shellforge/database/shellforge.db"
if os.path.exists(DB_PATH): os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Tables
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

# === MODULES (7 niveaux) ===
modules = [
    ("m01", "Introduction au Shell", "Premiers pas dans Bash et le terminal Linux", 1, "basics", 100, "easy", True),
    ("m02", "Variables et Arguments", "Gérer les variables et les paramètres du script", 1, "basics", 150, "easy", True),
    ("m03", "Conditions et Logique", "Structures if/then/else et opérateurs de test", 1, "basics", 200, "medium", True),
    ("m04", "Boucles", "Boucles for, while et jusqu'à automatiser les tâches", 1, "basics", 200, "medium", True),
    ("m05", "Redirections", "Manipuler stdout, stderr et pipes pour le flux de données", 2, "intermediate", 250, "medium", True),
    ("m06", "Fonctions", "Créer et utiliser des fonctions Bash pour modulariser le code", 2, "intermediate", 300, "hard", True),
    ("m07", "Expressions Régulières", "Utiliser grep et sed avec des patterns de recherche avancés", 3, "advanced", 350, "hard", True),
]
for m in modules:
    c.execute("INSERT OR IGNORE INTO modules VALUES (?,?,?,?,?,?,?,?)", m)

# === CHALLENGES (21 défis - 3 par module) ===

challenges = [
    # Level 01: Introduction
    ("c01", "m01", "Premier script Bash", "Créez un script qui affiche un message de bienvenue", "./hello.sh \"World\"", "Bonjour World!", "exact", 100, "easy"),
    ("c02", "m01", "Afficher l'aide", "Utilisez la commande help pour trouver information sur ls", "help ls", "Usage: ls [OPTION]... [FICHIER]...", "contains", 100, "easy"),
    ("c03", "m01", "Chemin absolu vs relatif", "Déterminez si un chemin est absolu ou relatif", "./paths.sh /home", "/home", "contains", 100, "easy"),

    # Level 02: Variables
    ("c04", "m02", "Utiliser des variables", "Afficher le premier argument passé au script", "./vars.sh arg1", "La valeur est: arg1", "exact", 150, "easy"),
    ("c05", "m02", "Définir une variable", "Créez une variable MY_VAR=\"Hello\" et affichez-la", "./varassign.sh", "Hello", "exact", 150, "easy"),
    ("c06", "m02", "Longueur de chaîne", "Affichez la longueur du mot \"Bonjour\"", "./length.sh Bonjour", "9", "exact", 150, "easy"),

    # Level 03: Conditions
    ("c07", "m03", "Tester si un fichier existe", "Vérifiez si /etc/hosts existe", "./check.sh /etc/hosts", "/etc/hosts existe", "exact", 200, "medium"),
    ("c08", "m03", "Comparaison de nombres", "Vérifiez si 10 est plus grand que 5", "./compare.sh 10 5", "10 est plus grand que 5", "exact", 200, "medium"),
    ("c09", "m03", "Condition utilisateur", "Demandez à l'utilisateur son nom et dites bonjour", "./welcome.sh", "Bonjour [nom]", "contains", 200, "medium"),

    # Level 04: Boucles
    ("c10", "m04", "Boucle for nombres", "Affichez les nombres de 1 à 5 en utilisant une boucle", "./forloop.sh", "1\n2\n3\n4\n5", "exact", 200, "medium"),
    ("c11", "m04", "Boucle while compteur", "Comptez de 0 à 3 en utilisant while", "./whileloop.sh", "0\n1\n2\n3", "exact", 200, "medium"),
    ("c12", "m04", "Boucle until", "Exécutez jusqu'à ce que compteur >= 5", "./untilloop.sh", "Compteur: 5", "exact", 200, "medium"),

    # Level 05: Redirections
    ("c13", "m05", "Rediriger stdout vers fichier", "Enregistrez la sortie standard dans output.log", "./redirect_std.sh > output.log", "[CONTENU]", "contains", 250, "medium"),
    ("c14", "m05", "Append dans un fichier", "Ajoutez à la fin de errors.log en utilisant >>", "./append.sh >> errors.log", "[ERREUR]", "contains", 250, "medium"),
    ("c15", "m05", "Pipes basic", "Comptez le nombre de lignes en utilisant un pipe", "cat files.txt | wc -l", "3", "contains", 250, "medium"),

    # Level 06: Fonctions
    ("c16", "m06", "Fonction addition", "Créez une fonction add() qui retourne la somme de 3 + 4", "./func_add.sh", "7", "exact", 300, "hard"),
    ("c17", "m06", "Fonction avec paramètres", "Affichez la longueur du premier argument", "./func_len.sh \"test\"", "4", "exact", 300, "hard"),
    ("c18", "m06", "Fonction retour", "Créez une fonction qui retourne une valeur de retour", "./func_ret.sh", "Exit code: 0", "contains", 300, "hard"),

    # Level 07: Expressions Régulières
    ("c19", "m07", "Recherche grep basique", "Trouvez des lignes contenant ERROR dans un log", "grep -r ERROR /var/log/", "ligne(s) trouvées", "contains", 350, "hard"),
    ("c20", "m07", "Remplacer avec sed", "Remplacez tous les \"old\" par \"new\" dans un fichier", 'sed -i "s/old/new/g" text.txt', "Remplacement effectué", "contains", 350, "hard"),
    ("c21", "m07", "Pattern complexe grep", "Utilisez une expression regex pour trouver des emails", "grep -E \"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}\" emails.txt", "trouvé@domaine", "contains", 350, "hard"),
]

for ch in challenges:
    c.execute("INSERT OR IGNORE INTO challenges VALUES (?,?,?,?,?,?,?,?,?,?,?)", ch)

conn.commit()
conn.close()
print(f"Base de données initialisée avec {len(modules)} modules et {len(challenges)} challenges")