from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

PARENT = "c4e8a1f6d203"
FOUNDATION = "d5f9b2a7c406"
HEAD = "c2d8f5a1b309"
TABLES = {"m09_scenario_subjects", "m09_scenario_adjustments", "m09_scenario_subject_seals", "m09_subject_runs", "m09_subject_monthly_results"}


def run(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy(); env["DATABASE_URL"] = url
    return subprocess.run(["alembic", *args], cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=True)


def test_pkg014_is_single_additive_head() -> None:
    assert run("sqlite:///:memory:", "heads").stdout.strip() == f"{HEAD} (head)"


def test_pkg014_upgrade_downgrade_and_triggers(tmp_path: Path) -> None:
    db = tmp_path / "pkg014.db"; url = f"sqlite:///{db.as_posix()}"
    run(url, "upgrade", PARENT)
    with sqlite3.connect(db) as connection:
        assert TABLES.isdisjoint({r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")})
    run(url, "upgrade", HEAD)
    with sqlite3.connect(db) as connection:
        names = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert TABLES.issubset(names)
        triggers = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        assert all(f"trg_{table}_no_update" in triggers and f"trg_{table}_no_delete" in triggers for table in TABLES - {"m09_scenario_subject_seals"})
        assert "trg_m09_scenario_subject_seals_no_update" in triggers
        assert "trg_m09_scenario_subject_seals_no_delete" in triggers
        connection.execute("INSERT INTO clients (client_id, display_name, id_number) VALUES (1, 'One', '001')")
        connection.execute("""INSERT INTO m09_scenario_subjects VALUES ('S1',1,'declared_retirement_cashflow_adjustments','v1','baseline',NULL,'{}',?,?,?,'server_resolved_no_scenario_adjustments','system:m09',CURRENT_TIMESTAMP)""", ("a"*64,"b"*64,"c"*64))
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="m09_subject_append_only_violation"):
            connection.execute("UPDATE m09_scenario_subjects SET display_label='x' WHERE scenario_subject_id='S1'")
        with pytest.raises(sqlite3.IntegrityError, match="m09_subject_append_only_violation"):
            connection.execute("DELETE FROM m09_scenario_subjects WHERE scenario_subject_id='S1'")


def test_pkg014_offline_sql_is_query_independent() -> None:
    for url in ("sqlite:///:memory:", "postgresql://ddl-only.invalid/retirement"):
        ddl = run(url, "upgrade", f"{PARENT}:{HEAD}", "--sql").stdout.lower()
        assert all(f"create table {table}" in ddl for table in TABLES)
        assert "m09_subject_append_only_violation" in ddl
        assert "m09_subject_manifest_sealed" in ddl
        down = run(url, "downgrade", f"{HEAD}:{PARENT}", "--sql").stdout.lower()
        assert all(f"drop table {table}" in down for table in TABLES)
        assert "trg_m09_adjustment_reject_after_seal" in down
        if url.startswith("postgresql"):
            assert "m09_reject_adjustment_after_seal" in down


def test_pkg014_seal_rejects_raw_adjustment_injection(tmp_path: Path) -> None:
    db = tmp_path / "pkg014-seal.db"; url = f"sqlite:///{db.as_posix()}"
    run(url, "upgrade", HEAD)
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO clients (client_id, display_name, id_number) VALUES (1, 'One', '001')")
        connection.execute("""INSERT INTO m09_scenario_subjects VALUES ('S1',1,'declared_retirement_cashflow_adjustments','v1','adjusted','A','{}',?,?,?,'planner_declared_scenario_adjustment','system:m09',CURRENT_TIMESTAMP)""", ("a"*64,"b"*64,"c"*64))
        connection.execute("""INSERT INTO m09_scenario_adjustments VALUES ('A1','S1',1,1,'declared_additional_monthly_income',100.00,'100.00','2026-01','2026-02','planner_declared_scenario_adjustment',?,'system:m09',CURRENT_TIMESTAMP)""", ("d"*64,))
        connection.execute("""INSERT INTO m09_scenario_subject_seals VALUES ('S1',1,1,?,'system:m09',CURRENT_TIMESTAMP)""", ("a"*64,))
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="m09_subject_manifest_sealed"):
            connection.execute("""INSERT INTO m09_scenario_adjustments VALUES ('A2','S1',1,2,'declared_additional_monthly_income',900.00,'900.00','2026-01','2026-02','planner_declared_scenario_adjustment',?,'system:m09',CURRENT_TIMESTAMP)""", ("e"*64,))


def test_pkg014_correction_downgrade_reupgrade(tmp_path: Path) -> None:
    db = tmp_path / "pkg014-cycle.db"; url = f"sqlite:///{db.as_posix()}"
    run(url, "upgrade", HEAD); run(url, "downgrade", FOUNDATION); run(url, "upgrade", HEAD)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM m09_scenario_subject_seals").fetchone() == (0,)
