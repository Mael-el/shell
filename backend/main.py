#!/usr/bin/env python3
"""SHELLFORGE Backend - plateforme d'apprentissage offensive et défensive.

Le contenu pédagogique vit dans ``backend/curriculum/*.json`` : chaque mission
combine un cours, un laboratoire équipé et des contrôles de preuves exécutés
côté serveur. Ce module expose l'API consommée par le front React.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import curriculum
import roadmap

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


for env_path in (BASE_DIR / ".env", BASE_DIR / "backend" / ".env"):
    _load_env_file(env_path)

DATABASE_DIR = Path(os.getenv("SHELLFORGE_DB_DIR", str(BASE_DIR / "database"))).expanduser()
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("SHELLFORGE_DB_PATH", str(DATABASE_DIR / "shellforge.db"))).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = (BASE_DIR / DB_PATH).resolve()

LAB_ROOT = Path(os.getenv("SHELLFORGE_LAB_ROOT", str(Path(tempfile.gettempdir()) / "shellforge-labs"))).expanduser()
LAB_TIMEOUT = int(os.getenv("SHELLFORGE_LAB_TIMEOUT", "20"))
MAX_FILE_PREVIEW = 65536


def _parse_origins(raw: str) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]
ALLOWED_ORIGINS = _parse_origins(os.getenv("CORS_ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS))) or DEFAULT_ALLOWED_ORIGINS
DEFAULT_ALLOWED_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?" r"|https?://[a-z0-9-]+\.e2b\.app"
ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ALLOWED_ORIGIN_REGEX", DEFAULT_ALLOWED_ORIGIN_REGEX)

app = FastAPI(
    title="SHELLFORGE API",
    description="Parcours progressif : fondations, administration Linux, reconnaissance, pentest, ingénierie.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------


def get_db():
    """Nouvelle connexion SQLite (WAL) par requête."""
    conn = sqlite3_connect()
    conn.row_factory = dict_row
    return conn


def sqlite3_connect():
    import sqlite3

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def dict_row(cursor, row):  # pragma: no cover - délégué à sqlite3.Row
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def exec_sql(conn, sql, params=None):
    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    conn.commit()
    return cursor


@app.on_event("startup")
def init_db() -> None:
    """Crée le schéma minimal (les contenus viennent du curriculum JSON)."""
    conn = get_db()
    exec_sql(
        conn,
        """CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            score INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )""",
    )
    exec_sql(
        conn,
        """CREATE TABLE IF NOT EXISTS mission_progress (
            session_id TEXT NOT NULL,
            mission_id TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            first_completed_at TIMESTAMP,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, mission_id)
        )""",
    )
    exec_sql(
        conn,
        """CREATE TABLE IF NOT EXISTS lesson_progress (
            session_id TEXT NOT NULL,
            mission_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            status TEXT DEFAULT 'not_started',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (session_id, mission_id, section_id)
        )""",
    )
    exec_sql(
        conn,
        """CREATE TABLE IF NOT EXISTS dojo_progress (
            session_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            PRIMARY KEY (session_id, task_id)
        )""",
    )
    exec_sql(conn, "CREATE INDEX IF NOT EXISTS idx_mission_progress_session ON mission_progress(session_id)")
    conn.close()


# ---------------------------------------------------------------------------
# Laboratoires : espace de travail isolé par session et par mission
# ---------------------------------------------------------------------------

BLOCKED_PATTERNS = [
    "rm -rf /",
    "mkfs",
    "dd if=/dev/zero",
    ":(){",
    "chmod -r 777 /",
    "> /dev/sda",
    "shutdown",
    "reboot",
]


def validate_lab_segment(value: str, field_name: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise HTTPException(status_code=400, detail=f"{field_name} invalide")
    return value


def _safe_join(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise HTTPException(status_code=400, detail="Chemin invalide")
    return candidate


def seed_lab_workspace(target: Path, mission: dict) -> None:
    """Amorce le laboratoire une seule fois, puis respecte le travail de l'apprenant.

    Les fichiers, dossiers et permissions de départ ne sont appliqués que sur un
    espace vierge (création ou réinitialisation). Les visites suivantes ne doivent
    jamais réécrire un fichier déplacé, modifié ou supprimé volontairement.
    """
    target.mkdir(parents=True, exist_ok=True)
    root = target.resolve()
    lab = mission["lab"]
    marker = root / ".shellforge-mission"
    existing = [entry for entry in root.iterdir() if entry.name != ".shellforge-mission"]
    fresh = not marker.exists() and not existing

    if fresh:
        for directory in lab.get("dirs", []):
            _safe_join(root, directory).mkdir(parents=True, exist_ok=True)
        for relative_path, content in lab.get("files", {}).items():
            path = _safe_join(root, relative_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        for relative_path, mode in lab.get("modes", {}).items():
            path = _safe_join(root, relative_path)
            if path.exists():
                os.chmod(path, int(str(mode), 8))
    else:
        # Espace déjà utilisé : on s'assure seulement que les dossiers existent.
        # Aucun fichier n'est recréé, sinon un fichier déplacé volontairement
        # (ou supprimé) réapparaîtrait à chaque visite.
        for directory in lab.get("dirs", []):
            _safe_join(root, directory).mkdir(parents=True, exist_ok=True)

    if not marker.exists():
        marker.write_text(f"{mission['id']} - {mission['title']}\n", encoding="utf-8")


def build_lab_dir(session_id: str, mission_id: str) -> Path:
    validate_lab_segment(session_id, "session_id")
    validate_lab_segment(mission_id, "working_dir")
    mission = curriculum.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")

    root = LAB_ROOT.resolve()
    root.mkdir(parents=True, exist_ok=True)
    session_dir = root / session_id
    if session_dir.is_symlink():
        raise HTTPException(status_code=400, detail="Répertoire de session invalide")
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir = session_dir.resolve()
    if not session_dir.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Répertoire de session invalide")

    target = session_dir / mission_id
    if target.is_symlink():
        raise HTTPException(status_code=400, detail="Répertoire de mission invalide")
    seed_lab_workspace(target, mission)
    resolved = target.resolve()
    if not resolved.is_relative_to(session_dir):
        raise HTTPException(status_code=400, detail="Répertoire de mission invalide")
    return resolved


def run_in_lab(workdir: Path, command: str, timeout: int | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(workdir), "SHELLFORGE_LAB": "1"}
    env.pop("SHELLFORGE_DB_PATH", None)
    return subprocess.run(
        ["bash", "-lc", command],
        cwd=str(workdir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout or LAB_TIMEOUT,
    )


# ---------------------------------------------------------------------------
# Vérification des preuves
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def evaluate_check(workdir: Path, check: dict) -> dict:
    """Exécute un contrôle et renvoie un résultat lisible par l'apprenant."""
    result = {"id": check["id"], "label": check["label"], "passed": False, "detail": ""}
    ctype = check["type"]

    if ctype in {"file_exists", "dir_exists", "file_contains", "file_not_contains", "file_mode"}:
        try:
            path = _safe_join(workdir, check["path"])
        except HTTPException:
            result["detail"] = "Chemin hors du laboratoire"
            return result
        if ctype == "file_exists":
            result["passed"] = path.is_file() and not path.is_symlink()
            result["detail"] = f"{check['path']} {'trouvé' if result['passed'] else 'absent'}"
            return result
        if ctype == "dir_exists":
            result["passed"] = path.is_dir() and not path.is_symlink()
            result["detail"] = f"{check['path']} {'trouvé' if result['passed'] else 'absent'}"
            return result
        if not path.is_file() or path.is_symlink():
            result["detail"] = f"{check['path']} est introuvable"
            return result
        if ctype == "file_mode":
            actual = format(stat.S_IMODE(path.stat().st_mode), "o")
            expected = str(check["mode"]).lstrip("0") or "0"
            normalized_actual = str(int(actual, 8))
            result["passed"] = normalized_actual == str(int(expected, 8))
            result["detail"] = f"mode observé {actual}, attendu {expected}"
            return result
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # pragma: no cover
            result["detail"] = f"lecture impossible : {exc}"
            return result
        match = re.search(check["pattern"], content, re.MULTILINE)
        if ctype == "file_contains":
            result["passed"] = bool(match)
            result["detail"] = "motif trouvé" if match else f"motif attendu /{check['pattern']}/ absent"
        else:
            result["passed"] = not match
            result["detail"] = "aucune occurrence interdite" if not match else "motif interdit détecté"
        return result

    if ctype == "run":
        try:
            process = run_in_lab(workdir, check["cmd"], timeout=check.get("timeout", 30))
        except subprocess.TimeoutExpired:
            result["detail"] = "commande de vérification expirée"
            return result
        output = (process.stdout or "") + "\n" + (process.stderr or "")
        matched = re.search(check["expect"], output, re.MULTILINE) is not None
        result["passed"] = matched and process.returncode == 0
        if not result["passed"]:
            tail = " ".join(output.split())[:220]
            result["detail"] = f"sortie inattendue (code {process.returncode}) : {tail or 'vide'}"
        else:
            result["detail"] = "vérification réussie"
        return result

    result["detail"] = "type de contrôle inconnu"
    return result


