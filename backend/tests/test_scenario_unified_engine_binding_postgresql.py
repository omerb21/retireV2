"""Package 2 binding acceptance on the existing disposable local PG16 fixture.

The persisted scenario, source and election are real SQLAlchemy/PostgreSQL rows.
The Stage 6 engines execute through the existing read-only snapshot owner.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import select, text

from app.models.capital_projection_basis import CapitalProjectionBasisDecision
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
        # The canonical capital-asset DDL listener installs PG guard
        # functions. Keep them in this disposable schema, never in public.
        schema = scoped.get_execution_options()["schema_translate_map"][None]
        connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
        Base.metadata.create_all(connection, tables=[
            ClientProfile.__table__,
            ScenarioPensionFactorAdmission.__table__,
            RecurringIncome.__table__,
            PensionIncomeResolution.__table__,
            batches, conversions,
            CapitalAsset.__table__, EmploymentRecord.__table__,
            Grant.__table__, ActualCapitalization.__table__,
            CapitalProjectionBasisDecision.__table__,
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


def test_live_pg16_package2_fact_evidence_binds_source_and_is_never_cash(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(EmploymentRecord(
            employment_record_id="work7", client_id=7,
            employer_name="Synthetic employer", work_start_date=date(2010, 1, 1),
            work_end_date=date(2025, 12, 31), is_current=False,
            exempt_grant_status="not_reviewed",
        ))
        asset = CapitalAsset(
            client_id=7, asset_category="bank deposit",
            asset_description="Synthetic deposit",
            known_value_amount=Decimal("800.00"),
            value_as_of_date=date(2026, 10, 1),
            lifecycle_status="current", verification_state="verified",
            source_status="external statement", origin_kind="manual",
        )
        db.add(asset)
        db.flush()
        db.add(CapitalProjectionBasisDecision(
            capital_asset_id=asset.id, client_id=7,
            annual_rate=Decimal("0.05"), return_basis="NET",
            price_basis="NOMINAL",
            contract_version="canonical-pre-retirement-projection-basis-v1",
            source_semantic_fingerprint_at_decision="a" * 64,
            timing_context_fingerprint_at_decision="b" * 64,
            planning_calculation_input_fingerprint_at_decision="c" * 64,
            actor="synthetic-planner",
            provenance="explicit_professional_capital_projection_basis",
            decided_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ))
        db.add(ActualCapitalization(
            capitalization_id="cap7", client_id=7,
            amount=Decimal("60.00"), capitalization_date=date(2022, 1, 1),
            source_label="Test historical capitalization",
        ))
        db.add(FixationRun(
            client_id=7, calculation_version="test-only",
            status="success", is_latest=True,
        ))
    with factory.begin() as db:
        db.add(Grant(
            grant_id="grant7", client_id=7, employment_record_id="work7",
            employer_name="Synthetic employer",
            nominal_amount=Decimal("500.00"),
            grant_date=date(2025, 12, 31),
            work_start_date=date(2010, 1, 1),
            work_end_date=date(2025, 12, 31),
        ))
    before = build(factory)
    facts = before["financial_evidence"]
    assert set(facts) == {"capital", "severance", "fixation_tax"}
    for name in facts:
        assert facts[name]["client_id"] == 7
        assert facts[name]["scenario_id"] == "a1"
        assert facts[name]["scenario_version"] == 1
        assert facts[name]["authority_state"] == "FACTUAL_EVIDENCE_ONLY"
        assert facts[name]["estimated_withdrawable_amount_ils"] is None
        assert facts[name]["tax_effect_ils"] is None
        assert len(facts[name]["evidence_fingerprint"]) == 64

    capital = facts["capital"]["facts"]
    assert capital["canonical_assets"][0]["reported_current_value_ils"] == "800.00"
    assert capital["canonical_assets"][0]["available_to_withdraw_ils"] is None
    assert capital["capital_projection_basis_evidence"][0]["annual_rate_text"] == "0.05"
    assert capital["capital_projection_basis_evidence"][0][
        "state"] == "CLIENT_LEVEL_BASIS_NOT_SCENARIO_ADMITTED"
    assert capital["capital_projection_basis_evidence"][0]["projected_amount_ils"] is None
    assert capital["source_components_consumed_once"] == [{
        "product_id": "p7", "component_id": "c7",
        "capacity_ils": "200.00",
        "planned_allocations_total_ils": "40.00",
    }]
    assert capital["decisions"][0]["cash_paid"] is False
    assert capital["decisions"][0]["amount_planned_ils"] == "40.00"

    grants = facts["severance"]["facts"]["grants"]
    assert len(grants) == 1
    assert grants[0]["reported_nominal_amount_ils"] == "500.00"
    assert grants[0]["payment_classification"] == "UNKNOWN_NOT_VERIFIED"
    assert grants[0]["actual_payment_ils"] is None
    assert grants[0]["tax_exemption_ils"] is None
    fixation = facts["fixation_tax"]["facts"]
    assert fixation["historical_actual_capitalizations"][0]["reported_amount_ils"] == "60.00"
    assert fixation["historical_fixation_run_references"][0]["calculation_status"] == "success"
    assert fixation["historical_fixation_run_references"][0]["authority_state"] == (
        "HISTORICAL_CALCULATION_NOT_TAX_AUTHORITY_APPROVAL"
    )
    assert fixation["tax_authority_approval"] is None
    for name in ("capital", "severance", "fixation_tax"):
        assert before["domain_results"][name]["state"] == "BLOCKED"
        assert before["domain_results"][name]["result"] is None
    assert before["net_income"]["state"] == "BLOCKED"

    # A factual grant edit must invalidate the entire envelope without changing
    # the independent client/scenario or implying the grant was ever paid.
    with factory.begin() as db:
        grant = db.get(Grant, "grant7")
        grant.nominal_amount = Decimal("550.00")
    after = build(factory)
    assert after["identity"] == before["identity"]
    assert after["result_fingerprint"] != before["result_fingerprint"]
    assert (after["financial_evidence"]["severance"]["evidence_fingerprint"]
            != facts["severance"]["evidence_fingerprint"])
    assert after["financial_evidence"]["severance"]["facts"]["grants"][0][
        "reported_nominal_amount_ils"] == "550.00"
    assert after["domain_results"]["severance"]["result"] is None
    assert build(factory, client=7, scenario="a2")["identity"]["scenario_id"] == "a2"
    foreign = build(factory, client=8, scenario="b1")
    assert foreign["financial_evidence"]["severance"]["facts"]["grants"] == []
    assert foreign["financial_evidence"]["capital"]["facts"]["canonical_assets"] == []
    assert foreign["financial_evidence"]["fixation_tax"]["facts"][
        "historical_fixation_run_references"] == []


def test_live_pg16_package2_duplicate_source_allocation_never_counts_twice(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(ScenarioDraftDecision(
            decision_id="extra_a1", scenario_id="a1",
            source_product_id="p7", source_component_id="c7",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("180.00"), action="capital_asset",
            effective_date=date(2027, 1, 1),
            validation_state="unverified", product_version_at_review=1,
        ))
    result = build(factory)
    capital = result["financial_evidence"]["capital"]
    assert capital["facts"]["source_components_consumed_once"] == [{
        "product_id": "p7", "component_id": "c7",
        "capacity_ils": "200.00",
        "planned_allocations_total_ils": "220.00",
    }]
    assert "CAPITAL_SOURCE_OVERALLOCATED" in capital["blockers"]
    assert result["domain_results"]["capital"]["state"] == "BLOCKED"
    assert result["domain_results"]["capital"]["result"] is None
    assert result["execution_allowed"] is False


def test_live_pg16_package2_rejects_foreign_asset_basis_without_id_leak(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        foreign = CapitalAsset(
            client_id=8, asset_category="bank deposit",
            asset_description="Other client private asset",
            known_value_amount=Decimal("900.00"),
            value_as_of_date=date(2026, 10, 1),
            lifecycle_status="current", source_status="external statement",
            verification_state="verified", origin_kind="manual",
        )
        db.add(foreign)
        db.flush()
        foreign_id = foreign.id
        db.add(CapitalProjectionBasisDecision(
            capital_asset_id=foreign_id, client_id=7,
            annual_rate=Decimal("0.05"), return_basis="NET",
            price_basis="NOMINAL",
            contract_version="canonical-pre-retirement-projection-basis-v1",
            source_semantic_fingerprint_at_decision="a" * 64,
            timing_context_fingerprint_at_decision="b" * 64,
            planning_calculation_input_fingerprint_at_decision="c" * 64,
            actor="synthetic-planner",
            provenance="explicit_professional_capital_projection_basis",
            decided_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ))
    result = build(factory, client=7, scenario="a1")
    capital = result["financial_evidence"]["capital"]
    assert "CAPITAL_PROJECTION_BASIS_CLIENT_ASSET_MISMATCH" in capital["blockers"]
    assert capital["facts"]["capital_projection_basis_evidence"] == []
    assert capital["facts"]["canonical_assets"] == []
    assert str(foreign_id) not in [
        str(row["capital_asset_id"])
        for row in capital["facts"]["capital_projection_basis_evidence"]
    ]
    assert result["domain_results"]["capital"]["result"] is None
    assert result["professional_authority"] is False
    other = build(factory, client=8, scenario="b1")
    assert other["financial_evidence"]["capital"]["facts"]["canonical_assets"][0][
        "reported_current_value_ils"] == "900.00"
