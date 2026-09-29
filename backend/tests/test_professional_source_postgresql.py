"""Isolated real PostgreSQL migration, MVCC, write serialization and lifecycle."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Barrier
from decimal import Decimal
from datetime import date
import pytest
from sqlalchemy import create_engine, event, select, text, inspect
from sqlalchemy.orm import Session
from app.db.base import load_all_models
from app.models.canonical_manual_pension_source import CanonicalManualPensionSource as Manual
from app.models.retirement_facts import CapitalAsset
from app.models.pension_product import PensionProduct
from app.schemas.canonical_manual_pension_source import ManualPensionUpdate, ManualPensionSupersede
from app.schemas.pension_product import ProductUpdate
from app.services import canonical_manual_pension_service as manual
from app.services.pension_product_service import product_response, update_product, PensionProductError
from app.services.canonical_component_conversion_service import execute
from app.api.clients_routes import update_capital_asset, CapitalAssetUpdateRequest
from test_recovery_migration_postgresql import postgres_url
from test_canonical_conversion_migration import migrate
from test_professional_source_snapshot import read, facts
from test_canonical_component_conversion import seeded, request

REVISION = "a6b2d9e5f743"


def test_postgresql_corrected_readiness(pg_engine):
    from test_professional_source_snapshot import assert_positive_basis_readiness, assert_fixed_rate_readiness
    for mode in ("entered", "calculated"):
        for amount in ("0.00", "0.01"):
            assert_positive_basis_readiness(pg_engine, mode, amount)
    for method, rate, code in (
        ("fixed", None, "fixed_indexation_rate_missing"),
        ("fixed", "-1", "fixed_indexation_rate_not_positive"),
        ("fixed", "0", "fixed_indexation_rate_not_positive"),
        ("fixed", "0.000000000000000000000000001", None),
        ("none", None, None), ("cpi", None, None),
    ):
        assert_fixed_rate_readiness(pg_engine, method, rate, code)
        with pg_engine.begin() as db:
            db.execute(text("DELETE FROM canonical_manual_pension_sources WHERE manual_pension_source_id='rate-case'"))


@pytest.fixture
def pg_engine(postgres_url):
    load_all_models()
    migrate(postgres_url, "upgrade", "f1a7c4d0e298")
    engine = create_engine(postgres_url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123'),(2,'other','456')"))
    yield engine
    engine.dispose()


def test_postgresql_migration_preserves_existing_and_downgrade_guard(postgres_url):
    load_all_models()
    migrate(postgres_url, "upgrade", "f5a1c8d4e632")
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
            db.execute(text("INSERT INTO recurring_income(client_id,income_category,description,amount,amount_basis,frequency,continuation_status) VALUES(1,'pension','general',123.45,'gross','monthly','ongoing')"))
        before = set(inspect(engine).get_table_names())
        migrate(postgres_url, "upgrade", REVISION)
        assert set(inspect(engine).get_table_names()) - before == {"canonical_manual_pension_sources"}
        with engine.connect() as db:
            assert db.scalar(text("SELECT count(*) FROM canonical_manual_pension_sources")) == 0
            assert db.scalar(text("SELECT amount FROM recurring_income")) == Decimal("123.45")
            assert db.execute(text("SELECT numeric_precision,numeric_scale FROM information_schema.columns WHERE table_name='canonical_manual_pension_sources' AND column_name='monthly_amount'")).one() == (20, 2)
        migrate(postgres_url, "downgrade", "f5a1c8d4e632")
        migrate(postgres_url, "upgrade", REVISION)
        migrate(postgres_url, "upgrade", "f1a7c4d0e298")
        with Session(engine) as db, db.begin():
            manual.create(db, 1, facts(base_amount_effective_date=None, temporal_authority=None))
        failure = migrate(postgres_url, "downgrade", "f5a1c8d4e632", success=False)
        assert "MANUAL_PENSION_SOURCE_DOWNGRADE_WOULD_LOSE_HISTORY" in failure
        assert len(read(engine)["pension_sources"]) == 1
        with engine.connect() as db:
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == "f1a7c4d0e298"
    finally:
        engine.dispose()


def test_postgresql_read_only_exact_version_race_and_supersede(pg_engine):
    from test_professional_source_snapshot import test_manual_api_version_isolation_supersede_and_no_conversion_edit
    test_manual_api_version_isolation_supersede_and_no_conversion_edit(pg_engine)
    from sqlalchemy.exc import IntegrityError
    for columns, values in (("monthly_amount", "-1"), ("annuity_factor,input_mode", "'0','calculated'"),
                            ("balance", "1")):
        # Client FK and exclusive-mode/amount checks run on the actual DB.
        with pg_engine.connect() as connection:
            sql = ("INSERT INTO canonical_manual_pension_sources(manual_pension_source_id,client_id,"
                   + ("" if "input_mode" in columns else "input_mode,") + columns + ") VALUES('bad',1,"
                   + ("" if "input_mode" in columns else "'entered',") + values + ")")
            with pytest.raises(IntegrityError):
                connection.execute(text(sql))
            connection.rollback()
    with Session(pg_engine) as db, db.begin():
        source = manual.create(db, 1, facts())
    source_id = source["manual_pension_source_id"]
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())
    event.listen(pg_engine, "before_cursor_execute", capture)
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.session import get_db
        def session():
            with Session(pg_engine) as db:
                yield db
        app.dependency_overrides[get_db] = session
        try:
            with TestClient(app) as client:
                first = client.get("/api/clients/1/professional-source-snapshot")
                assert first.status_code == 200, first.text
                assert first.json() == client.get("/api/clients/1/professional-source-snapshot").json()
        finally:
            app.dependency_overrides.clear()
        assert all(s.startswith(("SELECT", "SET TRANSACTION")) for s in statements)
    finally:
        event.remove(pg_engine, "before_cursor_execute", capture)
    with Session(pg_engine) as db:
        row = db.get(Manual, source_id)
        assert row.version == 1
        assert row.updated_at.isoformat() == source["updated_at"]
    gate = Barrier(2)
    def writer():
        with Session(pg_engine) as db:
            gate.wait(timeout=20)
            try:
                result = manual.change(db, 1, source_id, ManualPensionUpdate(
                    **{**facts().model_dump(), "monthly_amount": "999999999999999999.99"}, expected_version=1))
                db.commit()
                return result["version"]
            except PensionProductError as error:
                db.rollback()
                return error.status_code
    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(lambda _: writer(), range(2)))
    assert sorted(outcomes) == [2, 409]
    assert read(pg_engine)["pension_sources"][0]["amount_authority"]["amount"] == "999999999999999999.99"
    with Session(pg_engine) as db, db.begin():
        manual.change(db, 1, source_id, ManualPensionSupersede(expected_version=2), supersede=True)
    assert read(pg_engine)["pension_sources"] == []
    with Session(pg_engine) as db:
        assert db.get(Manual, source_id).lifecycle_status == "superseded"


@pytest.mark.parametrize("kind", ["product", "conversion", "manual_pension", "manual_capital"])
def test_postgresql_snapshot_coherent_during_committed_writer(pg_engine, kind):
    source = seeded(pg_engine)
    with Session(pg_engine) as db, db.begin():
        pension = manual.create(db, 1, facts())
        asset = CapitalAsset(client_id=1, asset_category="other", asset_description="manual", known_value_amount=Decimal("10.00"), value_as_of_date=date(2026, 1, 1))
        db.add(asset)
        db.flush()
        asset_id = asset.id
    before = read(pg_engine)
    reader_started, writer_done = Event(), Event()
    def pause(conn, cursor, statement, parameters, context, many):
        if conn.info.get("snapshot_test_reader") and statement.lstrip().startswith("SELECT") and not reader_started.is_set():
            reader_started.set()
            assert writer_done.wait(30), "writer did not commit while read-only snapshot was open"
    event.listen(pg_engine, "after_cursor_execute", pause)
    def reader():
        with Session(pg_engine) as db:
            # Mark connection without beginning the Session transaction.
            with pg_engine.connect() as connection:
                connection.info["snapshot_test_reader"] = True
                try:
                    with Session(bind=connection) as read_db:
                        from app.services.professional_source_snapshot_service import snapshot
                        return snapshot(read_db, 1)
                finally:
                    connection.info.pop("snapshot_test_reader", None)
    def writer():
        assert reader_started.wait(30)
        try:
            with Session(pg_engine) as db:
                if kind == "conversion":
                    execute(db, 1, request(source, destination="pension"), "test")
                elif kind == "manual_pension":
                    manual.change(db, 1, pension["manual_pension_source_id"], ManualPensionUpdate(
                        **{**facts().model_dump(), "monthly_amount": "200.00"}, expected_version=1))
                elif kind == "manual_capital":
                    update_capital_asset(1, asset_id, CapitalAssetUpdateRequest(known_value_amount="20.00"), db)
                else:
                    p = db.get(PensionProduct, source[0])
                    state = product_response(db, p)
                    from app.schemas.pension_product import ProductCreate
                    update_product(db, 1, source[0], ProductUpdate(
                        **{k: state[k] for k in ProductCreate.model_fields}, expected_version=2,
                        components={k: "2.00" for k in state["components"]}), "test")
                db.commit()
        finally:
            writer_done.set()
    try:
        with ThreadPoolExecutor(2) as pool:
            reading = pool.submit(reader)
            writing = pool.submit(writer)
            writing.result(timeout=45)
            during = reading.result(timeout=45)
        assert during == before
        after = read(pg_engine)
        assert after["source_state_fingerprint"] != before["source_state_fingerprint"]
    finally:
        event.remove(pg_engine, "after_cursor_execute", pause)
