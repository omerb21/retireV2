"""Live service integration, on a disposable localhost-only PostgreSQL 16 schema.

No mocks: both unified public entrypoints execute through the original SQLAlchemy
snapshot owner and real PostgreSQL transactions. Only synthetic fixture rows.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
import re
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.models.client import Client
from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.planning_input_decision import PlanningInputDecision
from app.models.retirement_facts import PlannerAssumption
from app.models.retirement_monthly_income_target import RetirementMonthlyIncomeTargetElection
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.scenario_draft_pension_election import ScenarioDraftPensionElection
from app.services.scenario_draft_service import DraftError, _source_evidence
from app.services.scenario_unified_result_service import (
    FINANCIAL_DOMAINS, assert_unified_result_current, build_unified_scenario_result,
)

load_all_models()
CODE = "תגמולי_עובד_עד_2000"
HASH = "a" * 64
MUTATING_SQL = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|UPSERT|MERGE|TRUNCATE|CREATE|ALTER|DROP|GRANT|REVOKE|COPY|CALL)\b",
    re.IGNORECASE,
)


def _url():
    url = os.environ.get("SCENARIO_TEST_POSTGRES_URL")
    if not url:
        pytest.fail("SCENARIO_TEST_POSTGRES_URL missing: use isolated PG16 runner")
    parsed = urlsplit(url)
    if (parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.path != "/retire_v2_scenario_test"):
        pytest.fail("Only localhost/retire_v2_scenario_test is permitted")
    return url


@pytest.fixture
def pg16():
    engine = create_engine(_url())
    schema = "unified_" + uuid4().hex[:16]
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped, autoflush=False, expire_on_commit=False)
    try:
        with engine.begin() as conn:
            assert int(conn.scalar(text("SHOW server_version_num"))) // 10000 == 16
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        with scoped.begin() as conn:
            # All foreign-key targets are created in the same isolated schema.
            from app.db.base import Base
            Base.metadata.create_all(conn, tables=[
                Client.__table__, PensionProduct.__table__,
                PensionProductComponent.__table__,
                ScenarioDraft.__table__, ScenarioDraftDecision.__table__,
                ScenarioDraftPensionElection.__table__, PlanningInputDecision.__table__,
                RetirementMonthlyIncomeTargetElection.__table__,
                PlannerAssumption.__table__,
            ])
            for client_id in (7, 8):
                conn.execute(Client.__table__.insert(), {
                    "client_id": client_id, "display_name": f"Synthetic {client_id}",
                    "id_number": f"unified-test-{client_id}",
                })
                conn.execute(PensionProduct.__table__.insert(), {
                    "product_id": f"p{client_id}", "client_id": client_id,
                    "source_kind": "manual", "source_identity": f"manual:{client_id}",
                    "product_name": "Synthetic pension", "product_type": "קרן פנסיה",
                    "account_reference": "TEST ONLY", "version": 1,
                    "historical_employers": [], "created_by": "test", "updated_by": "test",
                })
                conn.execute(PensionProductComponent.__table__.insert(), {
                    "component_id": f"c{client_id}", "product_id": f"p{client_id}",
                    "component_code": CODE, "balance": Decimal("200.00"),
                })
                conn.execute(PlanningInputDecision.__table__.insert(), {
                    "client_id": client_id, "version": 1,
                    "planning_base_date": date(2026, 11, 1),
                    "retirement_target_date": date(2032, 1, 1),
                    "actor": "synthetic-test",
                })
            for scenario_id, client_id in (("a1", 7), ("a2", 7), ("b1", 8)):
                conn.execute(ScenarioDraft.__table__.insert(), {
                    "scenario_id": scenario_id, "client_id": client_id,
                    "name": f"Test {scenario_id}", "status": "draft",
                    "version": 1, "created_by": "test", "updated_by": "test",
                })
                source = _source_evidence(
                    SimpleNamespace(client_id=client_id, product_id=f"p{client_id}",
                        version=1, product_type="קרן פנסיה",
                        source_kind="manual", source_identity=f"manual:{client_id}"),
                    SimpleNamespace(product_id=f"p{client_id}",
                        component_id=f"c{client_id}", component_code=CODE,
                        balance=Decimal("200.00")),
                )
                conn.execute(ScenarioDraftDecision.__table__.insert(), {
                    "decision_id": "d_" + scenario_id, "scenario_id": scenario_id,
                    "source_product_id": f"p{client_id}",
                    "source_component_id": f"c{client_id}",
                    "component_code": CODE, "amount": Decimal("40.00"),
                    "action": "pension", "effective_date": date(2027, 1, 1),
                    "validation_state": "unverified",
                    "product_version_at_review": 1,
                    "source_fingerprint_at_review": source["source_fingerprint"],
                    "ruleset_digest_at_review": HASH,
                })
                conn.execute(ScenarioDraftPensionElection.__table__.insert(), {
                    "election_id": "e_" + scenario_id,
                    "scenario_id": scenario_id, "decision_id": "d_" + scenario_id,
                    "scenario_version": 1,
                    "pension_start_date": date(2032, 1, 1),
                    "target_year": 2032, "survivors_option": "60%",
                    "spouse_age_diff": 0,
                    "coefficient_selection": "manual_review_required",
                })
        yield factory, scoped
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        scoped.dispose()
        engine.dispose()


def _read_with_transaction_evidence(factory, scoped, client_id, scenario_id):
    statements = []
    settings = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
        # Raw psycopg cursor interrogates *this* transaction, not another session.
        if not settings:
            with cursor.connection.cursor() as verify:
                verify.execute(
                    "SELECT current_setting('transaction_isolation'), "
                    "current_setting('transaction_read_only'), "
                    "current_setting('server_version_num')"
                )
                settings.append(verify.fetchone())

    event.listen(scoped, "before_cursor_execute", capture)
    try:
        result = build_unified_scenario_result(
            factory, client_id=client_id, scenario_id=scenario_id,
        )
    finally:
        event.remove(scoped, "before_cursor_execute", capture)
    assert statements, "No database statement observed"
    assert settings, "Transaction settings not observed"
    assert settings[0][0] == "repeatable read"
    assert settings[0][1] == "on"
    assert int(settings[0][2]) // 10000 == 16
    assert not any(MUTATING_SQL.search(sql) for sql in statements), statements
    return result


def _unapproved(result):
    assert result["execution_allowed"] is False
    assert result["professional_authority"] is False
    for domain in FINANCIAL_DOMAINS:
        cell = result["financial_domains"][domain]
        assert cell["state"] in {"NOT_CONNECTED", "BLOCKED"}
        assert cell["result"] is None
        assert cell["professional_authority"] is False
        assert cell["result_fingerprint"] is None


def test_a_b_d_e_f_g_live_identity_repeatability_isolation_no_writes(pg16):
    factory, scoped = pg16
    before = _source_state(factory)
    first = _read_with_transaction_evidence(factory, scoped, 7, "a1")
    second = _read_with_transaction_evidence(factory, scoped, 7, "a1")
    assert first == second
    assert first["result_fingerprint"] == second["result_fingerprint"]
    assert re.fullmatch("[0-9a-f]{64}", first["result_fingerprint"])
    assert first["identity"] == {
        "client_id": 7, "scenario_id": "a1",
        "scenario_version": 1, "scenario_status": "draft",
    }
    assert first["decisions"][0]["election_state"] == "CURRENT_DRAFT_ONLY"
    assert first["decisions"][0]["source_state"] == "CURRENT_STRUCTURAL_ONLY"
    _unapproved(first)
    assert assert_unified_result_current(factory, client_id=7, scenario_id="a1",
                                         expected_result_fingerprint=first["result_fingerprint"])
    assert not assert_unified_result_current(factory, client_id=7, scenario_id="a1",
                                             expected_result_fingerprint="0" * 64)
    other = _read_with_transaction_evidence(factory, scoped, 7, "a2")
    foreign = _read_with_transaction_evidence(factory, scoped, 8, "b1")
    assert other["identity"]["scenario_id"] == "a2"
    assert other["result_fingerprint"] != first["result_fingerprint"]
    assert foreign["identity"]["client_id"] == 8
    assert foreign["source_facts"][0]["client_id"] == 8
    assert foreign["source_facts"][0]["product_id"] == "p8"
    with pytest.raises(DraftError) as error:
        build_unified_scenario_result(factory, client_id=8, scenario_id="a1")
    assert error.value.code == "SCENARIO_NOT_FOUND"
    with pytest.raises(DraftError):
        build_unified_scenario_result(factory, client_id=7, scenario_id="b1")
    assert _source_state(factory) == before, "Read-only contract mutated persisted rows"


def _source_state(factory):
    with factory() as db:
        return {
            "products": [(p.product_id, p.version) for p in db.scalars(
                select(PensionProduct).order_by(PensionProduct.product_id)).all()],
            "balances": [(c.component_id, str(c.balance)) for c in db.scalars(
                select(PensionProductComponent).order_by(PensionProductComponent.component_id)).all()],
            "drafts": [(s.scenario_id, s.version) for s in db.scalars(
                select(ScenarioDraft).order_by(ScenarioDraft.scenario_id)).all()],
            "decisions": [(d.decision_id, str(d.amount)) for d in db.scalars(
                select(ScenarioDraftDecision).order_by(ScenarioDraftDecision.decision_id)).all()],
            "elections": [(e.election_id, e.scenario_version) for e in db.scalars(
                select(ScenarioDraftPensionElection).order_by(
                    ScenarioDraftPensionElection.election_id)).all()],
        }


def test_c_live_decision_change_invalidates_fingerprint_and_election(pg16):
    factory, scoped = pg16
    original = _read_with_transaction_evidence(factory, scoped, 7, "a1")
    with factory.begin() as db:
        draft = db.scalar(select(ScenarioDraft).where(ScenarioDraft.scenario_id == "a1"))
        decision = db.scalar(select(ScenarioDraftDecision).where(
            ScenarioDraftDecision.decision_id == "d_a1"))
        draft.version += 1
        decision.amount = Decimal("45.00")
    current = _read_with_transaction_evidence(factory, scoped, 7, "a1")
    assert current["identity"]["scenario_version"] == 2
    assert current["decisions"][0]["decision"]["amount"] == "45.00"
    assert current["decisions"][0]["election_state"] == "BLOCKED_STALE"
    assert current["result_fingerprint"] != original["result_fingerprint"]
    assert not assert_unified_result_current(
        factory, client_id=7, scenario_id="a1",
        expected_result_fingerprint=original["result_fingerprint"],
    )
    unchanged = _read_with_transaction_evidence(factory, scoped, 7, "a2")
    assert unchanged["identity"]["scenario_version"] == 1
    _unapproved(current)


def test_c_e_live_source_change_blocks_previous_evidence(pg16):
    factory, scoped = pg16
    original = _read_with_transaction_evidence(factory, scoped, 7, "a1")
    with factory.begin() as db:
        product = db.scalar(select(PensionProduct).where(PensionProduct.product_id == "p7"))
        component = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.component_id == "c7"))
        product.version = 2
        component.balance = Decimal("190.00")
    changed = _read_with_transaction_evidence(factory, scoped, 7, "a1")
    assert changed["result_fingerprint"] != original["result_fingerprint"]
    assert changed["decisions"][0]["source_state"] == "BLOCKED_STALE"
    assert changed["source_candidate_state"] == "BLOCKED"
    assert not assert_unified_result_current(
        factory, client_id=7, scenario_id="a1",
        expected_result_fingerprint=original["result_fingerprint"],
    )
    _unapproved(changed)
