from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest


PARENT = "f9a1c3e5b702"
REVISION = "a7c9e1f3b805"
HEAD = "c4e8a1f6d203"
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
    assert run("sqlite:///:memory:", "heads").stdout.strip() == f"{HEAD} (head)"


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
    run(url, "upgrade", HEAD)
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
    run(url, "upgrade", HEAD)
    assert TABLES.issubset(tables(database))


def test_pkg013_offline_sqlite_and_postgresql_are_query_independent() -> None:
    for url in ("sqlite:///:memory:", "postgresql://ddl-only.invalid/retirement"):
        ddl = run(url, "upgrade", f"{PARENT}:{HEAD}", "--sql").stdout.lower()
        assert all(f"create table {table}" in ddl for table in TABLES)
        assert "authoritative_monthly_amount" in ddl
        assert "select count" not in ddl
        down = run(url, "downgrade", f"{HEAD}:{PARENT}", "--sql").stdout.lower()
        assert all(f"drop table {table}" in down for table in TABLES)
        assert "m09_append_only_violation" in ddl
        assert all(f"trg_{table}" in ddl for table in TABLES)
        assert all(f"trg_{table}" in down for table in TABLES)


def test_pkg013_downgrade_refuses_evidence_loss(tmp_path: Path) -> None:
    database = tmp_path / "pkg013-evidence.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", HEAD)
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


def test_pkg013_database_triggers_block_raw_update_delete_but_allow_append(tmp_path: Path) -> None:
    database = tmp_path / "pkg013-triggers.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", HEAD)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO clients (client_id, display_name, id_number) VALUES (1, 'One', '001')")
        connection.execute(
            """INSERT INTO m09_resolved_component_inventories
            (inventory_id, client_id, scenario_family, scenario_contract_version, start_month, end_month,
             component_domain_contract_version, assessment_timestamp, actor, inventory_payload,
             inventory_fingerprint, complete, blocker_codes)
            VALUES ('M09-I-one', 1, 'deterministic_monthly_cashflow', 'v1', '2026-01', '2026-01',
             'm09-component-domains-v1', CURRENT_TIMESTAMP, 'system:m09', '{}', ?, 1, '[]')""",
            ("a" * 64,),
        )
        run_values = (
            "M09-R-one", 1, None, 1, "M09-I-one", "success_complete",
            "{}", "b" * 64, "{}", "c" * 64, "[]", "[]",
            '{"gross_inflow_total":"1.00","gross_outflow_total":"0.00","period_net":"1.00"}',
            "d" * 64, "e" * 64, "system:m09",
        )
        connection.execute(
            """INSERT INTO m09_scenario_runs
            (run_id, client_id, predecessor_run_id, run_sequence, scenario_family, scenario_contract_version,
             start_month, end_month, inventory_id, status, assumption_manifest, assumption_manifest_fingerprint,
             upstream_snapshot, upstream_snapshot_fingerprint, warnings, blocker_codes, range_totals,
             semantic_result_fingerprint, result_integrity_fingerprint, actor, created_at)
            VALUES (?, ?, ?, ?, 'deterministic_monthly_cashflow', 'v1', '2026-01', '2026-01', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            run_values,
        )
        connection.execute(
            """INSERT INTO m09_monthly_results
            (monthly_result_id, run_id, client_id, month, gross_inflow_total, gross_outflow_total,
             period_net, component_evidence, result_fingerprint)
            VALUES ('M09-M-one', 'M09-R-one', 1, '2026-01', 1.00, 0.00, 1.00, '[]', ?)""",
            ("f" * 64,),
        )
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM m09_scenario_runs").fetchone()[0] == 1
        for table in sorted(TABLES):
            with pytest.raises(sqlite3.IntegrityError, match="m09_append_only_violation"):
                connection.execute(f"UPDATE {table} SET client_id = client_id WHERE 1 = 1")
            with pytest.raises(sqlite3.IntegrityError, match="m09_append_only_violation"):
                connection.execute(f"DELETE FROM {table} WHERE 1 = 1")
        successor = list(run_values)
        successor[0], successor[2], successor[3] = "M09-R-two", "M09-R-one", 2
        connection.execute(
            """INSERT INTO m09_scenario_runs
            (run_id, client_id, predecessor_run_id, run_sequence, scenario_family, scenario_contract_version,
             start_month, end_month, inventory_id, status, assumption_manifest, assumption_manifest_fingerprint,
             upstream_snapshot, upstream_snapshot_fingerprint, warnings, blocker_codes, range_totals,
             semantic_result_fingerprint, result_integrity_fingerprint, actor, created_at)
            VALUES (?, ?, ?, ?, 'deterministic_monthly_cashflow', 'v1', '2026-01', '2026-01', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            tuple(successor),
        )
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM m09_scenario_runs").fetchone()[0] == 2


def test_pkg013_corrective_downgrade_removes_only_trigger_protection(tmp_path: Path) -> None:
    database = tmp_path / "pkg013-trigger-down.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", HEAD)
    run(url, "downgrade", REVISION)
    with sqlite3.connect(database) as connection:
        trigger_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'trg_m09_%'"
        ).fetchone()[0]
        assert trigger_count == 0
    assert TABLES.issubset(tables(database))
