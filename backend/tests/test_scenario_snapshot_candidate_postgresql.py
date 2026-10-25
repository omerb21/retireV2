"""SC-03A/C real PostgreSQL snapshot-owner acceptance evidence.

The URL must identify the dedicated local retire_v2_scenario_test database.
"""
from datetime import date
from decimal import Decimal
import os
from types import SimpleNamespace
import threading
import uuid
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.models.client import Client
from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.services import scenario_snapshot_candidate_service as subject
from app.services.scenario_draft_service import _source_evidence


HASH_A = "a" * 64
HASH_B = "b" * 64
CODE = "תגמולי_עובד_עד_2000"

load_all_models()


def _url():
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated PostgreSQL test URL not supplied")
    parsed = urlsplit(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("SC-03 PostgreSQL evidence requires a local host")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("SC-03 PostgreSQL evidence requires retire_v2_scenario_test")
    return value


def _source(version: int, balance: str) -> dict:
    return _source_evidence(
        SimpleNamespace(
            client_id=7, product_id="p", version=version,
            product_type="קרן פנסיה", source_kind="manual",
            source_identity="manual:7:p",
        ),
        SimpleNamespace(
            product_id="p", component_id="c", component_code=CODE,
            balance=Decimal(balance),
        ),
    )


def test_manifest_and_candidate_share_read_only_repeatable_snapshot(monkeypatch):
    engine = create_engine(_url(), isolation_level="READ COMMITTED")
    if engine.dialect.name != "postgresql":
        pytest.fail("SCENARIO_TEST_POSTGRES_URL must point to PostgreSQL")
    schema = "sc03_snapshot_" + uuid.uuid4().hex[:16]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped, expire_on_commit=False)
    started = threading.Event()
    release = threading.Event()
    observed = {}
    result_box = {}
    error_box = {}
    original = subject.build_inert_manifest
    old_source = _source(1, "100.00")
    new_source = _source(2, "200.00")
    statements = []

    def paused_build(db, client_id, scenario_id):
        observed["isolation"] = db.scalar(text("SHOW transaction_isolation"))
        observed["read_only"] = db.scalar(text("SHOW transaction_read_only"))
        observed["server_version"] = db.scalar(text("SHOW server_version"))
        observed["first_version"] = db.scalar(select(ScenarioDraft.version).where(
            ScenarioDraft.client_id == client_id,
            ScenarioDraft.scenario_id == scenario_id,
        ))
        started.set()
        assert release.wait(10), "writer did not complete"
        return original(db, client_id, scenario_id)

    def capture(_conn, _cursor, statement, _parameters, _context, _many):
        if threading.current_thread() is not threading.main_thread():
            statements.append(statement)

    def reader():
        try:
            result_box["value"] = subject.build_manifest_candidate_snapshot(
                factory, client_id=7, scenario_id="s",
            )
        except BaseException as exc:  # surfaced in the owning test thread
            error_box["error"] = exc

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        with scoped.begin() as connection:
            for table in (
                Client.__table__, PensionProduct.__table__,
                PensionProductComponent.__table__, ScenarioDraft.__table__,
                ScenarioDraftDecision.__table__,
            ):
                table.create(connection)
            connection.execute(Client.__table__.insert(), {
                "client_id": 7, "display_name": "Synthetic", "id_number": "SC03-7",
            })
            connection.execute(PensionProduct.__table__.insert(), {
                "product_id": "p", "client_id": 7, "source_kind": "manual",
                "source_identity": "manual:7:p", "product_name": "Synthetic",
                "product_type": "קרן פנסיה", "account_reference": "SYNTHETIC",
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            connection.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "c", "product_id": "p",
                "component_code": CODE, "balance": Decimal("100.00"),
            })
            connection.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "s", "client_id": 7, "name": "Synthetic",
                "status": "draft", "version": 1,
                "created_by": "test", "updated_by": "test",
            })
            connection.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d", "scenario_id": "s",
                "source_product_id": "p", "source_component_id": "c",
                "component_code": CODE, "amount": Decimal("40.00"),
                "action": "pension", "effective_date": date(2026, 10, 24),
                "validation_state": "unverified", "product_version_at_review": 1,
                "source_fingerprint_at_review": old_source["source_fingerprint"],
                "ruleset_digest_at_review": HASH_A,
                "permission_preview_id_at_review": HASH_B,
            })
        monkeypatch.setattr(subject, "build_inert_manifest", paused_build)
        from sqlalchemy import event
        event.listen(scoped, "before_cursor_execute", capture)
        thread = threading.Thread(target=reader)
        thread.start()
        assert started.wait(10), (
            "reader did not acquire its first snapshot: "
            + repr(error_box.get("error"))
            + " caused by "
            + repr(getattr(error_box.get("error"), "__cause__", None))
        )
        with scoped.begin() as writer:
            writer.execute(ScenarioDraft.__table__.update().where(
                ScenarioDraft.scenario_id == "s",
            ).values(version=2))
            writer.execute(PensionProduct.__table__.update().where(
                PensionProduct.product_id == "p",
            ).values(version=2))
            writer.execute(PensionProductComponent.__table__.update().where(
                PensionProductComponent.component_id == "c",
            ).values(balance=Decimal("200.00")))
            writer.execute(ScenarioDraftDecision.__table__.update().where(
                ScenarioDraftDecision.decision_id == "d",
            ).values(
                amount=Decimal("60.00"), product_version_at_review=2,
                source_fingerprint_at_review=new_source["source_fingerprint"],
            ))
        release.set()
        thread.join(10)
        assert not thread.is_alive()
        assert error_box == {}
        first = result_box["value"]
        assert observed["isolation"] == "repeatable read"
        assert observed["read_only"] == "on"
        assert observed["server_version"].startswith("16.")
        assert observed["first_version"] == 1
        assert first["manifest"]["scenario_version"] == 1
        assert first["manifest"]["decisions"][0]["amount"] == "40.00"
        assert first["manifest"]["decisions"][0]["source"]["balance"] == "100.00"
        assert first["candidate"]["evidence_state"] == "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
        assert first["candidate"]["execution_allowed"] is False
        monkeypatch.setattr(subject, "build_inert_manifest", original)
        fresh = subject.build_manifest_candidate_snapshot(
            factory, client_id=7, scenario_id="s",
        )
        assert fresh["manifest"]["scenario_version"] == 2
        assert fresh["manifest"]["decisions"][0]["amount"] == "60.00"
        assert fresh["manifest"]["decisions"][0]["source"]["balance"] == "200.00"
        assert fresh["candidate"]["evidence_state"] == "STRUCTURALLY_CONSISTENT_NOT_ADMITTED"
        reader_sql = "\n".join(statements).upper()
        assert not any(token in reader_sql for token in (
            "INSERT INTO", "UPDATE ", "DELETE FROM", "TRUNCATE ", "CREATE ", "ALTER ",
        ))
    finally:
        release.set()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()