def verify_mission(workdir: Path, mission: dict) -> dict:
    checks = [evaluate_check(workdir, check) for check in mission["lab"]["checks"]]
    passed = all(item["passed"] for item in checks)
    return {
        "mission_id": mission["id"],
        "passed": passed,
        "checks": checks,
        "passed_count": sum(1 for item in checks if item["passed"]),
        "total_count": len(checks),
    }


# ---------------------------------------------------------------------------
# Progression
# ---------------------------------------------------------------------------


def session_progress_map(session_id: str) -> dict[str, dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT mission_id, attempts, completed, score FROM mission_progress WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return {row["mission_id"]: row for row in rows}


def completed_missions(session_id: str) -> set[str]:
    return {
        mission_id
        for mission_id, row in session_progress_map(session_id).items()
        if row["completed"]
    }


def dojo_progress_map(session_id: str) -> dict[str, dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT task_id, score, completed_at FROM dojo_progress WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return {row["task_id"]: row for row in rows}


def dojo_xp(session_id: str) -> int:
    """XP gagné dans le dojo (tâches cochées), séparé de l'XP des missions."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(score), 0) AS xp FROM dojo_progress WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    finally:
        conn.close()
    return int(row["xp"] or 0)


def recompute_session_score(session_id: str) -> dict:
    """Recalcule le score total (missions + dojo) et le niveau de la session."""
    conn = get_db()
    try:
        mission_xp = conn.execute(
            "SELECT COALESCE(SUM(score), 0) AS xp FROM mission_progress WHERE session_id = ?",
            (session_id,),
        ).fetchone()["xp"]
        dojo = conn.execute(
            "SELECT COALESCE(SUM(score), 0) AS xp FROM dojo_progress WHERE session_id = ?",
            (session_id,),
        ).fetchone()["xp"]
        total = int(mission_xp or 0) + int(dojo or 0)
        level = calculate_level_from_xp(total)
        exec_sql(
            conn,
            "UPDATE sessions SET score = ?, level = ?, last_seen_at = ? WHERE id = ?",
            (total, level, datetime.now(timezone.utc).isoformat(timespec="seconds"), session_id),
        )
    finally:
        conn.close()
    return {"mission_xp": int(mission_xp or 0), "dojo_xp": int(dojo or 0), "total_xp": total, "level": level}


def build_roadmap(session_id: str | None = None) -> dict:
    """Vue du plan d'entraînement, enrichie de l'avancement de la session."""
    rows = dojo_progress_map(session_id) if session_id else {}
    completed = {task_id for task_id, row in rows.items() if row["completed_at"]}
    scores = {task_id: int(row["score"] or 0) for task_id, row in rows.items()}
    payload = roadmap.public_payload(completed, scores)
    payload["session_id"] = session_id
    return payload


def calculate_level_from_xp(xp: int) -> int:
    return 1 + (max(xp, 0) // 500)


def level_is_unlocked(level_index: int, levels: list[dict], completed: set[str]) -> bool:
    if level_index == 0:
        return True
    previous = levels[level_index - 1]
    total = len(previous["mission_ids"])
    if total == 0:
        return True
    done = sum(1 for mid in previous["mission_ids"] if mid in completed)
    return (done / total) >= 0.7


def module_state(module: dict, completed: set[str], levels: list[dict]) -> dict:
    mission_ids = module["mission_ids"]
    done = sum(1 for mid in mission_ids if mid in completed)
    level_index = next((i for i, lvl in enumerate(levels) if lvl["id"] == module["level"]), 0)
    return {
        "completed_missions": done,
        "total_missions": len(mission_ids),
        "percentage": round(done / len(mission_ids) * 100) if mission_ids else 0,
        "unlocked": level_is_unlocked(level_index, levels, completed),
    }


def record_attempt(session_id: str, mission: dict, passed: bool) -> dict:
    """Enregistre une tentative et renvoie l'XP réellement gagné."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT attempts, completed FROM mission_progress WHERE session_id = ? AND mission_id = ?",
            (session_id, mission["id"]),
        ).fetchone()
        already_completed = bool(row and row["completed"])
        attempts = (row["attempts"] if row else 0) + 1
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        score = mission["points"] if (passed and not already_completed) else 0
        exec_sql(
            conn,
            """INSERT INTO mission_progress (session_id, mission_id, attempts, completed, score, first_completed_at, last_activity_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id, mission_id) DO UPDATE SET
                 attempts = excluded.attempts,
                 completed = MAX(mission_progress.completed, excluded.completed),
                 score = mission_progress.score + excluded.score,
                 last_activity_at = excluded.last_activity_at,
                 first_completed_at = COALESCE(mission_progress.first_completed_at, excluded.first_completed_at)""",
            (
                session_id,
                mission["id"],
                attempts,
                1 if passed else 0,
                score,
                now if passed else None,
                now,
            ),
        )
    finally:
        conn.close()
    totals = recompute_session_score(session_id)
    total_xp = totals["total_xp"]
    level = totals["level"]
    return {
        "score_awarded": score,
        "already_completed": already_completed,
        "total_xp": int(total_xp),
        "level": level,
    }


def require_session(session_id: str) -> dict:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return row


def require_mission(mission_id: str) -> dict:
    mission = curriculum.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    return mission


def build_learning_progress(session_id: str, mission: dict) -> dict:
    sections = mission["lesson"].get("sections", [])
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT section_id, status FROM lesson_progress WHERE session_id = ? AND mission_id = ?",
            (session_id, mission["id"]),
        ).fetchall()
    finally:
        conn.close()
    statuses = {row["section_id"]: row["status"] for row in rows}
    states = [
        {"id": section["id"], "name": section["name"], "status": statuses.get(section["id"], "not_started")}
        for section in sections
    ]
    completed = sum(1 for item in states if item["status"] == "completed")
    return {
        "mission_id": mission["id"],
        "session_id": session_id,
        "total_sections": len(states),
        "completed_sections": completed,
        "progress_percent": round(completed / len(states) * 100) if states else 0,
        "sections": states,
    }


