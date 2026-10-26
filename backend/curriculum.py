"""Chargement, validation et sérialisation du curriculum SHELLFORGE.

Le contenu pédagogique est découpé par niveau dans ``backend/curriculum/level-*.json``.
Chaque mission contient :
- une partie cours (``lesson``) : sections, références de commandes, pièges ;
- une partie laboratoire (``lab``) : fichiers de départ, consignes, indices et
  ``checks`` exécutés côté serveur pour vérifier les preuves produites ;
- une note de remédiation (vision défensive / ingénierie).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

CURRICULUM_DIR = Path(__file__).resolve().parent / "curriculum"

CHECK_TYPES = {
    "file_exists",
    "dir_exists",
    "file_contains",
    "file_not_contains",
    "file_mode",
    "run",
}

MISSION_ID_RE = re.compile(r"^m\d{2}-\d{2}$")
DIFFICULTY_ORDER = {"easy": 1, "medium": 2, "hard": 3, "expert": 4}


def _fail(message: str) -> None:
    raise ValueError(f"Curriculum invalide : {message}")


def _validate_mission(mission: dict, module_id: str) -> None:
    mid = mission.get("id", "")
    if not MISSION_ID_RE.match(mid):
        _fail(f"identifiant de mission inattendu '{mid}'")
    for key in ("title", "brief", "difficulty", "points", "lesson", "lab"):
        if key not in mission:
            _fail(f"{mid} : champ '{key}' manquant")
    if mission["difficulty"] not in DIFFICULTY_ORDER:
        _fail(f"{mid} : difficulté '{mission['difficulty']}' inconnue")
    lesson = mission["lesson"]
    if not lesson.get("sections"):
        _fail(f"{mid} : aucune section pédagogique")
    if not mission["lab"].get("files"):
        _fail(f"{mid} : laboratoire sans fichier de départ")
    checks = mission["lab"].get("checks") or []
    if not checks:
        _fail(f"{mid} : aucun check de validation")
    seen = set()
    for check in checks:
        cid = check.get("id")
        if not cid or cid in seen:
            _fail(f"{mid} : identifiant de check manquant ou dupliqué")
        seen.add(cid)
        ctype = check.get("type")
        if ctype not in CHECK_TYPES:
            _fail(f"{mid}/{cid} : type de check '{ctype}' inconnu")
        if not check.get("label"):
            _fail(f"{mid}/{cid} : label manquant")
        if ctype in {"file_contains", "file_not_contains"}:
            try:
                re.compile(check["pattern"], re.MULTILINE)
            except re.error as exc:  # pragma: no cover - garde-fou auteur
                _fail(f"{mid}/{cid} : motif invalide ({exc})")
        if ctype == "run":
            if not check.get("cmd"):
                _fail(f"{mid}/{cid} : commande manquante")
            if not check.get("expect"):
                _fail(f"{mid}/{cid} : sortie attendue manquante")
            try:
                re.compile(check["expect"], re.MULTILINE)
            except re.error as exc:  # pragma: no cover
                _fail(f"{mid}/{cid} : attente invalide ({exc})")


@lru_cache(maxsize=1)
def load_curriculum() -> dict:
    """Charge et valide l'ensemble du curriculum (cache mémoire)."""
    levels = []
    modules = []
    missions: dict[str, dict] = {}
    order: list[str] = []

    paths = sorted(CURRICULUM_DIR.glob("level-*.json"))
    if not paths:
        raise ValueError("Aucun fichier de curriculum trouvé")

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        level_id = data["level"]
        level = {
            "id": level_id,
            "name": data["name"],
            "tagline": data.get("tagline", ""),
            "description": data.get("description", ""),
            "icon": data.get("icon", "◆"),
            "accent": data.get("accent", "#38bdf8"),
            "module_ids": [],
        }
        for module in data["modules"]:
            module_id = module["id"]
            module_missions = module.get("missions", [])
            if not module_missions:
                _fail(f"module {module_id} sans mission")
            module_record = {
                key: value
                for key, value in module.items()
                if key != "missions"
            }
            module_record.update(
                {
                    "level": level_id,
                    "level_name": level["name"],
                    "mission_ids": [],
                    "order_index": len(modules) + 1,
                }
            )
            module_record.setdefault("difficulty", "medium")
            module_record.setdefault("category", level["name"].lower())
            module_record.setdefault("xp_reward", 0)
            for mission in module_missions:
                _validate_mission(mission, module_id)
                if mission["id"] in missions:
                    _fail(f"mission dupliquée {mission['id']}")
                mission_record = dict(mission)
                mission_record.update(
                    {
                        "module_id": module_id,
                        "module_title": module_record["title"],
                        "level": level_id,
                        "level_name": level["name"],
                        "category": module_record["category"],
                        "order_index": len(order) + 1,
                    }
                )
                mission_record.setdefault("tags", [])
                mission_record.setdefault("objectives", [])
                missions[mission["id"]] = mission_record
                module_record["mission_ids"].append(mission["id"])
                order.append(mission["id"])
            module_record["xp_reward"] = module_record["xp_reward"] or sum(
                missions[mid]["points"] for mid in module_record["mission_ids"]
            )
            modules.append(module_record)
            level["module_ids"].append(module_id)

        level["mission_ids"] = [
            mid for module_id in level["module_ids"] for mid in _module(modules, module_id)["mission_ids"]
        ]
        levels.append(level)

    return {
        "levels": levels,
        "modules": modules,
        "missions": missions,
        "order": order,
    }


