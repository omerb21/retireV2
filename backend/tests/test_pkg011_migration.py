from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any

import pytest


BACKEND = Path(__file__).resolve().parents[1]
REVISION = "e8f4b7c2d305"
M06_REVISION = "d7e3a6b9c204"
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


def _insert_stub(connection: sqlite3.Connection, table: str, **overrides: Any) -> None:
    columns: list[str] = []
    values: list[Any] = []
    for _cid, name, kind, not_null, default, primary_key in connection.execute(
        f"PRAGMA table_info({table})"
    ):
        if name in overrides:
            columns.append(name)
            values.append(overrides[name])
        elif (not_null or primary_key) and default is None:
            columns.append(name)
            if "INT" in kind.upper():
                values.append(1)
            elif any(token in kind.upper() for token in ("NUMERIC", "DECIMAL", "REAL")):
                values.append("0")
            elif "JSON" in kind.upper():
                values.append("{}")
            else:
                values.append(f"{table}:{name}:{overrides.get('client_id', 0)}")
    placeholders = ",".join("?" for _ in columns)
    connection.execute(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})", values
    )


def _seed_ownership_predecessors(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("PRAGMA ignore_check_constraints=ON")
    for client_id in (1, 2):
        _insert_stub(
            connection,
            "clients",
            client_id=client_id,
            display_name=f"Client {client_id}",
            id_number=f"00{client_id}",
            status="delivered",
        )
        _insert_stub(
            connection,
            "m02_intake_records",
            intake_id=f"M02-{client_id}",
            client_id=client_id,
            record_kind="manual",
            manual_technical_reference=f"M02-MANUAL-{client_id}",
            source_type="manual",
            lifecycle_status="accepted_for_review",
            preservation_status="not_applicable",
            diagnostics="[]",
            created_by_actor="system:test",
            updated_by_actor="system:test",
            lifecycle_decided_by_actor="system:test",
        )
        _insert_stub(
            connection,
            "m03_review_revisions",
            revision_id=f"M03-{client_id}",
            client_id=client_id,
            intake_id=f"M02-{client_id}",
            target_kind="manual_record_review",
            revision_sequence=1,
            state="under_review",
            actor="system:m03-review-ui:M03 review workflow",
        )
        _insert_stub(
            connection,
            "m04_classification_revisions",
            revision_id=f"M04-{client_id}",
            subject_id=f"M04-S-{client_id}",
            client_id=client_id,
            intake_id=f"M02-{client_id}",
            target_kind="manual_record_review",
            m03_revision_id=f"M03-{client_id}",
            revision_sequence=1,
            state="proposed",
            action_type="start",
            input_snapshot="{}",
            catalogue_version="m04-test",
            matched_rule_evidence="[]",
            match_basis="none",
            action_evidence="{}",
            evidence_digest="a" * 64,
            actor="system:test",
        )
        _insert_stub(
            connection,
            "m05_ledger_subjects",
            subject_id=f"M05-S-{client_id}",
            client_id=client_id,
            provider_name=f"Provider {client_id}",
            account_reference=f"Account {client_id}",
            provider_identity_digest="b" * 64,
            account_identity_digest=("c" if client_id == 1 else "d") * 64,
        )
        _insert_stub(
            connection,
            "m05_ledger_revisions",
            revision_id=f"M05-{client_id}",
            subject_id=f"M05-S-{client_id}",
            client_id=client_id,
            candidate_id=f"M05-CAND-{client_id}",
            intake_id=f"M02-{client_id}",
            target_kind="manual_record_review",
            m03_revision_id=f"M03-{client_id}",
            m04_revision_id=f"M04-{client_id}",
            revision_sequence=1,
            state="draft",
            action_type="start",
            provider_name=f"Provider {client_id}",
            account_reference=f"Account {client_id}",
            product_context="{}",
            statement_date="2026-01-01",
            evaluation_date="2026-01-01",
            is_stale=0,
            source_snapshot_digest="e" * 64,
            mapping_digest="f" * 64,
            currency="ILS",
            currency_confirmed=1,
            currency_confirmation_evidence="{}",
            source_total_state="recorded_zero",
            effective_total_state="recorded_zero",
            algorithm_version="m05-test",
            included_evidence="[]",
            excluded_evidence="[]",
            warnings="[]",
            warning_dispositions="[]",
            provenance="{}",
            evidence_digest=("1" if client_id == 1 else "2") * 64,
            actor="system:test",
        )
    connection.commit()
    connection.execute("PRAGMA ignore_check_constraints=OFF")
    connection.execute("PRAGMA foreign_keys=ON")


def _insert_m06_subject(
    connection: sqlite3.Connection, subject_id: str, client_id: int = 1
) -> None:
    connection.execute(
        "INSERT INTO m06_conversion_subjects "
        "(subject_id,client_id,m05_subject_id,mode,input_identity,"
        "provider_identity_digest,account_identity_digest,product_context_digest,"
        "semantic_digest,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            subject_id,
            client_id,
            f"M05-S-{client_id}",
            "balance_to_monthly_pension",
            f"component:{subject_id}",
            "b" * 64,
            ("c" if client_id == 1 else "d") * 64,
            "3" * 64,
            subject_id[-1] * 64,
            "2026-01-01T00:00:00",
        ),
    )