# ---------------------------------------------------------------------------
# Modèles de requête
# ---------------------------------------------------------------------------


class SessionCreate(BaseModel):
    user_id: str = "shellforge-user"


class LearningProgressRequest(BaseModel):
    session_id: str
    mission_id: str | None = None
    challenge_id: str | None = None
    lesson_id: str | None = None
    section_id: str | None = None
    status: str = "completed"


class RoadmapProgressRequest(BaseModel):
    session_id: str
    task_id: str
    done: bool = True


class LabRunRequest(BaseModel):
    session_id: str
    command: str
    working_dir: str | None = None
    mission_id: str | None = None


class LabResetRequest(BaseModel):
    session_id: str
    working_dir: str | None = None
    mission_id: str | None = None


# ---------------------------------------------------------------------------
# Routes : parcours
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    data = curriculum.load_curriculum()
    return {
        "message": "SHELLFORGE API",
        "version": "2.0.0",
        "levels": len(data["levels"]),
        "modules": len(data["modules"]),
        "missions": len(data["order"]),
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/levels")
async def list_levels(session_id: str | None = Query(default=None)):
    data = curriculum.load_curriculum()
    completed = completed_missions(session_id) if session_id else set()
    if session_id:
        require_session(session_id)
    levels = []
    for index, level in enumerate(data["levels"]):
        missions = [data["missions"][mid] for mid in level["mission_ids"]]
        done = sum(1 for mission in missions if mission["id"] in completed)
        levels.append(
            {
                "id": level["id"],
                "name": level["name"],
                "tagline": level["tagline"],
                "description": level["description"],
                "icon": level["icon"],
                "accent": level["accent"],
                "module_ids": level["module_ids"],
                "mission_ids": level["mission_ids"],
                "total_missions": len(missions),
                "completed_missions": done,
                "percentage": round(done / len(missions) * 100) if missions else 0,
                "xp_total": sum(mission["points"] for mission in missions),
                "unlocked": level_is_unlocked(index, data["levels"], completed),
            }
        )
    return {"levels": levels}


@app.get("/api/modules")
async def list_modules(session_id: str | None = Query(default=None)):
    data = curriculum.load_curriculum()
    completed = completed_missions(session_id) if session_id else set()
    payload = []
    for module in data["modules"]:
        summary = curriculum.module_summary(module)
        summary.update(module_state(module, completed, data["levels"]))
        payload.append(summary)
    return {"modules": payload}


@app.get("/api/modules/{module_id}")
async def get_module(module_id: str, session_id: str | None = Query(default=None)):
    data = curriculum.load_curriculum()
    module = curriculum.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module introuvable")
    completed = completed_missions(session_id) if session_id else set()
    payload = curriculum.module_summary(module)
    payload.update(module_state(module, completed, data["levels"]))
    for mission in payload["missions"]:
        mission["completed"] = mission["id"] in completed
        mission["locked"] = not payload["unlocked"]
    return payload


@app.get("/api/modules/{module_id}/challenges")
@app.get("/api/modules/{module_id}/missions")
async def list_module_missions(module_id: str, session_id: str | None = Query(default=None)):
    data = curriculum.load_curriculum()
    module = curriculum.get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Module introuvable")
    completed = completed_missions(session_id) if session_id else set()
    state = module_state(module, completed, data["levels"])
    missions = []
    for mission_id in module["mission_ids"]:
        mission = data["missions"][mission_id]
        item = curriculum.mission_summary(mission)
        item["completed"] = mission_id in completed
        item["locked"] = not state["unlocked"]
        missions.append(item)
    return {"module": module_id, **state, "missions": missions, "challenges": missions}


@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str, session_id: str | None = Query(default=None)):
    mission = require_mission(mission_id)
    payload = curriculum.mission_detail(mission)
    if session_id:
        require_session(session_id)
        progress = session_progress_map(session_id)
        row = progress.get(mission_id)
        payload["progress"] = {
            "attempts": row["attempts"] if row else 0,
            "completed": bool(row["completed"]) if row else False,
            "score": row["score"] if row else 0,
        }
        payload["learning_progress"] = build_learning_progress(session_id, mission)
        payload["next_mission"] = (curriculum.next_mission(mission_id) or {}).get("id")
    return payload


