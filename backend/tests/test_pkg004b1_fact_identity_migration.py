from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, text

from app.services.m07_evidence_service import m07_fingerprint


PARENT_REVISION = "e6f1a9c3b702"
IDENTITY_REVISION = "a9c4e7f2b615"


def _run_alembic(
    db_path: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return subprocess.run(
        ["alembic", *args],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=check,
    )


def _run_postgresql_offline(
    *args: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = (
        "postgresql://offline:offline@localhost/offline"
    )
    return subprocess.run(
        ["alembic", *args, "--sql"],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _prepare_parent_database(db_path: Path) -> None:
    _run_alembic(db_path, "upgrade", PARENT_REVISION)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO clients (client_id, display_name, id_number) "
                "VALUES (1, 'Migration Client', 'migration-client')"
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO m07_evidence_revisions (
                    m07_evidence_revision_id, profile_id, client_id,
                    revision_number, tax_year, event_year, schema_version,
                    rule_version, status, authority_classification,
                    technical_outcomes, fingerprint_algorithm_version,
                    created_at, created_by
                ) VALUES (
                    'm07rev-migration', 'profile-migration', 1, 1,
                    2026, 2026, 'pkg004b1.m07-evidence.v1',
                    'pkg004b1.technical-assessment.v1', 'draft',
                    'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY', '[]',
                    'sha256-canonical-json-v1', CURRENT_TIMESTAMP, 'creator'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO m07_planner_assertions (
                    assertion_id, m07_evidence_revision_id, client_id,
                    field_code, asserted_value, authority_classification,
                    assertion_basis, assertion_reason, asserted_at,
                    asserted_by, content_fingerprint
                ) VALUES (
                    'assertion-1', 'm07rev-migration', 1, 'legacy.field',
                    '"asserted"', 'ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY',
                    'planner evidence', 'legacy import', CURRENT_TIMESTAMP,
                    'planner', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                )
                """
            )
        )


def _insert_fact(
    db_path: Path,
    fact_id: str,
    *,
    field_code: str = "legacy.field",
    collection_state: str = "recorded",
    collection_basis: str | None = None,
    verification_state: str = "verified",
    source_type: str | None = None,
    source_record_type: str | None = None,
    source_record_id: str | None = None,
    source_document_reference: str | None = None,
    assertion_id: str | None = None,
    ignore_checks: bool = False,
) -> None:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        if ignore_checks:
            connection.execute(text("PRAGMA ignore_check_constraints = ON"))
        connection.execute(
            text(
                """
                INSERT INTO m07_fact_evidence (
                    fact_evidence_id, m07_evidence_revision_id, client_id,
                    field_code, structured_value, collection_state,
                    collection_basis, verification_state,
                    authority_classification, source_type,
                    source_record_type, source_record_id,
                    source_document_reference, source_metadata,
                    recorded_at, recorded_by, verified_at, verified_by,
                    verification_basis, assertion_id, content_fingerprint
                ) VALUES (
                    :fact_id, 'm07rev-migration', 1, :field_code, '"value"',
                    :collection_state, :collection_basis, :verification_state,
                    'EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY', :source_type,
                    :source_record_type, :source_record_id,
                    :source_document_reference, '{}', CURRENT_TIMESTAMP,
                    'collector',
                    CASE WHEN :verification_state IN ('verified', 'partly_verified')
                         THEN CURRENT_TIMESTAMP END,
                    CASE WHEN :verification_state IN ('verified', 'partly_verified')
                         THEN 'verifier' END,
                    CASE WHEN :verification_state IN ('verified', 'partly_verified')
                         THEN 'legacy verification' END,
                    :assertion_id,
                    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
                )
                """
            ),
            {
                "fact_id": fact_id,
                "field_code": field_code,
                "collection_state": collection_state,
                "collection_basis": collection_basis,
                "verification_state": verification_state,
                "source_type": source_type,
                "source_record_type": source_record_type,
                "source_record_id": source_record_id,
                "source_document_reference": source_document_reference,
                "assertion_id": assertion_id,
            },
        )


def _schema_snapshot(db_path: Path) -> list[tuple[str, str, str | None]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    """
                    SELECT type, name, sql
                      FROM sqlite_master
                     WHERE name NOT LIKE 'sqlite_%'
                     ORDER BY type, name
                    """
                )
            ).tuples()
        )


def _fact_rows(db_path: Path) -> list[tuple]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as connection:
        return list(
            connection.execute(
                text(
                    """
                    SELECT fact_evidence_id, field_code, collection_state,
                           collection_basis, verification_state, source_type,
                           source_record_type, source_record_id,
                           source_document_reference, assertion_id
                      FROM m07_fact_evidence
                     ORDER BY fact_evidence_id
                    """
                )
            ).tuples()
        )


def _version(db_path: Path) -> str:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as connection:
        return connection.scalar(text("SELECT version_num FROM alembic_version"))


@pytest.mark.parametrize(
    ("basis", "fact_kwargs"),
    [
        (
            "record:employment:record-1",
            {
                "source_type": "persisted_record",
                "source_record_type": "employment",
                "source_record_id": "record-1",
            },
        ),
        (
            "document:external_document:document://legacy",
            {
                "source_type": "external_document",
                "source_document_reference": "document://legacy",
            },
        ),
        (
            "assertion:assertion-1",
            {
                "verification_state": "planner_asserted",
                "assertion_id": "assertion-1",
            },
        ),
        (
            "state:not_collected",
            {
                "collection_state": "not_collected",
                "collection_basis": "not available during collection",
                "verification_state": "unverified",
            },
        ),
    ],
)
def test_valid_legacy_basis_migrates_with_service_identity_parity(
    tmp_path: Path, basis: str, fact_kwargs: dict[str, str]
) -> None:
    db_path = tmp_path / "valid-basis.db"
    _prepare_parent_database(db_path)
    _insert_fact(db_path, "fact-valid", **fact_kwargs)

    _run_alembic(db_path, "upgrade", IDENTITY_REVISION)

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as connection:
        actual = connection.scalar(
            text(
                "SELECT fact_identity_key FROM m07_fact_evidence "
                "WHERE fact_evidence_id = 'fact-valid'"
            )
        )
    assert actual == m07_fingerprint(
        {
            "revision_id": "m07rev-migration",
            "field_code": "legacy.field",
            "basis_identity": basis,
        }
    )


@pytest.mark.parametrize(
    ("fact_kwargs", "correction_sql"),
    [
        (
            {
                "source_type": "persisted_record",
                "source_record_type": "employment",
                "source_record_id": "record-1",
                "source_document_reference": "document://legacy",
            },
            "UPDATE m07_fact_evidence SET source_document_reference = NULL",
        ),
        (
            {
                "source_type": "persisted_record",
                "source_record_type": "employment",
                "source_record_id": "record-1",
                "assertion_id": "assertion-1",
            },
            "UPDATE m07_fact_evidence SET assertion_id = NULL",
        ),
        (
            {
                "source_type": "external_document",
                "source_document_reference": "document://legacy",
                "assertion_id": "assertion-1",
            },
            "UPDATE m07_fact_evidence SET assertion_id = NULL",
        ),
        (
            {
                "collection_state": "not_collected",
                "collection_basis": "not available",
                "verification_state": "planner_asserted",
            },
            "UPDATE m07_fact_evidence SET verification_state = 'unverified'",
        ),
        (
            {
                "source_type": "persisted_record",
                "source_record_type": "employment",
                "source_record_id": "record-1",
                "source_document_reference": "document://legacy",
                "assertion_id": "assertion-1",
            },
            "UPDATE m07_fact_evidence "
            "SET source_document_reference = NULL, assertion_id = NULL",
        ),
        (
            {
                "verification_state": "verified",
                "assertion_id": "assertion-1",
            },
            "UPDATE m07_fact_evidence "
            "SET verification_state = 'planner_asserted', "
            "verified_at = NULL, verified_by = NULL, "
            "verification_basis = NULL",
        ),
        (
            {
                "source_type": "external_document",
            },
            "UPDATE m07_fact_evidence "
            "SET source_document_reference = 'document://corrected'",
        ),
        (
            {
                "source_type": "persisted_record",
                "source_record_type": "employment",
            },
            "UPDATE m07_fact_evidence SET source_record_id = 'record-corrected'",
        ),
    ],
)
def test_malformed_basis_fails_before_schema_change_and_retry_succeeds(
    tmp_path: Path,
    fact_kwargs: dict[str, str],
    correction_sql: str,
) -> None:
    db_path = tmp_path / "malformed-basis.db"
    _prepare_parent_database(db_path)
    _insert_fact(
        db_path,
        "fact-malformed",
        ignore_checks=True,
        **fact_kwargs,
    )
    schema_before = _schema_snapshot(db_path)
    rows_before = _fact_rows(db_path)

    result = _run_alembic(
        db_path, "upgrade", IDENTITY_REVISION, check=False
    )

    assert result.returncode != 0
    assert "Malformed PKG-004B1 evidence must be corrected before upgrade" in (
        result.stdout + result.stderr
    )
    assert _schema_snapshot(db_path) == schema_before
    assert _fact_rows(db_path) == rows_before
    assert _version(db_path) == PARENT_REVISION
    inspector = sqlalchemy_inspect(
        create_engine(f"sqlite:///{db_path.as_posix()}")
    )
    assert "fact_identity_key" not in {
        column["name"]
        for column in inspector.get_columns("m07_fact_evidence")
    }
    assert "uq_m07_fact_evidence_identity_key" not in {
        item["name"]
        for item in inspector.get_unique_constraints("m07_fact_evidence")
    }

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text(correction_sql))
    _run_alembic(db_path, "upgrade", IDENTITY_REVISION)
    assert _version(db_path) == IDENTITY_REVISION


@pytest.mark.parametrize(
    ("index_name", "fact_kwargs", "correction_sql", "recreate_sql"),
    [
        (
            "uq_m07_fact_evidence_persisted_source_identity",
            {
                "source_type": "persisted_record",
                "source_record_type": "employment",
                "source_record_id": "record-1",
            },
            "UPDATE m07_fact_evidence SET source_record_id = 'record-2' "
            "WHERE fact_evidence_id = 'fact-2'",
            "CREATE UNIQUE INDEX uq_m07_fact_evidence_persisted_source_identity "
            "ON m07_fact_evidence (client_id, m07_evidence_revision_id, "
            "field_code, source_record_type, source_record_id)",
        ),
        (
            "uq_m07_fact_evidence_document_identity",
            {
                "source_type": "external_document",
                "source_document_reference": "document://legacy",
            },
            "UPDATE m07_fact_evidence "
            "SET source_document_reference = 'document://corrected' "
            "WHERE fact_evidence_id = 'fact-2'",
            "CREATE UNIQUE INDEX uq_m07_fact_evidence_document_identity "
            "ON m07_fact_evidence (client_id, m07_evidence_revision_id, "
            "field_code, source_document_reference)",
        ),
        (
            "uq_m07_fact_evidence_assertion_identity",
            {
                "verification_state": "planner_asserted",
                "assertion_id": "assertion-1",
            },
            "UPDATE m07_fact_evidence SET field_code = 'legacy.other' "
            "WHERE fact_evidence_id = 'fact-2'",
            "CREATE UNIQUE INDEX uq_m07_fact_evidence_assertion_identity "
            "ON m07_fact_evidence (client_id, m07_evidence_revision_id, "
            "field_code, assertion_id)",
        ),
    ],
)
def test_duplicate_identity_fails_preflight_preserves_rows_and_retries(
    tmp_path: Path,
    index_name: str,
    fact_kwargs: dict[str, str],
    correction_sql: str,
    recreate_sql: str,
) -> None:
    db_path = tmp_path / "duplicate-identity.db"
    _prepare_parent_database(db_path)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text(f"DROP INDEX {index_name}"))
    _insert_fact(db_path, "fact-1", **fact_kwargs)
    _insert_fact(db_path, "fact-2", **fact_kwargs)
    schema_before = _schema_snapshot(db_path)
    rows_before = _fact_rows(db_path)

    result = _run_alembic(
        db_path, "upgrade", IDENTITY_REVISION, check=False
    )

    assert result.returncode != 0
    assert "Duplicate PKG-004B1 fact identity must be corrected" in (
        result.stdout + result.stderr
    )
    assert _schema_snapshot(db_path) == schema_before
    assert _fact_rows(db_path) == rows_before
    assert _version(db_path) == PARENT_REVISION
    assert "fact_identity_key" not in {
        column["name"]
        for column in sqlalchemy_inspect(engine).get_columns(
            "m07_fact_evidence"
        )
    }

    with engine.begin() as connection:
        connection.execute(text(correction_sql))
        connection.execute(text(recreate_sql))
    _run_alembic(db_path, "upgrade", IDENTITY_REVISION)
    assert _version(db_path) == IDENTITY_REVISION


def test_sqlite_identity_upgrade_and_downgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "upgrade-downgrade.db"
    _prepare_parent_database(db_path)
    _insert_fact(
        db_path,
        "fact-valid",
        source_type="external_document",
        source_document_reference="document://legacy",
    )

    _run_alembic(db_path, "upgrade", IDENTITY_REVISION)
    _run_alembic(db_path, "downgrade", PARENT_REVISION)

    assert _version(db_path) == PARENT_REVISION
    assert "fact_identity_key" not in {
        column["name"]
        for column in sqlalchemy_inspect(
            create_engine(f"sqlite:///{db_path.as_posix()}")
        ).get_columns("m07_fact_evidence")
    }


def test_postgresql_offline_upgrade_and_downgrade_sql_generation() -> None:
    upgrade = _run_postgresql_offline(
        "upgrade", f"{PARENT_REVISION}:{IDENTITY_REVISION}"
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    assert "Malformed PKG-004B1 evidence" in upgrade.stdout
    assert "Duplicate PKG-004B1 fact identity" in upgrade.stdout
    assert "ADD COLUMN fact_identity_key" in upgrade.stdout
    assert "UPDATE m07_fact_evidence" in upgrade.stdout
    assert "sha256" in upgrade.stdout
    assert "uq_m07_fact_evidence_identity_key" in upgrade.stdout
    canonical_fragments = [
        """'{"basis_identity":'""",
        """',"field_code":'""",
        """',"revision_id":'""",
    ]
    fragment_positions = [
        upgrade.stdout.index(fragment) for fragment in canonical_fragments
    ]
    assert fragment_positions == sorted(fragment_positions)

    downgrade = _run_postgresql_offline(
        "downgrade", f"{IDENTITY_REVISION}:{PARENT_REVISION}"
    )
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
    assert "DROP CONSTRAINT uq_m07_fact_evidence_identity_key" in (
        downgrade.stdout
    )
    assert "DROP COLUMN fact_identity_key" in downgrade.stdout
