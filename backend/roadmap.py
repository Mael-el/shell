"""Plan d'entraînement « CyberDev Dojo » : 12 semaines, 6 niveaux, 24 tâches.

Le contenu vit dans ``backend/curriculum/roadmap-12-semaines.json``. Les tâches sont
des exercices externes (OverTheWire, Exercism, TryHackMe, PortSwigger…) que
l'apprenant coche lui-même ; l'application suit l'avancement, attribue l'XP une
seule fois par tâche et rappelle la méthode de travail sans IA.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROADMAP_PATH = Path(__file__).resolve().parent / "curriculum" / "roadmap-12-semaines.json"

TASK_ID_RE = re.compile(r"^d[1-6]-t[1-4]$")


def _fail(message: str) -> None:
    raise ValueError(f"Roadmap invalide : {message}")


def _validate(data: dict) -> None:
    levels = data.get("levels") or []
    if len(levels) != 6:
        _fail(f"6 niveaux attendus, {len(levels)} trouvés")
    seen: set[str] = set()
    for level in levels:
        if not level.get("id") or not level.get("name") or not level.get("weeks"):
            _fail("niveau sans id, nom ou période")
        tasks = level.get("tasks") or []
        if not tasks:
            _fail(f"niveau {level['id']} sans tâche")
        for task in tasks:
            tid = task.get("id", "")
            if not TASK_ID_RE.match(tid):
                _fail(f"identifiant de tâche inattendu '{tid}'")
            if tid in seen:
                _fail(f"tâche dupliquée {tid}")
            seen.add(tid)
            for key in ("label", "track", "xp"):
                if key not in task:
                    _fail(f"{tid} : champ '{key}' manquant")
            if not isinstance(task["xp"], int) or task["xp"] <= 0:
                _fail(f"{tid} : XP invalide")
            resource = task.get("resource")
            if resource and not str(resource.get("url", "")).startswith("https://"):
                _fail(f"{tid} : ressource sans URL HTTPS")
    if len(seen) != 24:
        _fail(f"24 tâches attendues, {len(seen)} trouvées")


@lru_cache(maxsize=1)
def load_roadmap() -> dict:
    data = json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))
    _validate(data)
    tasks: dict[str, dict] = {}
    for level in data["levels"]:
        for task in level["tasks"]:
            record = dict(task)
            record.update({"level_id": level["id"], "level_name": level["name"], "weeks": level["weeks"]})
            tasks[task["id"]] = record
    return {**data, "tasks": tasks, "task_ids": list(tasks)}


def get_task(task_id: str) -> dict | None:
    return load_roadmap()["tasks"].get(task_id)


def total_xp() -> int:
    return sum(task["xp"] for task in load_roadmap()["tasks"].values())


def public_payload(completed: set[str] | None = None, scores: dict[str, int] | None = None) -> dict:
    """Vue consommée par le front : tâches, avancement, badges et ressources."""
    data = load_roadmap()
    completed = completed or set()
    scores = scores or {}
    levels_payload = []
    for level in data["levels"]:
        tasks = [
            {
                **{key: task[key] for key in ("id", "label", "track", "xp", "detail")},
                "resource": task.get("resource"),
                "done": task["id"] in completed,
            }
            for task in level["tasks"]
        ]
        done = sum(1 for task in tasks if task["done"])
        levels_payload.append(
            {
                "id": level["id"],
                "name": level["name"],
                "weeks": level["weeks"],
                "accent": level["accent"],
                "goal": level["goal"],
                "tasks": tasks,
                "total_tasks": len(tasks),
                "completed_tasks": done,
                "percentage": round(done / len(tasks) * 100) if tasks else 0,
                "xp_total": sum(task["xp"] for task in level["tasks"]),
                "xp_earned": sum(task["xp"] for task in level["tasks"] if task["id"] in completed),
            }
        )
    total_tasks = len(data["tasks"])
    total_done = sum(1 for tid in data["tasks"] if tid in completed)
    xp_earned = sum(scores.get(tid, 0) for tid in data["tasks"])
    return {
        "title": data["title"],
        "subtitle": data["subtitle"],
        "principle": data["principle"],
        "total_tasks": total_tasks,
        "completed_tasks": total_done,
        "percentage": round(total_done / total_tasks * 100) if total_tasks else 0,
        "xp_total": total_xp(),
        "xp_earned": xp_earned,
        "weeks": 12,
        "badges": build_badges(levels_payload, completed),
        "levels": levels_payload,
        "resources": data["resources"],
    }


def build_badges(levels: list[dict], completed: set[str]) -> list[dict]:
    """Badges sobres : un par niveau terminé, plus deux paliers d'ensemble."""
    badges = [
        {
            "id": level["id"],
            "label": f"{level['name']} terminé",
            "icon": "◆",
            "earned": level["percentage"] == 100,
            "detail": f"{level['completed_tasks']}/{level['total_tasks']} tâches",
        }
        for level in levels
    ]
    total = sum(level["total_tasks"] for level in levels) or 1
    done = sum(level["completed_tasks"] for level in levels)
    badges.append(
        {
            "id": "demi",
            "label": "Mi-parcours (12 tâches)",
            "icon": "▲",
            "earned": done >= total / 2,
            "detail": f"{done}/{total} tâches",
        }
    )
    badges.append(
        {
            "id": "dojo",
            "label": "Dojo accompli (24 tâches)",
            "icon": "★",
            "earned": done == total,
            "detail": f"{done}/{total} tâches",
        }
    )
    return badges
