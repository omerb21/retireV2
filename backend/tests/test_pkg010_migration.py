from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess


BACKEND = Path(__file__).resolve().parents[1]
REVISION = "a4c9e2f7b106"
PARENT = "95222c79dce8"
TABLES = {
    "m05_ledger_subjects",
    "m05_candidate_links",
    "m05_ledger_revisions",
    "m05_ledger_values",
    "m05_adjustment_evidence",
}


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


def _tables(database: Path) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def test_pkg010_is_the_single_additive_head() -> None:
    result = _run("sqlite:///:memory:", "heads")
    assert result.stdout.strip() == f"{REVISION} (head)"


def test_pkg010_sqlite_upgrade_downgrade_reupgrade_is_bounded(tmp_path: Path) -> None:
    database = tmp_path / "pkg010-migration.db"
    url = f"sqlite:///{database.as_posix()}"
    _run(url, "upgrade", PARENT)
    assert TABLES.isdisjoint(_tables(database))

    _run(url, "upgrade", REVISION)
    assert TABLES.issubset(_tables(database))
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM m05_ledger_revisions"
        ).fetchone()[0] == 0
        revision_ddl = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='m05_ledger_revisions'"
        ).fetchone()[0]
        values_ddl = connection.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='m05_ledger_values'"
        ).fetchone()[0]
        assert "NUMERIC(20, 2)" in revision_ddl
        assert "NUMERIC(20, 2)" in values_ddl
        for constraint in (
            "uq_m05_revision_predecessor_child",
            "uq_m05_revision_subject_sequence",
            "fk_m05_revision_candidate_subject",
        ):
            assert constraint in revision_ddl
        assert "uq_m05_value_revision_identity" in values_ddl
        assert "fk_m05_value_revision_subject" in values_ddl

    _run(url, "downgrade", PARENT)
    assert TABLES.isdisjoint(_tables(database))
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == PARENT

    _run(url, "upgrade", REVISION)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == REVISION


def test_pkg010_sqlite_offline_upgrade_is_query_independent() -> None:
    result = _run(
        "sqlite:///:memory:",
        "upgrade",
        f"{PARENT}:{REVISION}",
        "--sql",
    )
    ddl = result.stdout.lower()
    assert all(f"create table {table}" in ddl for table in TABLES)
    assert "select " not in ddl


def test_pkg010_postgresql_offline_upgrade_and_downgrade_are_supported() -> None:
    url = "postgresql://ddl-only.invalid/retirement"
    upgrade = _run(url, "upgrade", f"{PARENT}:{REVISION}", "--sql").stdout.lower()
    assert all(f"create table {table}" in upgrade for table in TABLES)
    assert "numeric(20, 2)" in upgrade
    assert "select " not in upgrade

    downgrade = _run(url, "downgrade", f"{REVISION}:{PARENT}", "--sql").stdout.lower()
    assert all(f"drop table {table}" in downgrade for table in TABLES)
    assert "select " not in downgrade
