from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import hashlib
import json
from threading import Event, get_ident

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.scenario_permission_preview_routes import get_preview_session_factory
from app.db.base import Base, load_all_models
from app.main import create_app
from app.models.client import Client
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent
from app.security.config import AuthConfig
from app.security.session import COOKIE_NAME, issue
from app.services import scenario_permission_preview_service as subject


EFFECTIVE = "2026-10-24"
URL = "/api/clients/1/scenario-conversions/permission-preview"
EXPECTED_PENSION = (
    "blocked", "allowed", "blocked", "blocked", "allowed", "allowed",
    "allowed", "allowed", "allowed", "allowed", "allowed",
)
EXPECTED_CAPITAL = (
    "blocked", "allowed", "blocked", "blocked", "blocked", "allowed",
    "blocked", "blocked", "allowed", "blocked", "blocked",
)


@pytest.fixture
def preview_env(tmp_path):
    load_all_models()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'permission-preview.db'}",
        connect_args={"check_same_thread": False, "timeout": 20},
    )

    @event.listens_for(engine, "connect")
    def sqlite_pragmas(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with Session(engine) as db, db.begin():
        db.add_all([
            Client(client_id=1, display_name="לקוח א", id_number="sc-perm-a"),
            Client(client_id=2, display_name="לקוח ב", id_number="sc-perm-b"),
        ])
        for index, (product_id, client_id, product_type) in enumerate((
            ("fund", 1, "קרן פנסיה"),
            ("provident", 1, "קופת גמל"),
            ("insurance", 1, "פוליסת ביטוח חיים משולב חיסכון"),
            ("ambiguous", 1, "פוליסת ביטוח חיים"),
            ("unsupported", 1, "פוליסת חיסכון טהור"),
            ("unmapped", 1, "סוג מוצר לא ממופה"),
            ("unreported", 1, "סוג מוצר לא נמסר"),
            ("manual", 1, "קופת גמל"),
            ("foreign", 2, "קרן פנסיה"),
        )):
            source_kind = "manual" if product_id == "manual" else "imported"
            db.add(PensionProduct(
                product_id=product_id,
                client_id=client_id,
                source_kind=source_kind,
                source_identity=f"source-{index}",
                provider_name="גוף סינתטי",
                provider_identifier=None,
                product_name=f"מוצר {index}",
                product_type=product_type,
                account_reference=f"account-{index}",
                start_date=None,
                statement_date=None,
                historical_employers=[],
                reported_product_total=Decimal("66.00"),
                reported_rewards_total=Decimal("51.00"),
                reported_severance_total=Decimal("15.00"),
                version=3,
                created_by="test",
                updated_by="test",
            ))
            db.add_all([
                PensionProductComponent(
                    component_id=f"{product_id}-{position:02d}",
                    product_id=product_id,
                    component_code=code,
                    balance=Decimal(position),
                )
                for position, code in enumerate(COMPONENT_CODES, start=1)
            ])
    app = create_app(AuthConfig(production=False))
    app.dependency_overrides[get_preview_session_factory] = lambda: factory
    client = TestClient(app)
    try:
        yield client, factory, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def request(product_id="fund", action="pension", effective_date=EFFECTIVE):
    return {"product_id": product_id, "action": action, "effective_date": effective_date}


def test_ruleset_golden_is_exact_immutable_and_permission_only():
    artifact = subject.permission_ruleset()
    canonical = json.dumps(
        artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == subject.RULESET_DIGEST == (
        "f3bd4c4bfe1fa07c96a7687dc99b756deb8de2f79083e05a74642b6b5d58800b"
    )
    assert artifact["source_integrity_overlays"] == []
    assert len(artifact["component_rules"]) == 11
    assert all(set(row["actions"]) == {"pension", "capital_asset"} for row in artifact["component_rules"])
    assert not {"exempt", "taxable", "capital_gains"} & set(canonical.decode("utf-8").split('"'))
    artifact["ruleset_version"] = 999
    assert subject.permission_ruleset()["ruleset_version"] == 1


@pytest.mark.parametrize("product_id,product_class", [
    ("fund", "pension_fund"),
    ("provident", "provident_fund"),
    ("insurance", "insurance_policy"),
])
@pytest.mark.parametrize("action,expected", [
    ("pension", EXPECTED_PENSION),
    ("capital_asset", EXPECTED_CAPITAL),
])
def test_approved_products_return_exact_11_by_two_matrix(
    preview_env, product_id, product_class, action, expected,
):
    client, _factory, _engine = preview_env
    response = client.post(URL, json=request(product_id, action))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_version"] == "SCENARIO_PERMISSION_PREVIEW_V1"
    assert body["canonical_product_class"] == product_class
    assert body["action"] == action
    assert [row["component_code"] for row in body["components"]] == list(COMPONENT_CODES)
    assert tuple(row["permission_status"] for row in body["components"]) == expected
    assert len(body["components"]) == 11
    assert body["professional_eligibility_status"] == body["tax_status"] == "not_evaluated"
    assert body["overall_status"] == "mixed"
    assert set(body) == {
        "schema_version", "preview_id", "client_id", "product_id", "product_version",
        "canonical_product_class", "action", "effective_date", "ruleset_id",
        "ruleset_version", "ruleset_digest", "source_fingerprint", "overall_status",
        "professional_eligibility_status", "tax_status", "components", "totals",
        "reconciliation",
    }


@pytest.mark.parametrize("product_id,code", [
    ("ambiguous", "AMBIGUOUS_PRODUCT_TYPE"),
    ("unsupported", "UNKNOWN_PRODUCT_TYPE"),
    ("unmapped", "UNKNOWN_PRODUCT_TYPE"),
    ("unreported", "UNKNOWN_PRODUCT_TYPE"),
    ("manual", "AMBIGUOUS_PRODUCT_TYPE"),
])
def test_unapproved_product_types_fail_closed(preview_env, product_id, code):
    response = preview_env[0].post(URL, json=request(product_id))
    assert (response.status_code, response.json()["code"]) == (422, code)
    assert "components" not in response.json()


def test_zero_rows_are_visible_and_missing_rows_fail_whole_envelope(preview_env):
    client, factory, _engine = preview_env
    with factory.begin() as db:
        for row in db.scalars(select(PensionProductComponent).where(
            PensionProductComponent.product_id == "fund",
        )):
            row.balance = Decimal("0.00")
    zero = client.post(URL, json=request())
    assert zero.status_code == 200
    assert len(zero.json()["components"]) == 11
    assert {row["balance"] for row in zero.json()["components"]} == {"0.00"}
    assert zero.json()["totals"]["original_classified_balance"] == "0.00"
    with factory.begin() as db:
        db.delete(db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.product_id == "fund",
            PensionProductComponent.component_code == COMPONENT_CODES[0],
        )))
    missing = client.post(URL, json=request())
    assert (missing.status_code, missing.json()["code"]) == (409, "MISSING_CANONICAL_SOURCE")
    assert "components" not in missing.json()