@app.get("/api/missions/{mission_id}/learning-progress")
async def get_mission_learning_progress(mission_id: str, session_id: str):
    mission = require_mission(mission_id)
    require_session(session_id)
    return build_learning_progress(session_id, mission)


@app.post("/api/learning/progress")
async def update_learning_progress(payload: LearningProgressRequest):
    mission_id = payload.mission_id or payload.challenge_id
    section_id = payload.section_id or payload.lesson_id
    if not mission_id or not section_id:
        raise HTTPException(status_code=400, detail="mission_id et section_id requis")
    mission = require_mission(mission_id)
    require_session(payload.session_id)
    if payload.status not in {"not_started", "in_progress", "completed"}:
        raise HTTPException(status_code=400, detail="status invalide")
    if section_id not in {section["id"] for section in mission["lesson"]["sections"]}:
        raise HTTPException(status_code=400, detail="section inconnue")

    conn = get_db()
    try:
        exec_sql(
            conn,
            """INSERT INTO lesson_progress (session_id, mission_id, section_id, status, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session_id, mission_id, section_id) DO UPDATE SET
                 status = excluded.status, updated_at = excluded.updated_at""",
            (
                payload.session_id,
                mission_id,
                section_id,
                payload.status,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    finally:
        conn.close()
    return build_learning_progress(payload.session_id, mission)


# ---------------------------------------------------------------------------
# Routes : plan d'entraînement (CyberDev Dojo)
# ---------------------------------------------------------------------------


@app.get("/api/roadmap")
async def get_roadmap(session_id: str | None = Query(default=None)):
    """Plan de 12 semaines, 6 niveaux, 24 tâches, avec l'avancement de la session."""
    if session_id:
        require_session(session_id)
    return build_roadmap(session_id)


@app.post("/api/roadmap/progress")
async def update_roadmap_progress(payload: RoadmapProgressRequest):
    """Coche ou décoche une tâche. L'XP n'est attribué qu'une seule fois par tâche."""
    task = roadmap.get_task(payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tâche inconnue")
    require_session(payload.session_id)

    conn = get_db()
    try:
        if payload.done:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            exec_sql(
                conn,
                """INSERT INTO dojo_progress (session_id, task_id, score, completed_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(session_id, task_id) DO UPDATE SET
                     completed_at = COALESCE(dojo_progress.completed_at, excluded.completed_at)""",
                (payload.session_id, task["id"], task["xp"], now),
            )
        else:
            exec_sql(
                conn,
                "DELETE FROM dojo_progress WHERE session_id = ? AND task_id = ?",
                (payload.session_id, task["id"]),
            )
        row = conn.execute(
            "SELECT score, completed_at FROM dojo_progress WHERE session_id = ? AND task_id = ?",
            (payload.session_id, task["id"]),
        ).fetchone()
    finally:
        conn.close()

    tracked = bool(row and row["completed_at"])
    totals = recompute_session_score(payload.session_id)
    payload_out = build_roadmap(payload.session_id)
    payload_out.update(
        {
            "task_id": task["id"],
            "done": tracked,
            "score_awarded": int(row["score"] or 0) if tracked else 0,
            "session_total_xp": totals["total_xp"],
            "session_level": totals["level"],
        }
    )
    return payload_out


@app.get("/api/resources")
async def get_resources():
    """Catalogue de ressources externes : laboratoires, programmation, auto-hébergement, jeux."""
    resources = roadmap.decorate_resources(roadmap.load_roadmap()["resources"])
    return {
        **resources,
        "verification": roadmap.verification_summary(),
    }


# ---------------------------------------------------------------------------
# Routes : sessions et vérification
# ---------------------------------------------------------------------------


@app.post("/api/sessions")
async def create_session(session: SessionCreate):
    session_id = str(uuid.uuid4())
    conn = get_db()
    try:
        exec_sql(conn, "INSERT INTO sessions (id, user_id) VALUES (?, ?)", (session_id, session.user_id))
    finally:
        conn.close()
    return {"session_id": session_id, "message": "Session créée"}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Valide l'existence d'une session (utilisé par le front pour détecter une session périmée)."""
    session = require_session(session_id)
    rows = session_progress_map(session_id)
    totals = recompute_session_score(session_id)
    return {
        "session_id": session_id,
        "user_id": session.get("user_id"),
        "score": totals["total_xp"],
        "level": totals["level"],
        "xp_missions": totals["mission_xp"],
        "xp_dojo": totals["dojo_xp"],
        "started_at": session.get("started_at"),
        "completed_missions": sum(1 for row in rows.values() if row["completed"]),
    }


@app.post("/api/missions/{mission_id}/verify")
async def verify(mission_id: str, payload: dict):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id requis")
    require_session(session_id)
    mission = require_mission(mission_id)
    workdir = build_lab_dir(session_id, mission_id)
    result = verify_mission(workdir, mission)
    outcome = record_attempt(session_id, mission, result["passed"])
    next_step = curriculum.next_mission(mission_id)
    return {
        **result,
        **outcome,
        "message": "Mission validée." if result["passed"] else "Certaines preuves sont manquantes.",
        "next_mission": next_step["id"] if next_step else None,
        "solution": mission["lab"].get("solution") if result["passed"] else None,
    }


@app.post("/api/submissions")
async def submit_legacy(payload: dict):
    """Compatibilité : accepte {session_id, mission_id|challenge_id}."""
    mission_id = payload.get("mission_id") or payload.get("challenge_id")
    if not mission_id:
        raise HTTPException(status_code=400, detail="mission_id requis")
    return await verify(mission_id, payload)


@app.get("/api/sessions/{session_id}/progress")
async def get_progress(session_id: str):
    require_session(session_id)
    rows = session_progress_map(session_id)
    data = curriculum.load_curriculum()
    progress = []
    for mission_id in data["order"]:
        row = rows.get(mission_id)
        if not row:
            continue
        mission = data["missions"][mission_id]
        progress.append(
            {
                "mission_id": mission_id,
                "title": mission["title"],
                "module_id": mission["module_id"],
                "level": mission["level"],
                "attempts": row["attempts"],
                "correct": bool(row["completed"]),
                "score": row["score"],
                "points": mission["points"],
            }
        )
    return {"session_id": session_id, "progress": progress}


@app.get("/api/sessions/{session_id}/stats")
async def get_stats(session_id: str):
    require_session(session_id)
    rows = list(session_progress_map(session_id).values())
    attempts = sum(row["attempts"] for row in rows)
    completed = sum(1 for row in rows if row["completed"])
    return {
        "stats": {
            "missions_touched": len(rows),
            "missions_completed": completed,
            "attempts": attempts,
            "success_rate": round(completed / len(rows) * 100) if rows else 0,
            "xp": sum(row["score"] for row in rows),
        }
    }


@app.get("/api/sessions/{session_id}/summary")
async def get_summary(session_id: str):
    session = require_session(session_id)
    data = curriculum.load_curriculum()
    completed = completed_missions(session_id)
    rows = session_progress_map(session_id)

    levels_payload = []
    for index, level in enumerate(data["levels"]):
        missions = [data["missions"][mid] for mid in level["mission_ids"]]
        done = sum(1 for mission in missions if mission["id"] in completed)
        points_done = sum(mission["points"] for mission in missions if mission["id"] in completed)
        levels_payload.append(
            {
                "id": level["id"],
                "name": level["name"],
                "tagline": level["tagline"],
                "icon": level["icon"],
                "accent": level["accent"],
                "total_missions": len(missions),
                "completed_missions": done,
                "percentage": round(done / len(missions) * 100) if missions else 0,
                "xp_earned": points_done,
                "xp_total": sum(mission["points"] for mission in missions),
                "unlocked": level_is_unlocked(index, data["levels"], completed),
                "modules": [data["modules"][i]["id"] for i in range(len(data["modules"])) if data["modules"][i]["level"] == level["id"]],
            }
        )

    modules_payload = []
    for module in data["modules"]:
        state = module_state(module, completed, data["levels"])
        earned = sum(data["missions"][mid]["points"] for mid in module["mission_ids"] if mid in completed)
        modules_payload.append(
            {
                "id": module["id"],
                "title": module["title"],
                "level": module["level"],
                "level_name": module["level_name"],
                "xp_reward": module["xp_reward"],
                "earned_xp": earned,
                **state,
            }
        )

    total_missions = len(data["order"])
    total_points = sum(m["points"] for m in data["missions"].values())
    mission_xp = sum(row["score"] for row in rows.values())
    dojo_points = dojo_xp(session_id)
    xp = mission_xp + dojo_points
    next_mission = next((mid for mid in data["order"] if mid not in completed), None)
    return {
        "session_id": session_id,
        "user_id": session.get("user_id"),
        "score": xp,
        "xp_earned": xp,
        "xp_missions": mission_xp,
        "xp_dojo": dojo_points,
        "xp_total": total_points + roadmap.total_xp(),
        "level": calculate_level_from_xp(xp),
        "completed_missions": len(completed),
        "completed_challenges": len(completed),
        "total_missions": total_missions,
        "total_challenges": total_missions,
        "overall_percentage": round(len(completed) / total_missions * 100, 1) if total_missions else 0,
        "next_mission": next_mission,
        "levels": levels_payload,
        "modules": modules_payload,
    }


# ---------------------------------------------------------------------------
# Routes : laboratoire
# ---------------------------------------------------------------------------


@app.get("/api/labs/files")
async def list_lab_files(session_id: str, working_dir: str | None = None, mission_id: str | None = None):
    target = mission_id or working_dir
    if not target:
        raise HTTPException(status_code=400, detail="mission_id requis")
    root = build_lab_dir(session_id, target)
    entries = []
    for current_root, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current_root)
        directory_names[:] = sorted(
            name for name in directory_names if not (current_path / name).is_symlink()
        )
        for name in directory_names:
            path = current_path / name
            entries.append({"path": path.relative_to(root).as_posix() + "/", "type": "directory"})
        for name in sorted(file_names):
            path = current_path / name
            if path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            size = path.stat().st_size
            entry = {"path": relative, "type": "file", "size": size}
            if size <= MAX_FILE_PREVIEW:
                entry["content"] = path.read_text(encoding="utf-8", errors="replace")
            entries.append(entry)
            if len(entries) >= 300:
                break
        if len(entries) >= 300:
            break
    entries.sort(key=lambda item: (item["path"].count("/"), item["path"]))
    return {"session_id": session_id, "mission_id": target, "working_dir": target, "entries": entries}


@app.post("/api/labs/run")
async def run_lab_command(payload: LabRunRequest):
    if not payload.command or not payload.command.strip():
        raise HTTPException(status_code=400, detail="Commande requise")
    lowered = payload.command.lower()
    if any(token in lowered for token in BLOCKED_PATTERNS):
        raise HTTPException(status_code=400, detail="Commande bloquée par le bac à sable du laboratoire.")
    target = payload.mission_id or payload.working_dir
    if not target:
        raise HTTPException(status_code=400, detail="mission_id requis")
    workdir = build_lab_dir(payload.session_id, target)
    try:
        process = run_in_lab(workdir, payload.command)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Commande interrompue : délai dépassé.") from exc
    return {
        "session_id": payload.session_id,
        "mission_id": target,
        "cwd": str(workdir),
        "exit_code": process.returncode,
        "stdout": process.stdout[-MAX_FILE_PREVIEW:],
        "stderr": process.stderr[-MAX_FILE_PREVIEW:],
    }


@app.post("/api/labs/reset")
async def reset_lab(payload: LabResetRequest):
    target = payload.mission_id or payload.working_dir
    if not target:
        raise HTTPException(status_code=400, detail="mission_id requis")
    validate_lab_segment(payload.session_id, "session_id")
    mission = require_mission(target)
    root = LAB_ROOT.resolve()
    session_dir = (root / payload.session_id).resolve()
    if not session_dir.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Répertoire de session invalide")
    directory = session_dir / target
    if directory.is_symlink():
        directory.unlink()
    elif directory.exists():
        shutil.rmtree(directory)
    seed_lab_workspace(directory, mission)
    return {
        "session_id": payload.session_id,
        "mission_id": target,
        "cwd": str(directory),
        "message": "Laboratoire réinitialisé.",
    }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
