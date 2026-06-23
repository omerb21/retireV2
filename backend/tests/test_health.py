from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app


client = TestClient(app)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _upgrade_sqlite_database(db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_clients_endpoint_allows_local_vite_origin(tmp_path: Path) -> None:
    db_path = tmp_path / "cors.db"
    _upgrade_sqlite_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get(
            "/api/clients",
            headers={"Origin": "http://127.0.0.1:5173"},
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    finally:
        app.dependency_overrides.clear()
