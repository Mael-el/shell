import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

import main


def _prepare_db(tmp_path):
    main.DATABASE_DIR = tmp_path
    main.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    main.DB_PATH = tmp_path / 'shellforge.db'
    main.init_db()
    return main.DB_PATH


def test_modules_are_exposed(tmp_path):
    _prepare_db(tmp_path)
    client = TestClient(main.app)

    response = client.get('/api/modules')

    assert response.status_code == 200
    payload = response.json()
    assert 'modules' in payload
    assert len(payload['modules']) > 0


def test_session_and_lab_execution_work(tmp_path):
    _prepare_db(tmp_path)
    client = TestClient(main.app)

    session_response = client.post('/api/sessions', json={'user_id': 'pytest-user'})
    assert session_response.status_code == 200
    session_id = session_response.json()['session_id']

    lab_response = client.post(
        '/api/labs/run',
        json={'session_id': session_id, 'command': "printf 'hello\\n'", 'working_dir': 'pytest-run'}
    )

    assert lab_response.status_code == 200
    assert lab_response.json()['stdout'].strip() == 'hello'


def test_mission_lab_has_starter_files_and_reset_restores_them(tmp_path):
    _prepare_db(tmp_path)
    client = TestClient(main.app)
    session_response = client.post('/api/sessions', json={'user_id': 'pytest-user'})
    session_id = session_response.json()['session_id']

    files_response = client.get(
        '/api/labs/files',
        params={'session_id': session_id, 'working_dir': 'c19'},
    )

    assert files_response.status_code == 200
    entries = {entry['path']: entry for entry in files_response.json()['entries']}
    assert 'logs/' in entries
    assert 'logs/app.log' in entries
    assert 'ERROR fichier introuvable' in entries['logs/app.log']['content']

    write_response = client.post(
        '/api/labs/run',
        json={
            'session_id': session_id,
            'command': "printf 'learner data\\n' > logs/learner.log",
            'working_dir': 'c19',
        },
    )
    assert write_response.status_code == 200

    reset_response = client.post(
        '/api/labs/reset',
        json={'session_id': session_id, 'working_dir': 'c19'},
    )
    assert reset_response.status_code == 200

    refreshed_files = client.get(
        '/api/labs/files',
        params={'session_id': session_id, 'working_dir': 'c19'},
    )
    refreshed_paths = {entry['path'] for entry in refreshed_files.json()['entries']}
    assert 'logs/app.log' in refreshed_paths
    assert 'logs/learner.log' not in refreshed_paths


def test_lab_workspace_rejects_path_traversal(tmp_path):
    _prepare_db(tmp_path)
    client = TestClient(main.app)

    response = client.get(
        '/api/labs/files',
        params={'session_id': 'safe-session', 'working_dir': '..'},
    )

    assert response.status_code == 400


def test_lab_file_browser_does_not_follow_workspace_symlinks(tmp_path):
    _prepare_db(tmp_path)
    client = TestClient(main.app)
    session_response = client.post('/api/sessions', json={'user_id': 'pytest-user'})
    session_id = session_response.json()['session_id']
    session_root = Path(main.tempfile.gettempdir()) / 'shellforge-labs' / session_id
    outside_directory = tmp_path / 'outside'
    outside_directory.mkdir()
    protected_file = outside_directory / 'protected.txt'
    protected_file.write_text('keep me', encoding='utf-8')
    session_root.mkdir(parents=True, exist_ok=True)
    (session_root / 'c30').symlink_to(outside_directory, target_is_directory=True)

    try:
        response = client.get(
            '/api/labs/files',
            params={'session_id': session_id, 'working_dir': 'c30'},
        )
        assert response.status_code == 400
        assert protected_file.read_text(encoding='utf-8') == 'keep me'
    finally:
        (session_root / 'c30').unlink()
        session_root.rmdir()


def test_preview_origin_is_allowed_by_cors(tmp_path):
    _prepare_db(tmp_path)
    client = TestClient(main.app)

    response = client.options(
        '/api/modules',
        headers={
            'Origin': 'https://5173-demo.e2b.app',
            'Access-Control-Request-Method': 'GET',
        },
    )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'https://5173-demo.e2b.app'
