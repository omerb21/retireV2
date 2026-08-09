from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess


BACKEND = Path(__file__).resolve().parents[1]
REVISION = "d7e3a6b9c204"
PARENT = "a4c9e2f7b106"
TABLES = {
    "m06_conversion_subjects",
    "m06_conversion_revisions",
    "m06_coefficient_evidence",
    "m06_calculation_manifests",
    "m06_warning_dispositions",
}


def run(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["alembic", *args],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url},
        text=True,
        capture_output=True,
        check=True,
    )


def tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def test_pkg011_is_single_additive_head() -> None:
    assert run("sqlite:///:memory:", "heads").stdout.strip() == f"{REVISION} (head)"


def test_pkg011_upgrade_downgrade_reupgrade_is_bounded(tmp_path: Path) -> None:
    database = tmp_path / "pkg011.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", PARENT)
    assert TABLES.isdisjoint(tables(database))
    run(url, "upgrade", REVISION)
    assert TABLES.issubset(tables(database))
    with sqlite3.connect(database) as connection:
        ddl = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='m06_conversion_revisions'"
        ).fetchone()[0]
        assert (
            "uq_m06_revision_predecessor_child" in ddl
            and "uq_m06_revision_subject_sequence" in ddl
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM m06_conversion_revisions"
            ).fetchone()[0]
            == 0
        )
    run(url, "downgrade", PARENT)
    assert TABLES.isdisjoint(tables(database))
    run(url, "upgrade", REVISION)
    assert TABLES.issubset(tables(database))


def test_pkg011_offline_sqlite_and_postgresql_are_query_independent() -> None:
    for url in ("sqlite:///:memory:", "postgresql://ddl-only.invalid/retirement"):
        ddl = run(url, "upgrade", f"{PARENT}:{REVISION}", "--sql").stdout.lower()
        assert all(f"create table {table}" in ddl for table in TABLES)
        assert "select " not in ddl
        down = run(url, "downgrade", f"{REVISION}:{PARENT}", "--sql").stdout.lower()
        assert all(f"drop table {table}" in down for table in TABLES)
