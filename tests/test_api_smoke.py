import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import main


def _prepare_env(tmp_path):
    main.DATABASE_DIR = tmp_path
    main.DB_PATH = tmp_path / "shellforge.db"
    main.LAB_ROOT = tmp_path / "labs"
    main.init_db()
    return TestClient(main.app)


def _session(client, user="pytest-user"):
    response = client.post("/api/sessions", json={"user_id": user})
    assert response.status_code == 200
    return response.json()["session_id"]


def test_curriculum_is_exposed(tmp_path):
    client = _prepare_env(tmp_path)

    levels = client.get("/api/levels").json()["levels"]
    modules = client.get("/api/modules").json()["modules"]

    assert len(levels) == 7
    assert sum(item["total_missions"] for item in levels) == 36
    assert len(modules) == 18
    assert all(module["missions"] for module in modules)
    assert levels[0]["unlocked"] is True
    assert levels[1]["unlocked"] is False

    first = client.get("/api/missions/m01-01").json()
    assert first["lesson"]["sections"]
    assert first["lab"]["checks"]
    assert "solution" not in first["lab"]


def test_lab_is_seeded_and_reset_restores_starter_files(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    files = client.get("/api/labs/files", params={"session_id": session_id, "working_dir": "m02-01"})
    assert files.status_code == 200
    entries = {entry["path"]: entry for entry in files.json()["entries"]}
    assert "srv/var/log/auth.log" in entries
    assert "Failed password" in entries["srv/var/log/auth.log"]["content"]

    write = client.post(
        "/api/labs/run",
        json={"session_id": session_id, "command": "printf 'trace\\n' > preuve.txt", "working_dir": "m02-01"},
    )
    assert write.status_code == 200

    reset = client.post("/api/labs/reset", json={"session_id": session_id, "working_dir": "m02-01"})
    assert reset.status_code == 200

    refreshed = client.get("/api/labs/files", params={"session_id": session_id, "working_dir": "m02-01"})
    paths = {entry["path"] for entry in refreshed.json()["entries"]}
    assert "srv/var/log/auth.log" in paths
    assert "preuve.txt" not in paths


def test_mission_verification_awards_points_once(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)
    mission = main.curriculum.get_mission("m01-01")

    run = client.post(
        "/api/labs/run",
        json={"session_id": session_id, "command": mission["lab"]["solution"], "mission_id": "m01-01"},
    )
    assert run.status_code == 200
    assert run.json()["exit_code"] == 0

    verification = client.post("/api/missions/m01-01/verify", json={"session_id": session_id})
    assert verification.status_code == 200
    payload = verification.json()
    assert payload["passed"] is True, payload["checks"]
    assert payload["score_awarded"] == mission["points"]

    again = client.post("/api/missions/m01-01/verify", json={"session_id": session_id}).json()
    assert again["passed"] is True
    assert again["score_awarded"] == 0
    assert again["already_completed"] is True

    summary = client.get(f"/api/sessions/{session_id}/summary").json()
    assert summary["completed_missions"] == 1
    assert summary["xp_earned"] == mission["points"]


def test_verification_reports_missing_evidence(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    response = client.post("/api/missions/m01-01/verify", json={"session_id": session_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["passed"] is False
    assert payload["passed_count"] < payload["total_count"]
    assert any(not check["passed"] for check in payload["checks"])


def test_lesson_progress_is_tracked(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    response = client.post(
        "/api/learning/progress",
        json={"session_id": session_id, "mission_id": "m01-01", "section_id": "concept", "status": "completed"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_sections"] == 1
    assert payload["progress_percent"] > 0

    invalid = client.post(
        "/api/learning/progress",
        json={"session_id": session_id, "mission_id": "m01-01", "section_id": "inconnue"},
    )
    assert invalid.status_code == 400


def test_lab_rejects_path_traversal_and_symlink_escape(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    traversal = client.get("/api/labs/files", params={"session_id": session_id, "working_dir": ".."})
    assert traversal.status_code == 400

    mission_dir = main.LAB_ROOT / session_id
    mission_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("keep me", encoding="utf-8")
    (mission_dir / "m01-01").symlink_to(outside, target_is_directory=True)
    try:
        escape = client.get("/api/labs/files", params={"session_id": session_id, "working_dir": "m01-01"})
        assert escape.status_code == 400
        assert (outside / "secret.txt").read_text(encoding="utf-8") == "keep me"
    finally:
        (mission_dir / "m01-01").unlink()
        (mission_dir).rmdir()


def test_dangerous_command_is_blocked(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    response = client.post(
        "/api/labs/run",
        json={"session_id": session_id, "command": "rm -rf / --no-preserve-root", "working_dir": "m01-01"},
    )

    assert response.status_code == 400


def test_preview_origin_is_allowed_by_cors(tmp_path):
    client = _prepare_env(tmp_path)

    response = client.options(
        "/api/levels",
        headers={
            "Origin": "https://5173-demo.e2b.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://5173-demo.e2b.app"


def test_session_lookup_returns_progress_or_404(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    found = client.get(f"/api/sessions/{session_id}")
    assert found.status_code == 200
    payload = found.json()
    assert payload["session_id"] == session_id
    assert payload["user_id"] == "pytest-user"
    assert payload["score"] == 0
    assert payload["level"] == 1
    assert payload["completed_missions"] == 0
    assert payload["started_at"]

    missing = client.get("/api/sessions/session-inexistante")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Session introuvable"


def test_dojo_roadmap_exposes_the_twelve_week_plan(tmp_path):
    client = _prepare_env(tmp_path)

    payload = client.get("/api/roadmap").json()
    assert len(payload["levels"]) == 6
    assert payload["total_tasks"] == 24
    assert payload["weeks"] == 12
    assert payload["xp_total"] == 1610
    assert payload["completed_tasks"] == 0
    assert all(len(level["tasks"]) == 4 for level in payload["levels"])
    assert all(task["resource"]["url"].startswith("https://") for task in payload["levels"][0]["tasks"])
    assert payload["resources"]["recommended"][0]["name"] == "OverTheWire Bandit"
    assert len(payload["resources"]["categories"]) == 4


def test_dojo_progress_is_tracked_once_per_task(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    first = client.post(
        "/api/roadmap/progress", json={"session_id": session_id, "task_id": "d1-t1"}
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["done"] is True
    assert payload["score_awarded"] == 60
    assert payload["completed_tasks"] == 1
    assert payload["xp_earned"] == 60
    assert payload["levels"][0]["completed_tasks"] == 1

    again = client.post(
        "/api/roadmap/progress", json={"session_id": session_id, "task_id": "d1-t1"}
    ).json()
    assert again["completed_tasks"] == 1
    assert again["xp_earned"] == 60, "l'XP ne doit pas être attribué deux fois"

    undone = client.post(
        "/api/roadmap/progress",
        json={"session_id": session_id, "task_id": "d1-t1", "done": False},
    ).json()
    assert undone["done"] is False
    assert undone["completed_tasks"] == 0
    assert undone["xp_earned"] == 0

    stored = client.get("/api/roadmap", params={"session_id": session_id}).json()
    assert stored["completed_tasks"] == 0


def test_dojo_rejects_unknown_task_and_session(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    assert client.post(
        "/api/roadmap/progress",
        json={"session_id": session_id, "task_id": "d9-t9"},
    ).status_code == 404
    assert client.post(
        "/api/roadmap/progress",
        json={"session_id": "session-absente", "task_id": "d1-t1"},
    ).status_code == 404
    assert client.get("/api/roadmap", params={"session_id": "session-absente"}).status_code == 404
    assert client.get("/api/resources").json()["safety"]


def test_resource_catalogue_carries_verified_metadata(tmp_path):
    client = _prepare_env(tmp_path)

    payload = client.get("/api/resources").json()
    categories = {category["id"]: category for category in payload["categories"]}
    assert set(categories) == {"labs", "code", "selfhost", "games"}

    items = [item for category in payload["categories"] for item in category["items"]]
    assert all(item["access"] in {"gratuit", "freemium", "payant"} for item in items)
    assert all(item["provider"] for item in items)

    # Play with Docker a fermé en mars 2026 : il ne doit plus figurer au catalogue.
    urls = {item["url"] for item in items}
    assert not any("play-with-docker" in url for url in urls)

    juice = next(item for item in items if item["name"] == "OWASP Juice Shop")
    assert juice["verified"]["github"]["stars"] > 1000
    assert juice["verified"]["github"]["license"] == "MIT"
    assert juice["verified"]["checked_at"]

    verification = payload["verification"]
    assert verification["counts"]["github_checked"] >= 10
    assert verification["checked_at"]


def test_dojo_xp_counts_towards_the_session_score(tmp_path):
    client = _prepare_env(tmp_path)
    session_id = _session(client)

    client.post("/api/roadmap/progress", json={"session_id": session_id, "task_id": "d1-t1"})
    summary = client.get(f"/api/sessions/{session_id}/summary").json()
    assert summary["xp_dojo"] == 60
    assert summary["xp_missions"] == 0
    assert summary["score"] == 60
    assert summary["level"] == 1

    # Une mission validée ne doit pas écraser l'XP du dojo.
    mission = main.curriculum.get_mission("m01-01")
    client.post(
        "/api/labs/run",
        json={"session_id": session_id, "command": mission["lab"]["solution"], "mission_id": "m01-01"},
    )
    client.post("/api/missions/m01-01/verify", json={"session_id": session_id})
    summary = client.get(f"/api/sessions/{session_id}/summary").json()
    assert summary["xp_missions"] == mission["points"]
    assert summary["xp_dojo"] == 60
    assert summary["score"] == mission["points"] + 60
    assert client.get(f"/api/sessions/{session_id}").json()["xp_dojo"] == 60
