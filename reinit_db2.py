#!/usr/bin/env python3
import sqlite3, os
DB_PATH = '/home/shadow/shellforge/database/shellforge.db'
if os.path.exists(DB_PATH): os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY, title TEXT, description TEXT, level INTEGER, category TEXT,
    xp_reward INTEGER, difficulty TEXT DEFAULT 'medium', active BOOLEAN DEFAULT TRUE)''')

c.execute('''CREATE TABLE IF NOT EXISTS challenges (
    id TEXT PRIMARY KEY, module_id TEXT, title TEXT, description TEXT, command TEXT,
    expected_output TEXT, validation TEXT, points INTEGER DEFAULT 100, difficulty TEXT DEFAULT 'medium')''')

# Modules
mods = [
    ('m01', 'Introduction au Shell', 'Premiers pas', 1, 'basics', 100, 'easy', True),
    ('m02', 'Variables et Arguments', 'Gérer les variables', 1, 'basics', 150, 'easy', True),
    ('m03', 'Conditions et Logique', 'Structures de test', 1, 'basics', 200, 'medium', True),
    ('m04', 'Boucles', 'Boucles de traitement', 1, 'basics', 200, 'medium', True),
    ('m05', 'Redirections', 'Manipuler stdout/stderr', 2, 'intermediate', 250, 'medium', True),
    ('m06', 'Fonctions', 'Créer des fonctions', 2, 'intermediate', 300, 'hard', True),
    ('m07', 'Expressions Régulières', 'Patterns avancés', 3, 'advanced', 350, 'hard', True),
]
for m in mods:
    c.execute('INSERT OR IGNORE INTO modules VALUES (?,?,?,?,?,?,?,?)', m)

# Challenges - 9 values matching 9 columns:
# (id, module_id, title, description, command, expected_output, validation, points, difficulty)
chals = [
    # Level 01: Introduction (c01-c03) - contains validation
    ('c01','m01','Premier script Bash','./hello.sh "World"','Bonjour World!','exact result','contains',100,'easy'),
    ('c02','m01','Afficher l aide','help ls','Usage: ls','Usage: ls','contains',100,'easy'),
    ('c03','m01','Chemin absolu relatif','./paths.sh /home','/home','/home','contains',100,'easy'),
    
    # Level 02: Variables (c04-c06) - exact validation
    ('c04','m02','Utiliser des variables','./vars.sh arg1','La valeur est: arg1','La valeur est: arg1','exact',150,'easy'),
    ('c05','m02','Définir une variable','./varassign.sh','Hello','Hello','exact',150,'easy'),
    ('c06','m02','Longueur de chaîne','./length.sh Bonjour','9','9','exact',150,'easy'),
    
    # Level 03: Conditions (c07-c09) - exact validation
    ('c07','m03','Tester fichier existe','./check.sh /etc/hosts','/etc/hosts existe','/etc/hosts existe','exact',200,'medium'),
    ('c08','m03','Comparaison nombres','./compare.sh 10 5','10 est plus grand que 5','10 est plus grand que 5','exact',200,'medium'),
    ('c09','m03','Condition utilisateur','./welcome.sh','Bonjour [nom]','Bonjour [nom]','exact',200,'medium'),
    
    # Level 04: Boucles (c10-c12) - exact validation
    ('c10','m04','Boucle for nombres','./forloop.sh','1\n2\n3\n4\n5','1\n2\n3\n4\n5','1\n2\n3\n4\n5','exact',200,'medium'),
    ('c11','m04','Boucle while compteur','./whileloop.sh','0\n1\n2\n3','0\n1\n2\n3','0\n1\n2\n3','exact',200,'medium'),
    ('c12','m04','Boucle until','./untilloop.sh','Compteur: 5','Compteur: 5','exact',200,'medium'),
    
    # Level 05: Redirections (c13-c15) - contains validation
    ('c13','m05','Rediriger stdout','./redirect_std.sh > output.log','[CONTENU]','[CONTENU]','contains',250,'medium'),
    ('c14','m05','Append fichier','./append.sh >> errors.log','[ERREUR]','[ERREUR]','contains',250,'medium'),
    ('c15','m05','Pipes basiques','cat test.txt | wc -l','3','3','contains',250,'medium'),
    
    # Level 06: Fonctions (c16-c18) - exact validation
    ('c16','m06','Fonction addition','./func_add.sh','add 3 4','7','7','exact',300,'hard'),
    ('c17','m06','Fonction avec paramètres','./func_len.sh test','4','4','exact',300,'hard'),
    ('c18','m06','Fonction retour','./func_ret.sh','Resultat: 7','Resultat: 7','exact',300,'hard'),
    
    # Level 07: Expressions Régulières (c19-c21) - contains validation
    ('c19','m07','Recherche grep basique','grep -r ERROR /var/log/','ligne(s) trouvées','ligne(s) trouvées','contains',350,'hard'),
    ('c20','m07','Remplacer avec sed','sed -i s/old/new/g text.txt','Remplacement effectué','Remplacement effectué','contains',350,'hard'),
    ('c21','m07','Pattern complexe grep','grep -E user@domain emails.txt','trouvé@domaine','trouvé@domaine','contains',350,'hard'),
]
for ch in chals:
    print(f'Inserting {ch[0]}: len={len(ch)}')
    c.execute('INSERT OR IGNORE INTO challenges VALUES (?,?,?,?,?,?,?,?,?)', ch)

conn.commit()
conn.close()
print('DB recreated successfully with correct expected_output and validation')