def _insert_m06_revision(
    connection: sqlite3.Connection,
    revision_id: str,
    subject_id: str,
    m04_revision_id: str,
    m05_revision_id: str,
) -> None:
    connection.execute(
        "INSERT INTO m06_conversion_revisions "
        "(revision_id,subject_id,client_id,predecessor_revision_id,revision_sequence,"
        "state,action_type,mode,formula_id,input_identity,input_amount,input_date,"
        "m02_intake_id,m03_revision_id,m04_revision_id,m05_revision_id,"
        "predecessor_snapshot,warnings,blocking_reasons,informational_warnings,"
        "evidence_digest,actor,created_at) "
        "VALUES (?,?,1,NULL,1,'draft','start','balance_to_monthly_pension',"
        "'m06.balance_to_monthly_pension.v1',?,'0','2026-01-01','M02-1','M03-1',"
        "?,?, '{}','[]','[]','[]',?,?,?)",
        (
            revision_id,
            subject_id,
            f"component:{subject_id}",
            m04_revision_id,
            m05_revision_id,
            "9" * 64,
            "system:m06-conversion-ui:M06 conversion workflow",
            "2026-01-01T00:00:00",
        ),
    )


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
            and "fk_m06_revision_m04_client" in ddl
            and "fk_m06_revision_m05_client" in ddl
        )
        foreign_keys = list(
            connection.execute("PRAGMA foreign_key_list(m06_conversion_revisions)")
        )
        grouped: dict[int, list[tuple[str, str, str]]] = {}
        for row in foreign_keys:
            grouped.setdefault(row[0], []).append((row[2], row[3], row[4]))
        assert any(
            set(group)
            == {
                ("m04_classification_revisions", "m04_revision_id", "revision_id"),
                ("m04_classification_revisions", "client_id", "client_id"),
            }
            for group in grouped.values()
        )
        assert any(
            set(group)
            == {
                ("m05_ledger_revisions", "m05_revision_id", "revision_id"),
                ("m05_ledger_revisions", "client_id", "client_id"),
            }
            for group in grouped.values()
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
        ddl = run(url, "upgrade", f"{PARENT}:{M06_REVISION}", "--sql").stdout.lower()
        assert all(f"create table {table}" in ddl for table in TABLES)
        assert "select " not in ddl
        down = run(url, "downgrade", f"{M06_REVISION}:{PARENT}", "--sql").stdout.lower()
        assert all(f"drop table {table}" in down for table in TABLES)


def test_pkg011_postgresql_ownership_ddl_is_composite() -> None:
    url = "postgresql://ddl-only.invalid/retirement"
    ddl = run(url, "upgrade", f"{M06_REVISION}:{REVISION}", "--sql").stdout.lower()
    assert "uq_m04_revision_identity_client" in ddl
    assert "uq_m05_revision_identity_client" in ddl
    assert "fk_m06_revision_m04_client" in ddl
    assert "foreign key(m04_revision_id, client_id)" in ddl
    assert "references m04_classification_revisions (revision_id, client_id)" in ddl
    assert "fk_m06_revision_m05_client" in ddl
    assert "foreign key(m05_revision_id, client_id)" in ddl
    assert "references m05_ledger_revisions (revision_id, client_id)" in ddl
    down = run(url, "downgrade", f"{REVISION}:{M06_REVISION}", "--sql").stdout.lower()
    assert "drop constraint fk_m06_revision_m04_client" in down
    assert "drop constraint fk_m06_revision_m05_client" in down


def test_pkg011_ownership_upgrade_preserves_predecessor_rows(tmp_path: Path) -> None:
    database = tmp_path / "predecessor-preservation.db"
    url = f"sqlite:///{database.as_posix()}"
    run(url, "upgrade", M06_REVISION)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("PRAGMA ignore_check_constraints=ON")
        _insert_stub(
            connection,
            "m04_classification_revisions",
            revision_id="m04-preserved",
            client_id=41,
            target_kind="manual_record_review",
            state="under_review",
            action_type="start",
            evidence_digest="a" * 64,
        )
        _insert_stub(
            connection,
            "m05_ledger_revisions",
            revision_id="m05-preserved",
            client_id=41,
            target_kind="manual_record_review",
            state="draft",
            action_type="start",
            currency="ILS",
            evidence_digest="b" * 64,
        )
        connection.commit()
        before = {
            table: connection.execute(
                f"SELECT revision_id, client_id FROM {table} ORDER BY revision_id"
            ).fetchall()
            for table in (
                "m04_classification_revisions",
                "m05_ledger_revisions",
            )
        }

    run(url, "upgrade", REVISION)

    with sqlite3.connect(database) as connection:
        after = {
            table: connection.execute(
                f"SELECT revision_id, client_id FROM {table} ORDER BY revision_id"
            ).fetchall()
            for table in before
        }
    assert after == before


def test_pkg011_database_rejects_cross_client_m04_and_m05_without_residue(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pkg011-ownership.db"
    run(f"sqlite:///{database.as_posix()}", "upgrade", REVISION)
    with sqlite3.connect(database) as connection:
        _seed_ownership_predecessors(connection)

        _insert_m06_subject(connection, "M06-S-1")
        _insert_m06_revision(connection, "M06-R-same", "M06-S-1", "M04-1", "M05-1")
        connection.commit()
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM m06_conversion_revisions WHERE revision_id='M06-R-same'"
            ).fetchone()[0]
            == 1
        )

        _insert_m06_subject(connection, "M06-S-2")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            _insert_m06_revision(
                connection, "M06-R-cross-m04", "M06-S-2", "M04-2", "M05-1"
            )
        connection.rollback()
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM m06_conversion_revisions WHERE revision_id='M06-R-cross-m04'"
            ).fetchone()[0]
            == 0
        )

        _insert_m06_subject(connection, "M06-S-3")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            _insert_m06_revision(
                connection, "M06-R-cross-m05", "M06-S-3", "M04-1", "M05-2"
            )
        connection.rollback()
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM m06_conversion_revisions WHERE revision_id='M06-R-cross-m05'"
            ).fetchone()[0]
            == 0
        )
