from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path


PARENT = "f9a1c3e5b702"
REVISION = "a7c9e1f3b805"
TABLES = {
    "m09_resolved_component_inventories",
    "m09_scenario_runs",
    "m09_monthly_results",
}


def run(url: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    return subprocess.run(
        ["alembic", *args],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def tables(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def test_pkg013_is_single_additive_head() -> None:
    assert run("sqlite:///:memory:", "heads").stdout.strip() == f"{REVISION} (head)"


def test_pkg013_upgrade_downgrade_reupgrade_is_bounded(tmp_path: Path) -> None:
    database = tmp_path / "pkg013.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", PARENT)
    assert TABLES.isdisjoint(tables(database))
    with sqlite3.connect(database) as connection:
        before = connection.execute(
            "PRAGMA table_info('m06_calculation_manifests')"
        ).fetchall()
        assert "authoritative_monthly_amount" not in {row[1] for row in before}
    run(url, "upgrade", REVISION)
    assert TABLES.issubset(tables(database))
    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info('m06_calculation_manifests')"
            )
        }
        assert "authoritative_monthly_amount" in columns
        run_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info('m09_scenario_runs')")
        }
        assert {
            "assumption_manifest",
            "upstream_snapshot",
            "range_totals",
            "semantic_result_fingerprint",
            "result_integrity_fingerprint",
        }.issubset(run_columns)
    run(url, "downgrade", PARENT)
    assert TABLES.isdisjoint(tables(database))
    run(url, "upgrade", REVISION)
    assert TABLES.issubset(tables(database))


def test_pkg013_offline_sqlite_and_postgresql_are_query_independent() -> None:
    for url in ("sqlite:///:memory:", "postgresql://ddl-only.invalid/retirement"):
        ddl = run(url, "upgrade", f"{PARENT}:{REVISION}", "--sql").stdout.lower()
        assert all(f"create table {table}" in ddl for table in TABLES)
        assert "authoritative_monthly_amount" in ddl
        assert "select " not in ddl
        down = run(url, "downgrade", f"{REVISION}:{PARENT}", "--sql").stdout.lower()
        assert all(f"drop table {table}" in down for table in TABLES)


def test_pkg013_downgrade_refuses_evidence_loss(tmp_path: Path) -> None:
    database = tmp_path / "pkg013-evidence.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", REVISION)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO clients (client_id, display_name, id_number) VALUES (1, 'One', '001')"
        )
        connection.execute(
            """
            INSERT INTO m09_resolved_component_inventories (
                inventory_id, client_id, scenario_family,
                scenario_contract_version, start_month, end_month,
                component_domain_contract_version, assessment_timestamp,
                actor, inventory_payload, inventory_fingerprint, complete,
                blocker_codes
            ) VALUES (
                'M09-I-test', 1, 'deterministic_monthly_cashflow', 'v1',
                '2026-01', '2026-01', 'm09-component-domains-v1',
                CURRENT_TIMESTAMP, 'system:m09-cashflow:M09 cashflow workflow',
                '{}', ?, 1, '[]'
            )
            """,
            ("a" * 64,),
        )
        connection.commit()
    result = run(url, "downgrade", PARENT, check=False)
    assert result.returncode != 0
    assert "cannot downgrade while PKG-013 inventory or run evidence exists" in (
        result.stdout + result.stderr
    )
    assert TABLES.issubset(tables(database))