def _module(modules: list[dict], module_id: str) -> dict:
    for module in modules:
        if module["id"] == module_id:
            return module
    raise KeyError(module_id)


def get_mission(mission_id: str) -> dict | None:
    return load_curriculum()["missions"].get(mission_id)


def get_module(module_id: str) -> dict | None:
    for module in load_curriculum()["modules"]:
        if module["id"] == module_id:
            return module
    return None


def get_level(level_id: int) -> dict | None:
    for level in load_curriculum()["levels"]:
        if level["id"] == level_id:
            return level
    return None


def ordered_missions() -> list[dict]:
    data = load_curriculum()
    return [data["missions"][mid] for mid in data["order"]]


def next_mission(mission_id: str) -> dict | None:
    data = load_curriculum()
    try:
        index = data["order"].index(mission_id)
    except ValueError:
        return None
    if index + 1 >= len(data["order"]):
        return None
    return data["missions"][data["order"][index + 1]]


def mission_summary(mission: dict) -> dict:
    """Vue allégée pour les listes (aucune solution, aucun secret)."""
    return {
        "id": mission["id"],
        "module_id": mission["module_id"],
        "module_title": mission["module_title"],
        "level": mission["level"],
        "level_name": mission["level_name"],
        "title": mission["title"],
        "brief": mission["brief"],
        "difficulty": mission["difficulty"],
        "points": mission["points"],
        "tags": mission.get("tags", []),
        "objectives": mission.get("objectives", []),
        "section_count": len(mission["lesson"].get("sections", [])),
        "check_count": len(mission["lab"].get("checks", [])),
        "estimated_minutes": mission.get("estimated_minutes", 25),
    }


def mission_detail(mission: dict) -> dict:
    """Vue complète pour la page mission : cours + consignes + checks publics."""
    lab = mission["lab"]
    payload = mission_summary(mission)
    payload.update(
        {
            "lesson": mission["lesson"],
            "remediation": mission.get("remediation", ""),
            "lab": {
                "task": lab.get("task", ""),
                "steps": lab.get("steps", []),
                "hints": lab.get("hints", []),
                "files": sorted(lab.get("files", {}).keys()),
                "dirs": sorted(lab.get("dirs", [])),
                "checks": [
                    {"id": check["id"], "label": check["label"]}
                    for check in lab.get("checks", [])
                ],
                "verify_hint": lab.get("verify_hint", ""),
            },
        }
    )
    return payload


def module_summary(module: dict) -> dict:
    data = load_curriculum()
    return {
        "id": module["id"],
        "title": module["title"],
        "description": module.get("description", ""),
        "level": module["level"],
        "level_name": module["level_name"],
        "category": module["category"],
        "difficulty": module["difficulty"],
        "xp_reward": module["xp_reward"],
        "order_index": module["order_index"],
        "missions": [mission_summary(data["missions"][mid]) for mid in module["mission_ids"]],
    }
