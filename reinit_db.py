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

# Challenges - exactly 9 values each matching the 9 columns
chals = [
    ('c01','m01','Premier script Bash','./hello.sh "World"','Bonjour World!',100,'easy','easy',1),
    ('c02','m01','Afficher l aide','help ls','Usage: ls',100,'easy','easy',2),
    ('c03','m01','Chemin absolu relatif','./paths.sh /home','/home',100,'easy','easy',3),
    ('c04','m02','Utiliser des variables','./vars.sh arg1','La valeur est: arg1',150,'easy','easy',1),
    ('c05','m02','Définir une variable','./varassign.sh','Hello',150,'easy','easy',2),
    ('c06','m02','Longueur de chaîne','./length.sh Bonjour','9',150,'easy','easy',3),
    ('c07','m03','Tester fichier existe','./check.sh /etc/hosts','/etc/hosts existe',200,'medium','medium',1),
    ('c08','m03','Comparaison nombres','./compare.sh 10 5','10 est plus grand que 5',200,'medium','medium',2),
    ('c09','m03','Condition utilisateur','./welcome.sh','Bonjour [nom]',200,'medium','medium',3),
    ('c10','m04','Boucle for nombres','./forloop.sh','1\n2\n3\n4\n5',200,'medium','medium',1),
    ('c11','m04','Boucle while compteur','./whileloop.sh','0\n1\n2\n3',200,'medium','medium',2),
    ('c12','m04','Boucle until','./untilloop.sh','Compteur: 5',200,'medium','medium',3),
    ('c13','m05','Rediriger stdout','./redirect_std.sh > output.log','[CONTENU]',250,'medium','medium',1),
    ('c14','m05','Append fichier','./append.sh >> errors.log','[ERREUR]',250,'medium','medium',2),
    ('c15','m05','Pipes basiques','cat test.txt | wc -l','3',250,'medium','medium',3),
    ('c16','m06','Fonction addition','./func_add.sh','add 3 4',300,'hard','hard',1),
    ('c17','m06','Fonction paramètres','./func_len.sh test','4',300,'hard','hard',2),
    ('c18','m06','Fonction retour','./func_ret.sh','Resultat: 7',300,'hard','hard',3),
    ('c19','m07','Recherche grep basique','grep -r ERROR /var/log/',1,350,'hard','hard',1),
    ('c20','m07','Remplacer avec sed','sed -i s/old/new/g text.txt',1,350,'hard','hard',2),
    ('c21','m07','Pattern complexe grep','grep -E user@domain emails.txt',1,350,'hard','hard',3),
]
for ch in chals:
    print(f'Inserting {ch[0]}: len={len(ch)} values={ch}')
    c.execute('INSERT OR IGNORE INTO challenges VALUES (?,?,?,?,?,?,?,?,?)', ch)

conn.commit()
conn.close()
print('DB recreated successfully')