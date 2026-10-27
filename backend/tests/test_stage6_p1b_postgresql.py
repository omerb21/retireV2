"""Stage 6 P1B PostgreSQL transaction, CAS, migration and staleness evidence.

Runs only against the dedicated local ``retire_v2_scenario_test`` database.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.models.client import Client
from app.models.client_profile import ClientProfile
from app.models.pension_product import (
    COMPONENT_CODES, PensionProduct, PensionProductComponent,
)
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission
from app.services.scenario_draft_service import _source_evidence
from app.services.scenario_permission_preview_service import ruleset_digest
from app.services.scenario_pension_factor_admission_read_service import (
    FactorAdmissionBlocked, read_current_admission,
)
from app.services.scenario_pension_factor_admission_write_service import (
    PensionFactorWriteBlocked, _AUTHENTICATED_FACTOR_WRITE_CAPABILITY,
    _save_factor_admission, append_authenticated_serializable_factor_admission,
)

load_all_models()


def _url() -> str:
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated PostgreSQL test URL absent")
    parsed = urlsplit(value)
    if parsed.hostname not in {None, "localhost", "127.0.0.1", "::1"}:
        pytest.fail("local PostgreSQL required")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("only retire_v2_scenario_test permitted")
    return value


def _dependencies(*tables):
    found = set(tables)
    pending = list(tables)
    while pending:
        table = pending.pop()
        for fk in table.foreign_keys:
            parent = fk.column.table
            if parent not in found:
                found.add(parent)
                pending.append(parent)
    return list(found)


def _migration_module():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / (
        "d6f1a9c3b704_stage6_pension_factor_admissions.py")
    spec = importlib.util.spec_from_file_location("stage6_p1b_migration_pg", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _request(actor="planner-1"):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(
            auth_config=SimpleNamespace(production=True))),
        state=SimpleNamespace(
            trusted_professional_actor=actor,
            auth_session={"actor_id": actor}),
    )


def _write(factory, *, expected_revision, factor_value="200", actor="planner-1"):
    return append_authenticated_serializable_factor_admission(
        factory, request=_request(actor), client_id=7, scenario_id="s",
        decision_id="d", expected_scenario_version=1,
        expected_admission_revision=expected_revision,
        factor_value=factor_value,
        factor_evidence_type="PLANNER_ASSUMPTION",
        factor_evidence_reference="synthetic professional assumption",
    )


def _read(factory, *, scenario_id="s", decision_id="d"):
    with factory() as db, db.begin():
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        return read_current_admission(
            db, client_id=7, scenario_id=scenario_id, decision_id=decision_id)


def test_stage6_p1b_real_postgresql_lifecycle_cas_and_rollback(monkeypatch):
    engine = create_engine(_url())
    if engine.dialect.name != "postgresql":
        pytest.fail("PostgreSQL required")
    schema = "stage6_p1b_" + uuid4().hex[:12]
    role = "stage6_p1b_role_" + uuid4().hex[:10]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    migration = _migration_module()
    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
            conn.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
        with scoped.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(conn, tables=_dependencies(
                Client.__table__, ClientProfile.__table__, PensionProduct.__table__,
                PensionProductComponent.__table__, ScenarioDraft.__table__,
                ScenarioDraftDecision.__table__, ScenarioDraftPensionElection.__table__,
            ))
            monkeypatch.setenv("CRTISBA_APPLICATION_DB_ROLE", role)
            original_op = migration.op
            try:
                migration.op = Operations(MigrationContext.configure(conn))
                migration.upgrade()
            finally:
                migration.op = original_op
            assert "scenario_pension_factor_admissions" in inspect(conn).get_table_names(schema=schema)

            allowed_code = COMPONENT_CODES[1]
            conn.execute(Client.__table__.insert(), {
                "client_id": 7, "display_name": "Stage6 Synthetic",
                "id_number": "STAGE6-P1B-7",
            })
            conn.execute(ClientProfile.__table__.insert(), {
                "client_profile_id": "profile-7", "client_id": 7,
                "birth_date": date(1965, 4, 2), "gender": "female",
            })
            conn.execute(PensionProduct.__table__.insert(), {
                "product_id": "p", "client_id": 7, "source_kind": "imported",
                "source_identity": "imported:7:p", "product_name": "Synthetic",
                "product_type": "קרן פנסיה", "account_reference": "SYNTHETIC",
                "statement_date": date(2026, 9, 30), "historical_employers": [],
                "version": 1, "created_by": "test", "updated_by": "test",
            })
            conn.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "c", "product_id": "p",
                "component_code": allowed_code, "balance": Decimal("1000.00"),
            })
            source = _source_evidence(
                SimpleNamespace(client_id=7, product_id="p", version=1,
                    product_type="קרן פנסיה", source_kind="imported",
                    source_identity="imported:7:p"),
                SimpleNamespace(product_id="p", component_id="c",
                    component_code=allowed_code, balance=Decimal("1000.00")),
            )
            conn.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "s", "client_id": 7, "name": "Synthetic",
                "status": "draft", "version": 1, "created_by": "test",
                "updated_by": "test",
            })
            conn.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d", "scenario_id": "s", "source_product_id": "p",
                "source_component_id": "c", "component_code": allowed_code,
                "amount": Decimal("400.00"), "action": "pension",
                "effective_date": date(2026, 10, 27),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source["source_fingerprint"],
                "ruleset_digest_at_review": ruleset_digest(),
            })
            conn.execute(ScenarioDraftPensionElection.__table__.insert(), {
                "election_id": "e", "scenario_id": "s", "decision_id": "d",
                "scenario_version": 1, "pension_start_date": date(2027, 9, 30),
                "target_year": 2027, "survivors_option": "60%",
                "spouse_age_diff": 0, "coefficient_selection": "manual_review_required",
                "option_name": "standard",
            })

        factory = sessionmaker(bind=scoped, autoflush=False, expire_on_commit=False)
        first = _write(factory, expected_revision=0, factor_value="200")
        assert first["admission_revision"] == 1
        assert first["execution_allowed"] is False
        second = _write(factory, expected_revision=1, factor_value="210")
        assert second["admission_revision"] == 2
        assert _read(factory)["factor_value"] == "210"

        # Two real SERIALIZABLE transactions race with the same CAS token.
        def contender(value):
            try:
                return ("ok", _write(factory, expected_revision=2, factor_value=value))
            except PensionFactorWriteBlocked as exc:
                return ("blocked", str(exc))

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(contender, ("220", "221")))
        assert [kind for kind, _ in outcomes].count("ok") == 1
        assert [kind for kind, _ in outcomes].count("blocked") == 1
        assert outcomes[0][1] != outcomes[1][1]
        blocked_code = next(value for kind, value in outcomes if kind == "blocked")
        assert blocked_code in {
            "FACTOR_ADMISSION_REVISION_CONFLICT",
            "FACTOR_ADMISSION_SERIALIZATION_CONFLICT",
        }

        with factory() as db:
            count_before = db.query(ScenarioPensionFactorAdmission).count()
            latest = db.scalar(select(ScenarioPensionFactorAdmission.admission_revision)
                .order_by(ScenarioPensionFactorAdmission.admission_revision.desc()).limit(1))
            db.rollback()
        assert count_before == 3 and latest == 3

        # A failure after flush rolls the whole caller-owned transaction back.
        with pytest.raises(RuntimeError, match="forced after flush"):
            with factory() as db, db.begin():
                db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                _save_factor_admission(
                    db, client_id=7, scenario_id="s", decision_id="d",
                    expected_scenario_version=1, expected_admission_revision=3,
                    actor_id="planner-rollback", factor_value="230",
                    factor_evidence_type="PLANNER_ASSUMPTION",
                    factor_evidence_reference="must roll back",
                    _capability=_AUTHENTICATED_FACTOR_WRITE_CAPABILITY,
                )
                raise RuntimeError("forced after flush")
        with factory() as db:
            assert db.query(ScenarioPensionFactorAdmission).count() == count_before
            db.rollback()

        # Clone has no inherited professional admission.
        with scoped.begin() as conn:
            conn.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "clone", "client_id": 7, "name": "Clone",
                "status": "draft", "version": 1, "created_by": "test",
                "updated_by": "test",
            })
            conn.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d-clone", "scenario_id": "clone",
                "source_product_id": "p", "source_component_id": "c",
                "component_code": allowed_code, "amount": Decimal("400.00"),
                "action": "pension", "effective_date": date(2026, 10, 27),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": source["source_fingerprint"],
                "ruleset_digest_at_review": ruleset_digest(),
            })
            conn.execute(ScenarioDraftPensionElection.__table__.insert(), {
                "election_id": "e-clone", "scenario_id": "clone",
                "decision_id": "d-clone", "scenario_version": 1,
                "pension_start_date": date(2027, 9, 30), "target_year": 2027,
                "survivors_option": "60%", "spouse_age_diff": 0,
                "coefficient_selection": "manual_review_required",
                "option_name": "standard",
            })
        with pytest.raises(FactorAdmissionBlocked, match="FACTOR_ADMISSION_MISSING"):
            _read(factory, scenario_id="clone", decision_id="d-clone")

        # Source balance change invalidates the old admission but preserves it.
        with scoped.begin() as conn:
            conn.execute(PensionProductComponent.__table__.update().where(
                PensionProductComponent.component_id == "c").values(balance=Decimal("900.00")))
        with pytest.raises(Exception, match="PENSION_PERMISSION_SOURCE_STALE"):
            _read(factory)
        with factory() as db:
            assert db.query(ScenarioPensionFactorAdmission).count() == count_before
            db.rollback()

        # Application role can SELECT/INSERT but cannot UPDATE/DELETE.
        with scoped.begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{role}"'))
            assert conn.execute(text(
                f'SELECT count(*) FROM "{schema}".scenario_pension_factor_admissions')).scalar_one() == count_before
        for statement in (
            f'UPDATE "{schema}".scenario_pension_factor_admissions SET actor_id=\'x\'',
            f'DELETE FROM "{schema}".scenario_pension_factor_admissions',
        ):
            with pytest.raises(DBAPIError):
                with scoped.begin() as conn:
                    conn.execute(text(f'SET LOCAL ROLE "{role}"'))
                    conn.execute(text(statement))

        # Even the owner is stopped by the immediate append-only trigger.
        for statement in (
            f'UPDATE "{schema}".scenario_pension_factor_admissions SET actor_id=\'x\'',
            f'DELETE FROM "{schema}".scenario_pension_factor_admissions',
        ):
            with pytest.raises(DBAPIError) as exc:
                with scoped.begin() as conn:
                    conn.execute(text(statement))
            assert getattr(exc.value.orig, "pgcode", None) == "P7501"

        # The isolated migration supports downgrade and upgrade without touching
        # the database-wide Alembic version table.
        with scoped.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            original_op = migration.op
            try:
                migration.op = Operations(MigrationContext.configure(conn))
                migration.downgrade()
                assert "scenario_pension_factor_admissions" not in inspect(conn).get_table_names(schema=schema)
                monkeypatch.setenv("CRTISBA_APPLICATION_DB_ROLE", role)
                migration.upgrade()
                assert "scenario_pension_factor_admissions" in inspect(conn).get_table_names(schema=schema)
            finally:
                migration.op = original_op
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        scoped.dispose()
        engine.dispose()