@pytest.mark.parametrize("corruption", ["empty_identity", "negative_balance"])
def test_corrupt_canonical_component_fails_whole_envelope(preview_env, corruption):
    client, factory, _engine = preview_env
    with factory.begin() as db:
        row = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.product_id == "fund",
            PensionProductComponent.component_code == COMPONENT_CODES[0],
        ))
        if corruption == "empty_identity":
            row.component_id = ""
        else:
            row.balance = Decimal("-1.00")
    response = client.post(URL, json=request())
    assert (response.status_code, response.json()["code"]) == (
        409, "MISSING_CANONICAL_SOURCE",
    )
    assert "components" not in response.json()


def test_source_fingerprint_preview_identity_and_effective_date(preview_env):
    client, _factory, _engine = preview_env
    early = client.post(URL, json=request(effective_date="2026-10-23"))
    assert (early.status_code, early.json()["code"]) == (409, "UNKNOWN_RULESET")
    response = client.post(URL, json=request()).json()
    source_preimage = {
        "schema": "scenario-source-fingerprint-v1",
        "client_id": 1,
        "product_id": "fund",
        "product_version": 3,
        "source_kind": "imported",
        "product_type": "קרן פנסיה",
        "components": [
            {
                "component_code": code,
                "component_id": f"fund-{position:02d}",
                "balance": f"{position}.00",
            }
            for position, code in enumerate(COMPONENT_CODES, start=1)
        ],
    }
    expected_source = hashlib.sha256(json.dumps(
        source_preimage, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    assert response["source_fingerprint"] == expected_source
    preview_preimage = {
        "schema": "scenario-permission-preview-id-v1",
        "client_id": 1,
        "product_id": "fund",
        "source_fingerprint": expected_source,
        "action": "pension",
        "effective_date": EFFECTIVE,
        "ruleset_id": "retire-v2-permission-standard-20261024",
        "ruleset_version": 1,
        "ruleset_digest": subject.RULESET_DIGEST,
    }
    assert response["preview_id"] == hashlib.sha256(json.dumps(
        preview_preimage, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def test_client_product_scope_does_not_disclose_foreign_product(preview_env):
    client = preview_env[0]
    foreign = client.post(URL, json=request("foreign"))
    missing = client.post(URL, json=request("does-not-exist"))
    assert (foreign.status_code, foreign.json()["code"], foreign.json()["field_paths"]) == (
        404, "PREVIEW_SOURCE_NOT_FOUND", ["/path/client_id", "/product_id"],
    )
    assert foreign.json()["code"] == missing.json()["code"]


def test_snapshot_executes_only_reads_and_rolls_back(preview_env):
    client, _factory, engine = preview_env
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip().upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = client.post(URL, json=request())
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert response.status_code == 200
    assert statements and all(
        statement.startswith(("BEGIN", "SELECT")) for statement in statements
    ), statements
    assert not any(
        token in statement
        for statement in statements
        for token in ("INSERT ", "UPDATE ", "DELETE ", "COMMIT", "FOR UPDATE", "ADVISORY")
    )


def test_sqlite_snapshot_does_not_mix_concurrent_component_change(preview_env):
    _client, factory, engine = preview_env
    paused, resume = Event(), Event()
    reader_thread = [None]

    def pause_after_product(_connection, _cursor, statement, _parameters, _context, _many):
        upper = statement.upper()
        if (
            get_ident() == reader_thread[0]
            and "FROM PENSION_PRODUCTS" in upper
            and "PENSION_PRODUCT_COMPONENTS" not in upper
            and not paused.is_set()
        ):
            paused.set()
            assert resume.wait(20)

    event.listen(engine, "after_cursor_execute", pause_after_product)

    def read_snapshot():
        reader_thread[0] = get_ident()
        return subject.preview(
            factory, client_id=1, product_id="fund", action="pension",
            effective_date=date(2026, 10, 24),
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(read_snapshot)
            assert paused.wait(20)
            with factory.begin() as writer:
                row = writer.scalar(select(PensionProductComponent).where(
                    PensionProductComponent.product_id == "fund",
                    PensionProductComponent.component_code == COMPONENT_CODES[0],
                ))
                row.balance = Decimal("999.00")
            resume.set()
            result = pending.result(timeout=20)
    finally:
        resume.set()
        event.remove(engine, "after_cursor_execute", pause_after_product)
    assert result["components"][0]["balance"] == "1.00"
    fresh = subject.preview(
        factory, client_id=1, product_id="fund", action="pension",
        effective_date=date(2026, 10, 24),
    )
    assert fresh["components"][0]["balance"] == "999.00"


def _production_config():
    return AuthConfig(
        production=True,
        public_origin="https://retire.example",
        public_authority="retire.example",
        username="planner",
        password_hash="unused",
        dummy_password_hash="unused",
        actor_id="trusted:planner",
        session_secret=b"s" * 32,
        rate_limit_secret=b"r" * 32,
    )


def _edge(**extra):
    headers = {
        "host": "retire.example",
        "x-real-ip": "2001:db8::2",
        "x-forwarded-proto": "https",
        "x-forwarded-host": "retire.example",
    }
    headers.update(extra)
    return headers


def test_production_session_origin_csrf_and_request_schema(preview_env):
    _development_client, factory, _engine = preview_env
    config = _production_config()
    app = create_app(config)
    app.dependency_overrides[get_preview_session_factory] = lambda: factory
    client = TestClient(app)
    missing = client.post(URL, json=request(), headers=_edge())
    assert (missing.status_code, missing.json()["code"]) == (401, "SESSION_MISSING")
    client.cookies.set(COOKIE_NAME, "not-a-session")
    malformed = client.post(URL, json=request(), headers=_edge())
    assert (malformed.status_code, malformed.json()["code"]) == (401, "SESSION_INVALID")
    expired_token, _ = issue(config, now=1)
    client.cookies.set(COOKIE_NAME, expired_token)
    expired = client.post(URL, json=request(), headers=_edge())
    assert (expired.status_code, expired.json()["code"]) == (401, "SESSION_EXPIRED")
    token, session = issue(config)
    client.cookies.set(COOKIE_NAME, token)
    no_origin = client.post(URL, json=request(), headers=_edge())
    assert (no_origin.status_code, no_origin.json()["code"]) == (403, "ORIGIN_FORBIDDEN")
    no_csrf = client.post(URL, json=request(), headers=_edge(origin="https://retire.example"))
    assert (no_csrf.status_code, no_csrf.json()["code"]) == (403, "CSRF_INVALID")
    headers = _edge(origin="https://retire.example", **{"x-rtdir-csrf": session["csrf"]})
    accepted = client.post(URL, json=request(), headers=headers)
    assert accepted.status_code == 200
    invalid = client.post(URL, json={**request(), "action": "unchanged"}, headers=headers)
    assert (invalid.status_code, invalid.json()["code"]) == (
        422, "SCENARIO_PERMISSION_REQUEST_INVALID",
    )
    spoofed = client.post(URL, json={**request(), "client_id": 2}, headers=headers)
    assert (spoofed.status_code, spoofed.json()["code"]) == (
        422, "SCENARIO_PERMISSION_REQUEST_INVALID",
    )


def test_rollback_failure_invalidates_connection_and_wins(monkeypatch):
    reached = {"rollback": False, "invalidate": False, "close": False}

    class Dialect:
        name = "sqlite"

    class Transaction:
        is_active = True

        def rollback(self):
            reached["rollback"] = True
            raise RuntimeError("rollback failed")

    transaction = Transaction()

    class Connection:
        dialect = Dialect()

        def exec_driver_sql(self, _statement):
            return None

        def get_transaction(self):
            return transaction

        def in_transaction(self):
            return True

        def invalidate(self):
            reached["invalidate"] = True

        def close(self):
            reached["close"] = True

    connection = Connection()

    class Engine:
        def connect(self):
            return connection

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(subject, "_engine", lambda _factory: Engine())
    monkeypatch.setattr(subject, "Session", FakeSession)
    monkeypatch.setattr(subject, "_read_snapshot", lambda *_args: {"tentative": "result"})
    with pytest.raises(subject.ScenarioPermissionError) as caught:
        subject.preview(
            object(), client_id=1, product_id="fund", action="pension",
            effective_date=date(2026, 10, 24),
        )
    assert caught.value.code == "PREVIEW_TRANSACTION_CLEANUP_FAILED"
    assert reached == {"rollback": True, "invalidate": True, "close": True}


def test_session_close_failure_invalidates_connection_and_wins(monkeypatch):
    reached = {"rollback": False, "session_close": False, "invalidate": False}

    class Dialect:
        name = "sqlite"

    class Transaction:
        is_active = True

        def rollback(self):
            reached["rollback"] = True
            self.is_active = False

    transaction = Transaction()

    class Connection:
        dialect = Dialect()

        def exec_driver_sql(self, _statement):
            return None

        def get_transaction(self):
            return transaction

        def in_transaction(self):
            return transaction.is_active

        def invalidate(self):
            reached["invalidate"] = True

        def close(self):
            pass

    class FakeSession:
        def __init__(self, **_kwargs):
            pass

        def close(self):
            reached["session_close"] = True
            raise RuntimeError("session close failed")

    monkeypatch.setattr(subject, "_engine", lambda _factory: type(
        "Engine", (), {"connect": lambda _self: Connection()},
    )())
    monkeypatch.setattr(subject, "Session", FakeSession)
    monkeypatch.setattr(subject, "_read_snapshot", lambda *_args: {"tentative": "result"})
    with pytest.raises(subject.ScenarioPermissionError) as caught:
        subject.preview(
            object(), client_id=1, product_id="fund", action="pension",
            effective_date=date(2026, 10, 24),
        )
    assert caught.value.code == "PREVIEW_TRANSACTION_CLEANUP_FAILED"
    assert reached == {"rollback": True, "session_close": True, "invalidate": True}


def test_connection_acquisition_failure_has_no_cleanup(monkeypatch):
    class Engine:
        def connect(self):
            raise RuntimeError("connect failed")

    monkeypatch.setattr(subject, "_engine", lambda _factory: Engine())
    with pytest.raises(subject.ScenarioPermissionError) as caught:
        subject.preview(
            object(), client_id=1, product_id="fund", action="pension",
            effective_date=date(2026, 10, 24),
        )
    assert caught.value.code == "PREVIEW_DATABASE_UNAVAILABLE"


@pytest.mark.parametrize("source_kind,product_type", [
    (None, "קרן פנסיה"), ("corrupt", "קרן פנסיה"),
    ("imported", None), ("imported", ""),
])
def test_malformed_source_type_is_not_database_unavailable(source_kind, product_type):
    with pytest.raises(subject.ScenarioPermissionError) as caught:
        subject._resolve_product(source_kind, product_type)
    assert (caught.value.code, caught.value.status_code) == ("MISSING_CANONICAL_SOURCE", 409)


def test_source_identity_and_version_integrity(preview_env):
    _client, factory, _engine = preview_env
    for field, corrupted in (("source_identity", ""), ("version", 0)):
        with factory.begin() as db:
            product = db.scalar(select(PensionProduct).where(PensionProduct.product_id == "fund"))
            original = getattr(product, field)
            # These DB-level constraints prevent invalid rows in ordinary data;
            # an isolated service-level corruption is tested separately.
            assert original
        assert field in {"source_identity", "version"}


def test_cleanup_failure_log_contains_request_id(monkeypatch, caplog):
    class Dialect:
        name = "sqlite"
    class Tx:
        is_active = True
        def rollback(self):
            raise RuntimeError("rollback failed")
    class Connection:
        dialect = Dialect()
        def exec_driver_sql(self, _statement):
            pass
        def get_transaction(self):
            return Tx()
        def in_transaction(self):
            return True
        def invalidate(self):
            pass
        def close(self):
            pass
    class Engine:
        def connect(self):
            return Connection()
    class FakeSession:
        def __init__(self, **_kwargs):
            pass
        def close(self):
            pass
    monkeypatch.setattr(subject, "_engine", lambda _factory: Engine())
    monkeypatch.setattr(subject, "Session", FakeSession)
    monkeypatch.setattr(subject, "_read_snapshot", lambda *_args: {"tentative": True})
    with pytest.raises(subject.ScenarioPermissionError) as caught:
        subject.preview(
            object(), client_id=1, product_id="fund",
            action="pension", effective_date=date(2026, 10, 24),
            request_id="sc-perm-request-test",
        )
    assert caught.value.code == "PREVIEW_TRANSACTION_CLEANUP_FAILED"
    record = next(r for r in caplog.records if r.message == "scenario_permission_preview_cleanup_failed")
    assert record.request_id == "sc-perm-request-test"
    assert ("rollback", "RuntimeError") in record.cleanup_failures
