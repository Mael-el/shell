-- SHELLFORGE Database Initialization Script
-- SQLite database schema

-- Create tables for the learning platform

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'active',
    score INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    level INTEGER NOT NULL,
    category TEXT NOT NULL,
    xp_reward INTEGER DEFAULT 100,
    difficulty TEXT DEFAULT 'medium',
    order_index INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS challenges (
    id TEXT PRIMARY KEY,
    module_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    command TEXT,
    expected_output TEXT,
    validation_type TEXT DEFAULT 'redirect', -- exact, contains, redirect, custom
    points INTEGER DEFAULT 100,
    difficulty TEXT DEFAULT 'medium',
    hints TEXT,
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (module_id) REFERENCES modules(id)
);

CREATE TABLE IF NOT EXISTS progress (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    challenge_id TEXT NOT NULL,
    attempted BOOLEAN DEFAULT FALSE,
    correct BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id)
);

CREATE TABLE IF NOT EXISTS user_stats (
    user_id TEXT PRIMARY KEY,
    total_challenges INTEGER DEFAULT 0,
    correct_challenges INTEGER DEFAULT 0,
    total_xp INTEGER DEFAULT 0,
    current_level INTEGER DEFAULT 1,
    streak_days INTEGER DEFAULT 0,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Insert default modules (Bash learning path)
INSERT OR IGNORE INTO modules (id, title, description, level, category, xp_reward, difficulty, order_index) VALUES
('m01', 'Introduction au Shell', 'Premiers pas dans Bash et le terminal Linux', 1, 'basics', 100, 'easy', 1),
('m02', 'Variables et Arguments', 'Gérer les variables et les paramètres du script', 1, 'basics', 150, 'easy', 2),
('m03', 'Conditions et Logique', 'Structures if/then/else et opérateurs de test', 1, 'basics', 200, 'medium', 3),
('m04', 'Boucles', 'Boucles for, while et until pour automatiser', 1, 'basics', 200, 'medium', 4),
('m05', 'Redirections', 'Manipuler stdout, stderr et pipes', 2, 'intermediate', 250, 'medium', 5),
('m06', 'Fonctions', 'Créer et utiliser des fonctions Bash', 2, 'intermediate', 300, 'hard', 6),
('m07', 'Expressions Régulières', 'Utiliser grep et sed avec des patterns regex', 3, 'advanced', 350, 'hard', 7);

-- Insert default challenges
INSERT OR IGNORE INTO challenges (id, module_id, title, description, command, expected_output, validation_type, points, difficulty, order_index) VALUES
-- Level 01: Introduction
('c01', 'm01', 'Premier script Bash', 'Créez un script qui affiche bonjour', './hello.sh "World"', 'Bonjour World!', 'exact', 100, 'easy', 1),
-- Level 02: Variables
('c02', 'm02', 'Utiliser des variables', 'Afficher le premier argument', './vars.sh arg1', 'La valeur est: arg1', 'exact', 150, 'easy', 1),
-- Level 03: Conditions
('c03', 'm03', 'Tester une condition', 'Vérifier si un nombre est pair', './conditions.sh 42', '42 est pair', 'exact', 200, 'medium', 1),
-- Level 04: Boucles
('c04', 'm04', 'Boucle for simple', 'Afficher les nombres de 1 à 5', './loops.sh', '1\n2\n3\n4\n5', 'exact', 200, 'medium', 1),
-- Level 05: Redirections ← C'est notre défi actuel
('c05', 'm05', 'Enregistrer les erreurs', 'Redirigez stderr vers errors.log', './challenge.sh 2> errors.log', '[ERROR] Permission denied', 'redirect', 250, 'medium', 1),
-- Level 06: Fonctions
('c06', 'm06', 'Créer une fonction', 'Fonction qui additionne deux nombres', './functions.sh 3 5', '8', 'exact', 300, 'hard', 1),
-- Level 07: Regex
('c07', 'm07', 'Rechercher avec grep', 'Trouver des lignes contenant un pattern', 'grep -E "^ERROR" log.txt', '1 line', 'contains', 350, 'hard', 1);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_session ON progress(session_id);
CREATE INDEX IF NOT EXISTS idx_progress_challenge ON progress(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenges_module ON challenges(module_id);
CREATE INDEX IF NOT EXISTS idx_user_stats ON user_stats(user_id);

-- Create a default admin user (password: admin123 hashed)
INSERT OR IGNORE INTO users (id, username, email) VALUES
('user-001', 'apprenant', 'apprenant@shellforge.local');

-- Create default session
INSERT OR IGNORE INTO sessions (id, user_id) VALUES
('session-001', 'user-001');

CREATE TRIGGER IF NOT EXISTS update_user_stats_after_progress
AFTER UPDATE ON progress
BEGIN
    -- This trigger updates user stats when progress is updated
    -- Implementation would go here for more advanced stats
END;