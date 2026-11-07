"""Package 2 binding acceptance on the existing disposable local PG16 fixture.

The persisted scenario, source and election are real SQLAlchemy/PostgreSQL rows.
The Stage 6 engines execute through the existing read-only snapshot owner.
"""
from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select

from app.models.actual_capitalization import ActualCapitalization
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.models.fixation_run import FixationRun
from app.models.retirement_facts import CapitalAsset
from app.models.canonical_conversion import batches, conversions
from app.models.client_profile import ClientProfile
from app.models.planning_input_decision import PensionIncomeResolution
from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.retirement_facts import RecurringIncome
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision
from app.models.scenario_pension_factor_admission import ScenarioPensionFactorAdmission
from app.services.scenario_unified_engine_binding_service import (
    build_unified_scenario_engine_bindings, CONTRACT, FINANCIAL_DOMAINS,
)
from app.services.scenario_unified_result_service import assert_unified_result_current
import pytest
from app.db.base import Base, load_all_models
from tests.test_scenario_unified_result_real_postgresql import pg16 as pg16_base, _source_state


@pytest.fixture
def pg16(pg16_base):
    """Install only the extra Stage 6 read dependencies in the existing schema.

    The package-1 fixture already creates clients, canonical products/components,
    drafts/decisions, elections, planning decisions, income targets and planner
    assumptions. Stage 6 reads the client's profile and factor admissions;
    cashflow additionally reads recurring income and its pension-resolution
    records. All four tables have FK parents already present in this schema,
    except pension_income_resolutions -> recurring_income, created first below.
    No global metadata creation, mocks, or external databases.
    """
    factory, scoped = pg16_base
    load_all_models()
    with scoped.begin() as connection:
        Base.metadata.create_all(connection, tables=[
            ClientProfile.__table__,
            ScenarioPensionFactorAdmission.__table__,
            RecurringIncome.__table__,
            PensionIncomeResolution.__table__,
            batches, conversions,
            CapitalAsset.__table__, EmploymentRecord.__table__,
            Grant.__table__, ActualCapitalization.__table__,
            FixationRun.__table__,
        ], checkfirst=True)
    return factory, scoped


def build(factory, client=7, scenario="a1", start=None, end=None):
    return build_unified_scenario_engine_bindings(
        factory, client_id=client, scenario_id=scenario,
        start_month=start, end_month=end,
    )


def _all_unapproved(result):
    assert result["professional_authority"] is False
    assert result["execution_allowed"] is False
    assert result["base"]["professional_authority"] is False
    for domain in FINANCIAL_DOMAINS:
        cell = result["domain_results"][domain]
        assert cell["professional_authority"] is False
        if cell["state"] in {"BLOCKED", "NOT_REQUESTED"}:
            assert cell["result"] is None
            assert cell["result_fingerprint"] is None
    assert result["net_income"]["state"] == "BLOCKED"
    assert result["net_income"]["result"] is None


def test_live_pg16_package2_identity_repeatability_and_fail_closed(pg16):
    factory, _ = pg16
    before = _source_state(factory)
    first = build(factory)
    second = build(factory)
    assert first == second
    assert first["schema_version"] == CONTRACT
    assert first["identity"] == {
        "client_id": 7, "scenario_id": "a1",
        "scenario_version": 1, "scenario_status": "draft",
    }
    assert first["result_fingerprint"] == second["result_fingerprint"]
    assert first["domain_results"]["pension_gross"]["state"] == "BLOCKED"
    assert first["domain_results"]["pension_gross"]["result"] is None
    assert first["domain_results"]["monthly_cashflow"]["state"] == "NOT_REQUESTED"
    _all_unapproved(first)
    assert _source_state(factory) == before


def test_live_pg16_package2_gross_cashflow_with_missing_factor(pg16):
    factory, _ = pg16
    before = _source_state(factory)
    value = build(factory, start="2032-01", end="2032-03")
    assert value["identity"]["scenario_id"] == "a1"
    # No professional factor exists in this synthetic fixture: it must not
    # become a calculated positive pension.
    pension = value["domain_results"]["pension_gross"]
    assert pension["state"] == "BLOCKED"
    assert pension["result"] is None
    cashflow = value["domain_results"]["monthly_cashflow"]
    assert cashflow["state"] == "BLOCKED"
    assert cashflow["result"] is None
    assert cashflow["blockers"]
    _all_unapproved(value)
    assert _source_state(factory) == before


def test_live_pg16_package2_client_and_scenario_isolation(pg16):
    factory, _ = pg16
    a = build(factory, client=7, scenario="a1")
    a2 = build(factory, client=7, scenario="a2")
    b = build(factory, client=8, scenario="b1")
    assert a["result_fingerprint"] != a2["result_fingerprint"]
    assert a["result_fingerprint"] != b["result_fingerprint"]
    assert all(row["client_id"] == 8 for row in b["base"]["source_facts"])
    from app.services.scenario_draft_service import DraftError
    import pytest
    with pytest.raises(DraftError):
        build(factory, client=8, scenario="a1")
    _all_unapproved(a)
    _all_unapproved(a2)
    _all_unapproved(b)


def test_live_pg16_package2_source_change_invalidates_binding(pg16):
    factory, _ = pg16
    before = build(factory)
    with factory.begin() as db:
        product = db.scalar(select(PensionProduct).where(PensionProduct.product_id == "p7"))
        component = db.scalar(select(PensionProductComponent).where(
            PensionProductComponent.component_id == "c7"))
        product.version += 1
        component.balance = Decimal("190.00")
    after = build(factory)
    assert before["result_fingerprint"] != after["result_fingerprint"]
    assert after["base"]["source_candidate_state"] == "BLOCKED"
    assert after["domain_results"]["pension_gross"]["state"] == "BLOCKED"
    assert after["domain_results"]["pension_gross"]["result"] is None
    assert not assert_unified_result_current(
        factory, client_id=7, scenario_id="a1",
        expected_result_fingerprint=before["base"]["result_fingerprint"],
    )


def test_live_pg16_package2_decision_change_invalidates_binding(pg16):
    factory, _ = pg16
    before = build(factory)
    with factory.begin() as db:
        draft = db.scalar(select(ScenarioDraft).where(ScenarioDraft.scenario_id == "a1"))
        decision = db.scalar(select(ScenarioDraftDecision).where(
            ScenarioDraftDecision.decision_id == "d_a1"))
        draft.version += 1
        decision.amount = Decimal("45.00")
    after = build(factory)
    assert before["result_fingerprint"] != after["result_fingerprint"]
    assert after["identity"]["scenario_version"] == 2
    assert after["domain_results"]["pension_gross"]["result"] is None
    assert after["base"]["decisions"][0]["election_state"] == "BLOCKED_STALE"
