from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_alembic(db_path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return subprocess.run(
        ["alembic", *args],
        cwd=_backend_root(),
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )


def test_stage_a_blocks_non_digit_client_id_preflight(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_a_non_digit.db"
    _run_alembic(db_path, "upgrade", "a2f36c3147d2")

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        session.execute(
            text(
                """
                INSERT INTO clients (client_id, display_name, status)
                VALUES ('123abc', 'Bad Client', 'active')
                """
            )
        )
        session.commit()

    result = _run_alembic(db_path, "upgrade", "eb25e18b9fcd", check=False)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "values containing non-digit characters" in output


def test_stage_a_blocks_cast_changed_and_collision_client_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_a_collision.db"
    _run_alembic(db_path, "upgrade", "a2f36c3147d2")

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        session.execute(
            text(
                """
                INSERT INTO clients (client_id, display_name, status)
                VALUES ('1', 'Client 1', 'active'), ('01', 'Client 01', 'active')
                """
            )
        )
        session.commit()

    result = _run_alembic(db_path, "upgrade", "eb25e18b9fcd", check=False)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "would change under CAST(... AS INTEGER)" in output
    assert "colliding normalized integer values" in output


def test_stage_a_audits_planned_id_number_backfill(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_a_planned_id_number.db"
    _run_alembic(db_path, "upgrade", "a2f36c3147d2")

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        session.execute(
            text(
                """
                INSERT INTO clients (client_id, display_name, status)
                VALUES ('', 'Empty Id Client', 'active')
                """
            )
        )
        session.commit()

    result = _run_alembic(db_path, "upgrade", "eb25e18b9fcd", check=False)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "planned clients.id_number backfill from clients.client_id" in output


def test_stage_a_passes_for_valid_numeric_client_ids(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_a_valid.db"
    _run_alembic(db_path, "upgrade", "a2f36c3147d2")

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        session.execute(
            text(
                """
                INSERT INTO clients (client_id, display_name, status)
                VALUES ('1', 'Client 1', 'active'), ('2', 'Client 2', 'active')
                """
            )
        )
        session.commit()

    result = _run_alembic(db_path, "upgrade", "eb25e18b9fcd")
    assert result.returncode == 0


def test_clean_db_downgrade_upgrade_path_works(tmp_path: Path) -> None:
    db_path = tmp_path / "stage_clean_path.db"
    _run_alembic(db_path, "upgrade", "head")
    result = _run_alembic(db_path, "downgrade", "base")
    assert result.returncode == 0
    result = _run_alembic(db_path, "upgrade", "head")
    assert result.returncode == 0
