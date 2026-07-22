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


def test_pkg002_status_migration_preserves_existing_runs_and_supports_new_statuses(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "pkg002_statuses.db"
    _run_alembic(db_path, "upgrade", "b7e4c2d9a105")

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        session.execute(
            text(
                "INSERT INTO clients (client_id, display_name, id_number) "
                "VALUES (1, 'Migration Client', 'migration-client')"
            )
        )
        session.execute(
            text(
                "INSERT INTO fixation_runs "
                "(id, fixation_run_id, client_id, calculation_version, status, is_latest) "
                "VALUES (1, 'existing-run', 1, 'v1', 'validation_failed', 1)"
            )
        )
        session.commit()

    _run_alembic(db_path, "upgrade", "head")

    with Session(create_engine(f"sqlite:///{db_path.as_posix()}")) as session:
        assert session.execute(
            text("SELECT status FROM fixation_runs WHERE id = 1")
        ).scalar_one() == "validation_failed"
        session.execute(
            text(
                "INSERT INTO fixation_runs "
                "(fixation_run_id, client_id, calculation_version, status, is_latest) "
                "VALUES ('failed-run', 1, 'v2', 'calculation_failed', 0), "
                "('unsupported-run', 1, 'v2', 'unsupported_calculation', 0)"
            )
        )
        session.commit()

    downgrade = _run_alembic(db_path, "downgrade", "b7e4c2d9a105", check=False)
    assert downgrade.returncode != 0
    assert "Cannot downgrade while PKG-002 calculation failure statuses are present" in (
        downgrade.stdout + downgrade.stderr
    )


def test_pkg003_manifest_migration_preserves_legacy_runs_and_refuses_destructive_downgrade(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "pkg003_manifests.db"
    _run_alembic(db_path, "upgrade", "c2f8a4d1e706")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        session.execute(
            text(
                "INSERT INTO clients (client_id, display_name, id_number) "
                "VALUES (1, 'Manifest Migration Client', 'manifest-migration-client')"
            )
        )
        session.execute(
            text(
                "INSERT INTO fixation_runs "
                "(id, fixation_run_id, client_id, calculation_version, status, is_latest) "
                "VALUES (1, 'legacy-run', 1, 'legacy-v1', 'validation_failed', 1)"
            )
        )
        session.commit()

    _run_alembic(db_path, "upgrade", "head")
    with Session(engine) as session:
        assert session.execute(
            text(
                "SELECT COUNT(*) FROM fixation_dependency_manifests "
                "WHERE fixation_run_id = 1"
            )
        ).scalar_one() == 0
        session.execute(
            text(
                "INSERT INTO fixation_dependency_manifests "
                "(fixation_dependency_manifest_id, fixation_run_id, client_id, "
                "manifest_schema_version, fingerprint_algorithm_version, "
                "manifest_fingerprint, manifest_payload) "
                "VALUES ('manifest-1', 1, 1, 'manifest-v1', 'sha256-v1', NULL, '{}')"
            )
        )
        session.commit()

    downgrade = _run_alembic(db_path, "downgrade", "c2f8a4d1e706", check=False)
    assert downgrade.returncode != 0
    assert "Cannot downgrade while PKG-003 dependency manifests are present" in (
        downgrade.stdout + downgrade.stderr
    )

    with Session(engine) as session:
        assert session.execute(
            text("SELECT COUNT(*) FROM fixation_dependency_manifests")
        ).scalar_one() == 1
