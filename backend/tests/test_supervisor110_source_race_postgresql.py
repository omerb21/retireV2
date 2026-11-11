"""Supervisor 110: real PG16 SERIALIZABLE source-write race against internal approval."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.models.pension_product import PensionProductComponent
from app.services import scenario_fixation_approval_service as ledger
from tests.test_scenario_internal_fixation_approval_postgresql import pg16, seeded, request


def _change_source(factory, amount):
    with factory.begin() as db:
        row = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.component_id == "c7").with_for_update())
        assert row is not None
        row.balance = Decimal(amount)
        db.flush()


def _read(factory):
    with factory() as db:
        return ledger.read(db, 7, "a1"), ledger.history(db, 7, "a1")


def _assert_no_current(factory):
    state, history = _read(factory)
    assert not (state["decision_state"] == "APPROVED_INTERNAL"
                and state["validity_state"] == "CURRENT")
    assert state["internal_professional_authority"] is False
    assert state["professional_authority"] is False
    assert state["execution_allowed"] is False
    assert state["tax_authority_approval"] is None
    return state, history


def test_source_write_between_approval_read_and_commit(pg16):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    a_read = Event()
    b_done = Event()

    def approval():
        with factory() as db:
            try:
                result = ledger.request_internal_approval(
                    db, 7, "a1", payload, "trusted-planner")
                assert result["approval_attempt_state"] == "APPROVED_INTERNAL"
                assert db.execute(__import__("sqlalchemy").text(
                    "SHOW transaction_isolation")).scalar_one().lower() == "serializable"
                a_read.set()
                assert b_done.wait(20), "SOURCE_COMMIT_TIMEOUT"
                db.commit()
                return "COMMITTED"
            except DBAPIError as exc:
                db.rollback()
                sqlstate = getattr(exc.orig, "pgcode", None) or getattr(exc.orig, "sqlstate", None)
                if sqlstate != "40001":
                    raise
                return "SERIALIZATION_FAILURE_40001"
            finally:
                a_read.set()

    def source():
        assert a_read.wait(20), "APPROVAL_READ_TIMEOUT"
        try:
            _change_source(factory, "201.00")
            return "SOURCE_COMMITTED"
        finally:
            b_done.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        a_future = pool.submit(approval)
        b_future = pool.submit(source)
        a = a_future.result(timeout=60)
        b = b_future.result(timeout=60)
    assert b == "SOURCE_COMMITTED"
    assert a in {"COMMITTED", "SERIALIZATION_FAILURE_40001"}
    state, history = _assert_no_current(factory)
    if a == "COMMITTED":
        assert state["decision_state"] == "APPROVED_INTERNAL"
        assert state["validity_state"] == "STALE"
        assert history[-1]["status"] == "APPROVED_INTERNAL"
    else:
        assert state["decision_state"] != "APPROVED_INTERNAL"
        assert len(history) == 1


def test_source_write_after_approval_commit_marks_historical_decision_stale(pg16):
    factory, _ = pg16
    seeded(factory)
    payload = request(factory)
    with factory() as db:
        result = ledger.request_internal_approval(
            db, 7, "a1", payload, "trusted-planner")
        assert result["approval_attempt_state"] == "APPROVED_INTERNAL"
        assert db.execute(__import__("sqlalchemy").text(
            "SHOW transaction_isolation")).scalar_one().lower() == "serializable"
        db.commit()
    before, _ = _read(factory)
    assert before["decision_state"] == "APPROVED_INTERNAL"
    assert before["validity_state"] == "CURRENT"
    _change_source(factory, "202.00")
    after, history = _assert_no_current(factory)
    assert after["decision_state"] == "APPROVED_INTERNAL"
    assert after["validity_state"] == "STALE"
    assert history[-1]["status"] == "APPROVED_INTERNAL"
