#!/usr/bin/env python3
"""Auto-contrôle du curriculum SHELLFORGE.

Pour chaque mission : crée une session jetable, applique la solution de référence
dans le laboratoire, puis exécute les contrôles de preuves. Un échec signale une
incohérence entre la mission, sa solution et ses vérifications.

Usage::

    python3 scripts/selfcheck_curriculum.py            # toutes les missions
    python3 scripts/selfcheck_curriculum.py m01-02 m03-01
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

TMP = Path(tempfile.mkdtemp(prefix="shellforge-selfcheck-"))
os.environ.setdefault("SHELLFORGE_DB_PATH", str(TMP / "selfcheck.db"))
os.environ.setdefault("SHELLFORGE_LAB_ROOT", str(TMP / "labs"))

import curriculum  # noqa: E402
import main  # noqa: E402


def check_mission(mission: dict) -> tuple[bool, list[str]]:
    session = f"selfcheck-{mission['id']}"
    workdir = main.build_lab_dir(session, mission["id"])
    solution = mission["lab"].get("solution", "")
    if solution.strip():
        process = main.run_in_lab(workdir, solution, timeout=60)
        if process.returncode != 0:
            return False, [f"solution en échec (code {process.returncode}) : {process.stderr.strip()[:300]}"]
    result = main.verify_mission(workdir, mission)
    failures = [
        f"{item['id']} : {item['detail']}" for item in result["checks"] if not item["passed"]
    ]
    return result["passed"], failures


def main_entry(argv: list[str]) -> int:
    data = curriculum.load_curriculum()
    selected = argv or data["order"]
    failures = 0
    for mission_id in selected:
        mission = data["missions"].get(mission_id)
        if not mission:
            print(f"[??] mission inconnue {mission_id}")
            failures += 1
            continue
        ok, details = check_mission(mission)
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {mission_id} - {mission['title']}")
        for detail in details:
            print(f"        - {detail}")
        failures += 0 if ok else 1
    print(f"\n{len(selected) - failures}/{len(selected)} missions conformes")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main_entry(sys.argv[1:]))
