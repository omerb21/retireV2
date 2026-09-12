"""Real PostgreSQL locking, serialization, exact money and rollback proofs."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
import pytest
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import Session
from app.db.base import load_all_models
from app.models.pension_product import COMPONENT_CODES, PensionProduct, PensionProductComponent, PensionProductAuditEvent
from app.models.canonical_conversion import conversions, pensions, reversals
from app.schemas.canonical_conversion import ReversalRequest
from app.services import canonical_component_conversion_service as service
from app.services.pension_product_service import PensionProductError
from test_canonical_component_conversion import seeded, request
from test_canonical_conversion_migration import migrate, REVISION
from test_recovery_migration_postgresql import postgres_url


def test_live_postgresql_competing_conversions_locks_and_atomicity(postgres_url, monkeypatch):
    load_all_models()
    migrate(postgres_url, "upgrade", REVISION)
    engine = create_engine(postgres_url)
    try:
        with engine.begin() as db:
            db.execute(text("INSERT INTO clients(client_id,display_name,id_number) VALUES(1,'test','123')"))
        source = seeded(engine)
        # A distinct transaction cannot acquire the row while preflight holds it.
        with Session(engine) as holder, holder.begin():
            service.preview(holder, 1, request(source))
            with Session(engine) as contender:
                contender.execute(text("SET LOCAL lock_timeout = '100ms'"))
                with pytest.raises(OperationalError):
                    contender.execute(select(PensionProduct).where(PensionProduct.product_id == source[0]).with_for_update())
                contender.rollback()
        barrier = Barrier(2)
        requests = [request(source, amount="70.00", destination="pension") for _ in range(2)]
        def run(req):
            barrier.wait(timeout=10)
            try:
                with Session(engine) as db, db.begin():
                    return service.execute(db, 1, req, "concurrent-test")
            except PensionProductError as error:
                return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(run, requests))
        assert sum(isinstance(r, dict) for r in outcomes) == 1
        assert "STALE_PRODUCT_VERSION" in outcomes
        winner = next(r for r in outcomes if isinstance(r, dict))
        req = requests[outcomes.index(winner)]
        with Session(engine) as db, db.begin():
            assert service.execute(db, 1, req, "retry") == winner
            assert db.get(PensionProductComponent, source[1]).balance == Decimal("30.00")
            assert db.scalar(select(func.count()).select_from(conversions)) == 1
        with Session(engine) as db:
            with pytest.raises(PensionProductError) as conflict:
                service.execute(db, 1, req.model_copy(update={"expected_product_version": 99}), "test")
            assert conflict.value.code == "IDEMPOTENCY_CONFLICT"
        with Session(engine) as db, db.begin():
            other = db.scalar(select(PensionProductComponent).where(PensionProductComponent.product_id == source[0], PensionProductComponent.component_code == COMPONENT_CODES[1]))
            other.balance = Decimal("20.01")
        # A late failure after destination creation and balance/version mutation
        # must roll back the entire transaction, not merely the last statement.
        audit = service.audit
        def failure(*args, **kwargs):
            raise RuntimeError("injected late audit failure")
        monkeypatch.setattr(service, "audit", failure)
        with pytest.raises(RuntimeError, match="injected"):
            with Session(engine) as db, db.begin():
                service.execute(db, 1, request((source[0], source[1], 3), amount="10", destination="pension"), "test")
        with pytest.raises(RuntimeError, match="injected"):
            with Session(engine) as db, db.begin():
                batch = request((source[0], source[1], 3), destination="capital").model_copy(update={"whole_product": True, "selections": []})
                service.execute(db, 1, batch, "test")
        undo = ReversalRequest(expected_conversion_version=1, expected_product_version=3, idempotency_key="undo", reason="test")
        cid = winner["conversions"][0]["conversion_id"]
        with pytest.raises(RuntimeError, match="injected"):
            with Session(engine) as db, db.begin():
                service.reverse(db, 1, cid, undo, "test")
        with Session(engine) as db:
            assert db.get(PensionProductComponent, source[1]).balance == Decimal("30.00")
            assert db.get(PensionProduct, source[0]).version == 3
            assert db.scalar(select(func.count()).select_from(conversions)) == 1
            assert db.scalar(select(pensions.c.status)) == "active"
            assert db.scalar(select(func.count()).select_from(reversals)) == 0
            assert db.scalar(text("SELECT count(*) FROM capital_asset")) == 0
            assert db.scalar(select(PensionProductComponent.balance).where(PensionProductComponent.component_code == COMPONENT_CODES[1])) == Decimal("20.01")
        monkeypatch.setattr(service, "audit", audit)
        with Session(engine) as db, db.begin():
            result = service.reverse(db, 1, cid, undo, "test")
        with Session(engine) as db, db.begin():
            assert service.reverse(db, 1, cid, undo, "test") == result
            assert db.get(PensionProductComponent, source[1]).balance == Decimal("100.00")
            assert db.scalar(select(pensions.c.status)) == "reversed"
            event = db.scalar(select(PensionProductAuditEvent).where(PensionProductAuditEvent.action == "reversal"))
            assert event.snapshot["operation"]["allocations"][0]["before"] == "30.00"
            assert event.snapshot["operation"]["allocations"][0]["after"] == "100.00"
            assert event.actor == "test"
        # The DB itself rejects destructive access, independently of HTTP/ORM.
        for sql in ("DELETE FROM canonical_pension_destinations", "UPDATE canonical_conversion_reversals SET reason='rewritten'", "DELETE FROM canonical_conversion_allocations"):
            with engine.connect() as db:
                with pytest.raises(DBAPIError, match="CANONICAL_CONVERSION_HISTORY_IMMUTABLE"):
                    db.exec_driver_sql(sql)
                db.rollback()
    finally:
        engine.dispose()
