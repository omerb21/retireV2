"""Opt-in PostgreSQL 16 coverage for temporal migration and row locking."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.db.base import load_all_models
from app.models.canonical_conversion import batches, conversions, pensions
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.models.canonical_pension_temporal_decision import CanonicalPensionTemporalDecision as Decision
from app.schemas.canonical_conversion import ReversalRequest
from app.schemas.canonical_manual_pension_source import ConversionTemporalDecisionWrite
from app.services import pension_temporal_basis_service as temporal
from app.services.canonical_component_conversion_service import execute, reverse
from app.services.pension_product_service import PensionProductError
from test_canonical_component_conversion import request, seeded
from test_canonical_conversion_migration import migrate
from test_recovery_migration_postgresql import postgres_url

load_all_models()


def decision(source_version=1, decision_version=0, actor="pg-test"):
    return ConversionTemporalDecisionWrite(expected_source_version=source_version,
        expected_decision_version=decision_version,
        temporal_authority={"authority_kind": "none"}, actor=actor)


def test_postgresql_temporal_migration_is_additive_and_lossless(postgres_url):
    migrate(postgres_url, "upgrade", "e0f6b3c9d187")
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
            db.execute(text("INSERT INTO canonical_manual_pension_sources "
                "(manual_pension_source_id,client_id,input_mode,monthly_amount,indexation_method,fixed_indexation_rate) "
                "VALUES('none',1,'entered','100.00','none',NULL),"
                "('fixed',1,'entered','100.00','fixed','0.02'),"
                "('cpi',1,'entered','100.00','cpi',NULL)"))
        migrate(postgres_url, "upgrade", "f1a7c4d0e298")
        column = next(c for c in inspect(engine).get_columns("canonical_manual_pension_sources")
                      if c["name"] == "temporal_authority_explicit")
        assert not column["nullable"] and column["default"] is None
        with engine.connect() as db:
            assert db.execute(text("SELECT indexation_method,fixed_indexation_rate,temporal_authority_explicit "
                "FROM canonical_manual_pension_sources ORDER BY manual_pension_source_id")).all() == [
                    ("cpi", None, False), ("fixed", "0.02", False), ("none", None, False)]
            assert db.scalar(text("SELECT count(*) FROM canonical_pension_temporal_decisions")) == 0
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "f1a7c4d0e298"
        migrate(postgres_url, "downgrade", "e0f6b3c9d187")
        assert "temporal_authority_explicit" not in {
            c["name"] for c in inspect(engine).get_columns("canonical_manual_pension_sources")}
    finally:
        engine.dispose()


def test_postgresql_persisted_contradictory_manual_authority_fails_closed(postgres_url):
    migrate(postgres_url, "upgrade", "f1a7c4d0e298")
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
            db.execute(text("INSERT INTO canonical_manual_pension_sources "
                "(manual_pension_source_id,client_id,input_mode,monthly_amount,base_amount_effective_date,"
                "indexation_method,fixed_indexation_rate,temporal_authority_explicit) "
                "VALUES('contradictory',1,'entered','100.00','2030-01-15','cpi',NULL,TRUE)"))
        with Session(engine) as db:
            row = db.get(Manual, "contradictory")
            with pytest.raises(PensionProductError) as failure:
                temporal.manual(row, 1)
        assert failure.value.code == "TEMPORAL_DECISION_STRUCTURE_INVALID"
    finally:
        engine.dispose()


def test_postgresql_first_create_and_reversal_races_serialize(postgres_url):
    migrate(postgres_url, "upgrade", "f1a7c4d0e298")
    engine = create_engine(postgres_url, pool_size=6)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        source = seeded(engine)
        with Session(engine) as db, db.begin():
            created = execute(db, 1, request(source, destination="pension"), "test")
        destination_id = created["conversions"][0]["destination_id"]
        gate = Barrier(2)

        def first_create(actor):
            gate.wait(timeout=20)
            try:
                with Session(engine) as db, db.begin():
                    return temporal.write_conversion(db, 1, destination_id, decision(actor=actor))["outcome"]
            except PensionProductError as error:
                return error.code

        with ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(first_create, ("a", "b")))
        assert sorted(outcomes) == ["TEMPORAL_DECISION_CREATED", "TEMPORAL_DECISION_VERSION_STALE"]
        with Session(engine) as db:
            row = db.get(Decision, destination_id)
            assert row.version == 1 and row.source_version_at_decision == 1

        with Session(engine) as db, pytest.raises(PensionProductError) as failure:
            temporal.write_conversion(db, 1, destination_id, decision(source_version=2, decision_version=1))
        assert failure.value.code == "TEMPORAL_SOURCE_VERSION_STALE"
        with Session(engine) as db, pytest.raises(PensionProductError) as failure:
            temporal.write_conversion(db, 1, destination_id, decision(source_version=1, decision_version=0))
        assert failure.value.code == "TEMPORAL_DECISION_VERSION_STALE"

        with Session(engine) as db:
            destination = db.execute(select(pensions).where(
                pensions.c.pension_destination_id == destination_id)).mappings().one()
            conversion_row = db.execute(select(conversions).where(
                conversions.c.conversion_id == destination["conversion_id"])).mappings().one()
            batch = db.execute(select(batches).where(
                batches.c.batch_id == conversion_row["batch_id"])).mappings().one()
            before = temporal.conversion(db, 1, destination, conversion_row, batch)
        with engine.begin() as db:
            db.execute(text("DROP TRIGGER trg_canonical_pension_destinations_canonical "
                            "ON canonical_pension_destinations"))
            db.execute(pensions.update().where(
                pensions.c.pension_destination_id == destination_id).values(version=2))
        with Session(engine) as db, db.begin():
            rebound = temporal.write_conversion(db, 1, destination_id,
                decision(source_version=2, decision_version=1, actor="reauthorizer"))
        assert rebound["outcome"] == "TEMPORAL_DECISION_REAUTHORIZED"
        assert rebound["temporal_authority"]["temporal_semantic_fingerprint"] == before[
            "temporal_semantic_fingerprint"]
        assert rebound["temporal_authority"]["temporal_source_fingerprint"] != before[
            "temporal_source_fingerprint"]
        with Session(engine) as db:
            row = db.get(Decision, destination_id)
            assert row.version == 2 and row.source_version_at_decision == 2

        second_source = seeded(engine)
        with Session(engine) as db, db.begin():
            second = execute(db, 1, request(second_source, destination="pension"), "test")
        second_destination = second["conversions"][0]["destination_id"]
        conversion_id = second["conversions"][0]["conversion_id"]
        expected_product_version = second["product_version"]
        race = Barrier(2)

        def authorize():
            race.wait(timeout=20)
            try:
                with Session(engine) as db, db.begin():
                    return temporal.write_conversion(db, 1, second_destination, decision())["outcome"]
            except PensionProductError as error:
                return error.code

        def undo():
            race.wait(timeout=20)
            with Session(engine) as db, db.begin():
                reverse(db, 1, conversion_id, ReversalRequest(expected_conversion_version=1,
                    expected_product_version=expected_product_version,
                    idempotency_key="temporal-pg-race", reason="test"), "test")
            return "reversed"

        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(authorize), pool.submit(undo)]
            outcomes = [future.result(timeout=45) for future in futures]
        assert outcomes[1] == "reversed"
        assert outcomes[0] in {"TEMPORAL_DECISION_CREATED", "TEMPORAL_SOURCE_NOT_CURRENT"}
        with Session(engine) as db:
            destination = db.execute(select(pensions).where(
                pensions.c.pension_destination_id == second_destination)).mappings().one()
            assert destination["status"] == "reversed" and destination["version"] == 2
            row = db.get(Decision, second_destination)
            if outcomes[0] == "TEMPORAL_DECISION_CREATED":
                assert row is not None and row.source_version_at_decision == 1
            else:
                assert row is None
    finally:
        engine.dispose()
