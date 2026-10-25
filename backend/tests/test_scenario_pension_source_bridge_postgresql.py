"""SC-04/P3: real PostgreSQL shared-transaction boundary test.

Canonical producer is replaced by a SQL-backed probe so this test establishes
same-snapshot guarantees, not canonical registry completeness. The existing
canonical registry has separate contract tests.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import os
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
from app.services.scenario_draft_service import _source_evidence
from app.services import professional_source_snapshot_service as canonical
from app.services import scenario_pension_source_bridge_service as bridge

load_all_models()


def _url():
    value = os.getenv("SCENARIO_TEST_POSTGRES_URL")
    if not value:
        pytest.skip("dedicated test PostgreSQL URL not supplied")
    parsed = urlsplit(value)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("PostgreSQL must be local")
    if parsed.path != "/retire_v2_scenario_test":
        pytest.fail("only retire_v2_scenario_test is permitted")
    return value


def test_bridge_reads_canonical_probe_in_exact_scenario_snapshot(monkeypatch):
    engine = create_engine(_url(), isolation_level="READ COMMITTED")
    schema = "sc04_bridge_" + uuid.uuid4().hex[:16]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped, expire_on_commit=False)
    old = _source_evidence(
        SimpleNamespace(client_id=7, product_id="p", version=1,
                        product_type="קרן פנסיה", source_kind="manual",
                        source_identity="manual:7:p"),
        SimpleNamespace(product_id="p", component_id="c",
                        component_code="תגמולי_עובד_עד_2000", balance=Decimal("100.00")),
    )
    started, release = threading.Event(), threading.Event()
    outcomes, errors, observed = {}, {}, {}

    def canonical_sql_probe(db, client_id, *, as_of):
        # The scenario manifest has already performed SELECTs before this callback.
        observed["isolation"] = db.scalar(text("SHOW transaction_isolation"))
        observed["read_only"] = db.scalar(text("SHOW transaction_read_only"))
        observed["version"] = db.scalar(select(ScenarioDraft.version).where(
            ScenarioDraft.client_id == client_id, ScenarioDraft.scenario_id == "s"))
        started.set()
        assert release.wait(10), "concurrent writer timed out"
        product_version = db.scalar(select(PensionProduct.version).where(
            PensionProduct.client_id == client_id, PensionProduct.product_id == "p"))
        observed["product_version"] = product_version
        return {"pension_sources": [{
            "kind": "manual", "source_id": "manual:probe",
        }]}

    def run_reader():
        try:
            outcomes["first"] = bridge.build_pension_source_bridge_snapshot(
                factory, client_id=7, scenario_id="s")
        except BaseException as exc:
            errors["reader"] = exc

    try:
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        with scoped.begin() as conn:
            for table in (Client.__table__, PensionProduct.__table__,
                          PensionProductComponent.__table__, ScenarioDraft.__table__,
                          ScenarioDraftDecision.__table__):
                table.create(conn)
            conn.execute(Client.__table__.insert(), {
                "client_id": 7, "display_name": "Bridge Synthetic", "id_number": "SC04-7"})
            conn.execute(PensionProduct.__table__.insert(), {
                "product_id": "p", "client_id": 7, "source_kind": "manual",
                "source_identity": "manual:7:p", "product_name": "Synthetic",
                "product_type": "קרן פנסיה", "account_reference": "SYNTHETIC",
                "historical_employers": [], "version": 1,
                "created_by": "test", "updated_by": "test"})
            conn.execute(PensionProductComponent.__table__.insert(), {
                "component_id": "c", "product_id": "p",
                "component_code": "תגמולי_עובד_עד_2000", "balance": Decimal("100.00")})
            conn.execute(ScenarioDraft.__table__.insert(), {
                "scenario_id": "s", "client_id": 7, "name": "Bridge Synthetic",
                "status": "draft", "version": 1, "created_by": "test",
                "updated_by": "test"})
            conn.execute(ScenarioDraftDecision.__table__.insert(), {
                "decision_id": "d", "scenario_id": "s", "source_product_id": "p",
                "source_component_id": "c", "component_code": "תגמולי_עובד_עד_2000",
                "amount": Decimal("40.00"), "action": "pension",
                "effective_date": date(2026, 10, 24), "validation_state": "unverified",
                "product_version_at_review": 1,
                "source_fingerprint_at_review": old["source_fingerprint"],
                "ruleset_digest_at_review": "a"*64,
                "permission_preview_id_at_review": "b"*64})
        monkeypatch.setattr(canonical, "_snapshot", canonical_sql_probe)
        thread = threading.Thread(target=run_reader)
        thread.start()
        assert started.wait(10), "snapshot probe never reached"
        with scoped.begin() as conn:
            conn.execute(ScenarioDraft.__table__.update().where(
                ScenarioDraft.scenario_id == "s").values(version=2))
            conn.execute(PensionProduct.__table__.update().where(
                PensionProduct.product_id == "p").values(version=2))
        release.set()
        thread.join(10)
        assert not thread.is_alive()
        assert errors == {}
        assert observed["isolation"] == "repeatable read"
        assert observed["read_only"] == "on"
        assert observed["version"] == 1
        assert observed["product_version"] == 1
        first = outcomes["first"]
        assert first["scenario_version"] == 1
        assert first["bridge_state"] == "UNRESOLVED"
        assert first["execution_allowed"] is False
        assert first["financial_result"] is None
        # Current version is now 2 and source-review identity is stale,
        # so a subsequent complete snapshot must fail closed.
        monkeypatch.setattr(canonical, "_snapshot", lambda db, client_id, *, as_of: {
            "pension_sources": [{"kind": "manual", "source_id": "manual:probe"}]})
        fresh = bridge.build_pension_source_bridge_snapshot(factory, client_id=7, scenario_id="s")
        assert fresh["bridge_state"] == "BLOCKED"
    finally:
        release.set()
        if "thread" in locals() and thread.is_alive():
            thread.join(10)
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()
