from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess


BACKEND = Path(__file__).resolve().parents[1]
REVISION = "95222c79dce8"
PARENT = "e4a7c3d9b802"


def _run(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        ["alembic", *args],
        cwd=BACKEND,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )


def test_pkg009_is_the_single_additive_head() -> None:
    result = _run("sqlite:///:memory:", "heads")
    assert result.stdout.strip() == f"{REVISION} (head)"


def test_pkg009_sqlite_upgrade_downgrade_reupgrade_is_bounded(tmp_path: Path) -> None:
    database = tmp_path / "pkg009-migration.db"
    url = f"sqlite:///{database.as_posix()}"
    _run(url, "upgrade", PARENT)
    with sqlite3.connect(database) as connection:
        predecessor_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "m03_review_revisions" in predecessor_tables
        assert not any(name.startswith("m04_") for name in predecessor_tables)

    _run(url, "upgrade", REVISION)
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "m04_classification_subjects",
            "m04_classification_revisions",
            "m04_component_decisions",
        }.issubset(tables)
        assert connection.execute(
            "SELECT COUNT(*) FROM m04_classification_revisions"
        ).fetchone()[0] == 0
        revision_indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list('m04_classification_revisions')"
            )
        }
        assert "ix_m04_revision_client_target" in revision_indexes
        revision_ddl = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='m04_classification_revisions'"
        ).fetchone()[0]
        assert "uq_m04_revision_predecessor_child" in revision_ddl
        assert "uq_m04_revision_subject_sequence" in revision_ddl

    _run(url, "downgrade", PARENT)
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "m03_review_revisions" in tables
        assert not any(name.startswith("m04_") for name in tables)

    _run(url, "upgrade", REVISION)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == REVISION


def test_pkg009_postgresql_offline_ddl_is_supported() -> None:
    result = _run(
        "postgresql://ddl-only.invalid/retirement",
        "upgrade",
        f"{PARENT}:{REVISION}",
        "--sql",
    )
    ddl = result.stdout.lower()
    assert "create table m04_classification_subjects" in ddl
    assert "create table m04_classification_revisions" in ddl
    assert "create table m04_component_decisions" in ddl
    assert "json" in ddl
