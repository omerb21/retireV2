"""Package 2 binding acceptance on the existing disposable local PG16 fixture.

The persisted scenario, source and election are real SQLAlchemy/PostgreSQL rows.
The Stage 6 engines execute through the existing read-only snapshot owner.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Barrier
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.canonical_manual_pension_source import CanonicalManualPensionSource
from app.models.pension_product import COMPONENT_CODES
from app.models.retirement_facts import RecurringExpense, RetirementTimingWorkIntention
from app.services import planning_input_service as planning
from app.services import capital_projection_basis_service as capital_basis
from app.services import capital_projection_execution_service as capital_execution
from app.models.capital_projection_basis import CapitalProjectionBasisDecision
from app.models.actual_capitalization import ActualCapitalization
from app.models.employment_record import EmploymentRecord
from app.models.grant import Grant
from app.services import scenario_severance_planning_service as severance_choices_service
from app.services.scenario_severance_planning_service import replace_choices, read_choices
from app.services.scenario_draft_service import (
    DraftError, archive as archive_draft, duplicate as duplicate_draft,
    read as read_draft, rename as rename_draft, replace as replace_draft,
)
from app.schemas.scenario_draft import DraftDecisionWrite, DraftReplace
from app.models.fixation_run import FixationRun
from app.models.retirement_facts import CapitalAsset
from app.models.canonical_conversion import batches, conversions, pensions, allocations, reversals
from app.models.client_profile import ClientProfile
from app.models.planning_input_decision import PensionIncomeResolution
from app.models.pension_product import PensionProduct, PensionProductComponent
from app.models.retirement_facts import RecurringIncome
from app.models.scenario_draft import ScenarioDraft, ScenarioDraftDecision, ScenarioDraftRevision
from app.models.scenario_fixation_approval import (
    ScenarioFixationApprovalHead, ScenarioFixationApprovalRevision,
)
from app.schemas.scenario_fixation_approval import (
    FixationProfessionalDraftReplace, FixationProfessionalDecision,
    FixationAdmissionControls,
)
from app.services import scenario_fixation_approval_service as fixation_review
from app.services import scenario_fixation_admission_preparation_service as fixation_preparation
from app.models.m07_evidence import (
    M07EvidenceRevision, M07FactEvidence, M07PlannerAssertion, M07AssessmentFinding,
)
from app.schemas.m07_evidence import AssessmentRun
from app.services.m07_evidence_service import finalize_revision as finalize_m07_revision
from app.models.official_parameter_set import OfficialParameterSet
from app.schemas.official_parameter_sets import (
    OfficialParameterSetCreate, OfficialParameterValues,
    OfficialParameterVerificationRequest, OfficialParameterActivationRequest,
)
from app.services.official_parameter_service import (
    create_official_parameter_set_draft, verify_official_parameter_set,
    activate_official_parameter_set,
)
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
            # The base pg16 fixture already creates scenario_drafts, but its
            # minimal contract predates revision-backed severance choices.
            ScenarioDraftRevision.__table__,
            ScenarioFixationApprovalHead.__table__,
            ScenarioFixationApprovalRevision.__table__,
            OfficialParameterSet.__table__,
            M07EvidenceRevision.__table__,
            M07PlannerAssertion.__table__,
            M07FactEvidence.__table__,
            M07AssessmentFinding.__table__,
            ClientProfile.__table__,
            ScenarioPensionFactorAdmission.__table__,
            RecurringIncome.__table__,
            PensionIncomeResolution.__table__,
            batches, conversions,
            CapitalAsset.__table__, EmploymentRecord.__table__,
            Grant.__table__, ActualCapitalization.__table__,
            CapitalProjectionBasisDecision.__table__,
            FixationRun.__table__,
            pensions, allocations, reversals, CanonicalManualPensionSource.__table__,
            RecurringExpense.__table__, RetirementTimingWorkIntention.__table__,
        ], checkfirst=True)
        # The DDL listener creates the real canonical archive trigger under
        # this disposable schema. A transaction-local search_path used during
        # CREATE FUNCTION does not persist for later ORM UPDATE connections.
        # Pin only this test-schema function's lookup scope; do not disable or
        # replace the trigger or alter any production/database migration DDL.
        connection.execute(text(
            f'ALTER FUNCTION "{schema}".guard_capital_asset_canonical() '
            f'SET search_path TO "{schema}", pg_catalog'
        ))
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


@pytest.fixture
def admitted_capital(pg16):
    """A real, approved canonical capital basis, not a posted forecast.

    The fixture supplies the other ten factual pension-product components
    required by the existing professional-source snapshot. No engine is mocked
    and the rate decision fingerprints come from the current canonical plan.
    """
    factory, scoped = pg16
    with factory.begin() as db:
        for code in COMPONENT_CODES:
            if code == "תגמולי_עובד_עד_2000":
                continue
            db.add(PensionProductComponent(
                component_id="extra-" + str(COMPONENT_CODES.index(code)),
                product_id="p7", component_code=code, balance=Decimal("0.00"),
            ))
        capital = CapitalAsset(
            client_id=7, asset_category="bank deposit",
            asset_description="Synthetic independent deposit",
            known_value_amount=Decimal("800.00"),
            value_as_of_date=date(2026, 10, 1),
            lifecycle_status="current", verification_state="verified",
            source_status="external statement", origin_kind="manual",
        )
        db.add(capital)
        db.flush()
        capital_id = capital.id
    with factory.begin() as db:
        plan = planning.derive(db, 7)
        source = next(
            entry for entry in plan["capital_inputs"]
            if entry["id"] == capital_id
        )
        db.add(CapitalProjectionBasisDecision(
            capital_asset_id=capital_id, client_id=7,
            annual_rate=Decimal("0.05"), return_basis="NET",
            price_basis="NOMINAL",
            contract_version="canonical-pre-retirement-projection-basis-v1",
            source_semantic_fingerprint_at_decision=capital_basis.source_fingerprint(source),
            timing_context_fingerprint_at_decision=capital_basis.timing_fingerprint(plan),
            planning_calculation_input_fingerprint_at_decision=
                plan["planning_calculation_input_fingerprint"],
            actor="synthetic-professional",
            provenance="explicit_professional_capital_projection_basis",
            decided_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        ))
    return factory, capital_id


def test_live_pg16_package2_positive_canonical_capital_projection(admitted_capital):
    factory, capital_id = admitted_capital
    result = build(factory)
    cell = result["domain_results"]["capital"]
    assert cell["state"] == "NONBINDING_PROJECTION", cell["blockers"]
    assert cell["professional_authority"] is False
    assert result["execution_allowed"] is False
    assert result["net_income"]["result"] is None
    projection = cell["result"]
    assert projection["client_id"] == 7
    assert projection["scenario_id"] == "a1"
    assert projection["scenario_version"] == 1
    assert projection["planning_base_date"] == "2026-11-01"
    assert projection["retirement_target_date"] == "2032-01-01"
    assert projection["withdrawable_amount_ils"] is None
    assert projection["actual_withdrawal_ils"] is None
    assert projection["tax_effect_ils"] is None
    native = projection["projection"]
    assert native["execution_status"] == "AUTHORITATIVE_RESULT"
    assert len(native["projected_sources"]) == 1
    source = native["projected_sources"][0]
    assert source["source_id"] == f"capital:{capital_id}"
    assert Decimal(source["projected_amount"]) > Decimal("800.00")
    assert len(source["projection_result_fingerprint"]) == 64
    assert len(projection["native_execution_fingerprint"]) == 64
    assert len(cell["result_fingerprint"]) == 64

    # Prove the adapter uses exactly the existing engine's result rather than
    # a second formula or an arbitrary financial adjustment.
    with factory() as db:
        plan = planning.derive(db, 7)
        authority = capital_basis.derive(db, 7, plan)
        canonical = capital_execution.execute(7, plan, authority)
        db.rollback()
    assert native == canonical
    other_scenario = build(factory, client=7, scenario="a2")
    assert other_scenario["domain_results"]["capital"]["state"] == "NONBINDING_PROJECTION"
    assert (other_scenario["domain_results"]["capital"]["result_fingerprint"]
            != cell["result_fingerprint"])
    foreign = build(factory, client=8, scenario="b1")
    assert foreign["domain_results"]["capital"]["state"] == "BLOCKED"
    assert foreign["domain_results"]["capital"]["result"] is None


def test_live_pg16_package2_capital_rate_and_source_invalidation(admitted_capital):
    factory, capital_id = admitted_capital
    before = build(factory)
    assert before["domain_results"]["capital"]["state"] == "NONBINDING_PROJECTION"
    with factory.begin() as db:
        basis = db.get(CapitalProjectionBasisDecision, capital_id)
        basis.annual_rate = Decimal("0.06")
    rate_changed = build(factory)
    assert rate_changed["result_fingerprint"] != before["result_fingerprint"]
    assert (rate_changed["domain_results"]["capital"]["result_fingerprint"]
            != before["domain_results"]["capital"]["result_fingerprint"])
    with factory.begin() as db:
        asset = db.get(CapitalAsset, capital_id)
        asset.known_value_amount = Decimal("850.00")
    source_changed = build(factory)
    assert source_changed["domain_results"]["capital"]["state"] == "BLOCKED"
    assert source_changed["domain_results"]["capital"]["result"] is None
    assert source_changed["result_fingerprint"] != rate_changed["result_fingerprint"]


def test_live_pg16_package2_capital_target_and_allocations_block(admitted_capital):
    factory, _ = admitted_capital
    prior = build(factory)
    assert prior["domain_results"]["capital"]["state"] == "NONBINDING_PROJECTION"
    with factory.begin() as db:
        from app.models.planning_input_decision import PlanningInputDecision
        db.get(PlanningInputDecision, 7).retirement_target_date = date(2033, 1, 1)
    after = build(factory)
    assert after["domain_results"]["capital"]["state"] == "BLOCKED"
    assert after["domain_results"]["capital"]["result"] is None
    assert after["result_fingerprint"] != prior["result_fingerprint"]

    # A pension-product component withdrawal cannot be mistaken for a
    # projection of the independent deposit or counted twice.
    with factory.begin() as db:
        db.add(ScenarioDraftDecision(
            decision_id="capital-option", scenario_id="a1",
            source_product_id="p7", source_component_id="c7",
            component_code="תגמולי_עובד_עד_2000",
            amount=Decimal("160.00"), action="capital_asset",
            effective_date=date(2027, 1, 1),
            validation_state="unverified", product_version_at_review=1,
        ))
    blocked = build(factory)
    assert blocked["domain_results"]["capital"]["state"] == "BLOCKED"
    assert blocked["domain_results"]["capital"]["result"] is None
    assert blocked["financial_evidence"]["capital"]["facts"][
        "source_components_consumed_once"][0]["planned_allocations_total_ils"] == "200.00"


def test_live_pg16_package2_capital_unverified_value_not_projected(admitted_capital):
    factory, capital_id = admitted_capital
    assert build(factory)["domain_results"]["capital"]["state"] == "NONBINDING_PROJECTION"
    with factory.begin() as db:
        db.get(CapitalAsset, capital_id).verification_state = "partially verified"
    blocked = build(factory)
    cell = blocked["domain_results"]["capital"]
    assert cell["state"] == "BLOCKED"
    assert cell["result"] is None
    assert "CAPITAL_SOURCE_VERIFICATION_INCOMPLETE" in cell["blockers"]
    assert blocked["financial_evidence"]["capital"]["facts"][
        "canonical_assets"][0]["available_to_withdraw_ils"] is None


def test_live_pg16_package2_capital_archive_trigger_stays_enforced(pg16):
    """Real PG trigger allows a legal manual edit but rejects origin mutation."""
    factory, scoped = pg16
    schema = scoped.get_execution_options()["schema_translate_map"][None]
    with factory.begin() as db:
        asset = CapitalAsset(
            client_id=7, asset_category="bank deposit",
            asset_description="Archive guard synthetic",
            known_value_amount=Decimal("100.00"),
            value_as_of_date=date(2026, 10, 1),
            origin_kind="manual", lifecycle_status="current",
        )
        db.add(asset)
        db.flush()
        asset_id = asset.id
    with factory.begin() as db:
        db.execute(CapitalAsset.__table__.update().where(
            CapitalAsset.id == asset_id,
        ).values(known_value_amount=Decimal("101.00")))
    with pytest.raises(DBAPIError, match="CANONICAL_CONVERSION_HISTORY_IMMUTABLE"):
        with factory.begin() as db:
            db.execute(CapitalAsset.__table__.update().where(
                CapitalAsset.id == asset_id,
            ).values(origin_kind="canonical_component_conversion"))
    with factory() as db:
        asset = db.get(CapitalAsset, asset_id)
        assert asset.origin_kind == "manual"
        assert asset.known_value_amount == Decimal("101.00")
        guard_config = db.execute(text(
            "SELECT p.proconfig FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = :schema "
            "AND p.proname = 'guard_capital_asset_canonical'"
        ), {"schema": schema}).scalar_one()
        search_paths = [
            setting.partition("=")[2]
            for setting in guard_config
            if setting.partition("=")[0] == "search_path"
        ]
        assert len(search_paths) == 1
        assert [name.strip().strip('"') for name in search_paths[0].split(",")] == [
            schema, "pg_catalog",
        ]
        db.rollback()


def test_live_pg16_package2_severance_lineage_and_unreconciled_overlap(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(EmploymentRecord(
            employment_record_id="severance-work7", client_id=7,
            employer_name="Employer A", work_start_date=date(2010, 1, 1),
            work_end_date=date(2025, 12, 31), is_current=False,
            exempt_grant_status="requires_reconciliation",
        ))
        db.add(PensionProductComponent(
            component_id="severance-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי",
            balance=Decimal("300.00"),
        ))
    with factory.begin() as db:
        db.add(Grant(
            grant_id="severance-g7", client_id=7,
            employment_record_id="severance-work7",
            employer_name="Employer A",
            nominal_amount=Decimal("300.00"),
            grant_date=date(2025, 12, 31),
            work_start_date=date(2010, 1, 1),
            work_end_date=date(2025, 12, 31),
        ))
    before = build(factory)
    domain = before["financial_evidence"]["severance"]
    facts = domain["facts"]
    assert domain["client_id"] == 7
    assert domain["scenario_id"] == "a1"
    assert domain["scenario_version"] == 1
    assert len(facts["employment_records"][0]["source_fingerprint"]) == 64
    assert len(facts["grants"][0]["source_fingerprint"]) == 64
    assert facts["grants"][0]["payment_classification"] == "UNKNOWN_NOT_VERIFIED"
    assert facts["grants"][0]["actual_payment_ils"] is None
    assert facts["grants"][0]["future_payment_ils"] is None
    assert facts["grants"][0]["continuity_election"] is None
    assert facts["grants"][0]["tax_exemption_ils"] is None
    assert facts["pension_severance_component_candidates"] == [{
        "product_id": "p7",
        "component_id": "severance-c7",
        "component_code": "פיצויים_מעסיק_נוכחי",
        "reported_balance_ils": "300.00",
    }]
    assert "SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in domain["blockers"]
    assert before["domain_results"]["severance"]["state"] == "BLOCKED"
    assert before["domain_results"]["severance"]["result"] is None
    assert before["net_income"]["result"] is None

    with factory.begin() as db:
        db.get(EmploymentRecord, "severance-work7").notes = "Revised source"
    after = build(factory)
    assert after["result_fingerprint"] != before["result_fingerprint"]
    assert (after["financial_evidence"]["severance"]["facts"][
        "employment_records"][0]["source_fingerprint"]
        != facts["employment_records"][0]["source_fingerprint"])
    assert after["domain_results"]["severance"]["result"] is None
    other_scenario = build(factory, client=7, scenario="a2")
    assert other_scenario["financial_evidence"]["severance"]["scenario_id"] == "a2"
    assert (other_scenario["financial_evidence"]["severance"]["evidence_fingerprint"]
            != after["financial_evidence"]["severance"]["evidence_fingerprint"])
    foreign = build(factory, client=8, scenario="b1")
    assert foreign["financial_evidence"]["severance"]["facts"]["grants"] == []
    assert foreign["financial_evidence"]["severance"]["facts"][
        "pension_severance_component_candidates"] == []


def test_live_pg16_package2_foreign_employment_reference_is_blocked(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(EmploymentRecord(
            employment_record_id="other-employer8", client_id=8,
            employer_name="Private other-client employer",
            work_start_date=date(2011, 1, 1),
            work_end_date=date(2024, 1, 1), is_current=False,
        ))
    with factory.begin() as db:
        db.add(Grant(
            grant_id="cross-client-grant7", client_id=7,
            employment_record_id="other-employer8",
            employer_name="Unverified grant",
            nominal_amount=Decimal("15.00"),
            grant_date=date(2024, 1, 1),
            work_start_date=date(2011, 1, 1),
            work_end_date=date(2024, 1, 1),
        ))
    result = build(factory, client=7, scenario="a1")
    domain = result["financial_evidence"]["severance"]
    assert "SEVERANCE_EMPLOYMENT_CLIENT_MISMATCH" in domain["blockers"]
    assert domain["facts"]["employment_records"] == []
    assert domain["facts"]["grants"][0]["employment_record_id"] is None
    assert domain["facts"]["grants"][0]["actual_payment_ils"] is None
    assert result["domain_results"]["severance"]["result"] is None


def _severance_grant_source(factory):
    with factory.begin() as db:
        db.add(EmploymentRecord(
            employment_record_id="choice-work7", client_id=7,
            employer_name="Synthetic employer", work_start_date=date(2010, 1, 1),
            work_end_date=date(2025, 1, 1), is_current=False,
        ))
    with factory.begin() as db:
        db.add(Grant(
            grant_id="choice-grant7", client_id=7,
            employment_record_id="choice-work7", employer_name="Synthetic employer",
            nominal_amount=Decimal("100.00"), grant_date=date(2025, 1, 1),
            work_start_date=date(2010, 1, 1), work_end_date=date(2025, 1, 1),
        ))


def test_live_pg16_severance_choice_save_reload_two_scenarios_and_staleness(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    planned = [{
        "source_kind": "grant", "source_id": "choice-grant7",
        "choice": "PLANNED_SEVERANCE_CONTINUITY", "planned_amount_ils": "90.00",
    }]
    with factory.begin() as db:
        response = replace_choices(
            db, 7, "a1", expected_version=1, choices=planned, actor="test",
        )
        assert response["version"] == 2
    with factory() as db:
        loaded = read_choices(db, 7, "a1")
        first = loaded["choices"][0]
        assert first["state"] == "DRAFT_ONLY"
        assert first["choice"] == "PLANNED_SEVERANCE_CONTINUITY"
        assert first["professional_authority"] is False
        assert first["actual_paid_amount_ils"] is None
        assert first["exempt_amount_ils"] is None
        assert loaded["scenario_version"] == 2
    with factory.begin() as db:
        replace_choices(db, 7, "a2", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_WITHDRAWAL", "planned_amount_ils": None,
        }], actor="test")
    with factory() as db:
        assert read_choices(db, 7, "a2")["choices"][0]["choice"] == "PLANNED_WITHDRAWAL"
        assert read_choices(db, 7, "a1")["choices"][0]["choice"] == "PLANNED_SEVERANCE_CONTINUITY"
    before = build(factory, client=7, scenario="a1")
    with factory.begin() as db:
        db.get(Grant, "choice-grant7").nominal_amount = Decimal("110.00")
    after = build(factory, client=7, scenario="a1")
    assert after["result_fingerprint"] != before["result_fingerprint"]
    item = after["financial_evidence"]["severance"]["facts"]["scenario_planning_choices"]["choices"][0]
    assert item["state"] == "BLOCKED_SOURCE_STALE"
    assert item["actual_paid_amount_ils"] is None
    assert after["domain_results"]["severance"]["result"] is None
    assert after["net_income"]["result"] is None
    with factory() as db:
        assert read_choices(db, 8, "b1")["choices"] == []


def test_live_pg16_severance_choice_cas_revisions_and_duplicate_rejected(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    planned = [{
        "source_kind": "grant", "source_id": "choice-grant7",
        "choice": "UNDECIDED", "planned_amount_ils": None,
    }]
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=planned, actor="test")
    with pytest.raises(DraftError, match="SCENARIO_VERSION_CONFLICT"):
        with factory.begin() as db:
            replace_choices(db, 7, "a1", expected_version=1, choices=planned, actor="test")
    with pytest.raises(DraftError, match="SEVERANCE_DUPLICATE_SOURCE_CHOICE"):
        with factory.begin() as db:
            replace_choices(db, 7, "a1", expected_version=2,
                            choices=[planned[0], planned[0]], actor="test")
    with factory.begin() as db:
        rename_draft(db, 7, "a1", "Renamed choice", expected=2, actor="test")
    with factory() as db:
        loaded = read_choices(db, 7, "a1")
        assert loaded["scenario_version"] == 3
        assert loaded["choices"][0]["choice"] == "UNDECIDED"
        assert loaded["choices"][0]["actual_paid_amount_ils"] is None


def test_live_pg16_severance_component_limit_and_foreign_grant_rejected(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        db.add(PensionProductComponent(
            component_id="choice-severance-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי",
            balance=Decimal("100.00"),
        ))
        db.add(Grant(
            grant_id="choice-foreign8", client_id=8,
            nominal_amount=Decimal("100.00"),
            grant_date=date(2025, 1, 1),
            work_start_date=date(2010, 1, 1),
            work_end_date=date(2025, 1, 1),
        ))
        db.add(ScenarioDraftDecision(
            decision_id="prior-severance-a1", scenario_id="a1",
            source_product_id="p7", source_component_id="choice-severance-c7",
            component_code="פיצויים_מעסיק_נוכחי",
            amount=Decimal("80.00"), action="capital_asset",
            effective_date=date(2027, 1, 1),
            validation_state="unverified", product_version_at_review=1,
        ))
    with pytest.raises(DraftError, match="SEVERANCE_COMPONENT_OVERALLOCATED"):
        with factory.begin() as db:
            replace_choices(db, 7, "a1", expected_version=1, choices=[{
                "source_kind": "pension_component",
                "source_id": "choice-severance-c7",
                "choice": "PLANNED_PENSION_CONTINUITY",
                "planned_amount_ils": "30.00",
            }], actor="test")
    with pytest.raises(DraftError, match="SEVERANCE_SOURCE_CLIENT_MISMATCH"):
        with factory.begin() as db:
            replace_choices(db, 7, "a1", expected_version=1, choices=[{
                "source_kind": "grant", "source_id": "choice-foreign8",
                "choice": "PLANNED_WITHDRAWAL",
                "planned_amount_ils": "10.00",
            }], actor="test")
    with factory() as db:
        assert read_choices(db, 7, "a1")["choices"] == []
    result = build(factory, client=7, scenario="a1")
    assert "SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in result[
        "financial_evidence"]["severance"]["blockers"]
    assert result["domain_results"]["severance"]["result"] is None
    assert result["execution_allowed"] is False


def test_live_pg16_severance_choice_blocks_new_draft_overallocation(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(PensionProductComponent(
            component_id="post-save-severance-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי",
            balance=Decimal("100.00"),
        ))
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "pension_component",
            "source_id": "post-save-severance-c7",
            "choice": "PLANNED_WITHDRAWAL",
            "planned_amount_ils": "30.00",
        }], actor="test")
    with factory() as db:
        assert read_choices(db, 7, "a1")["choices"][0]["state"] == "DRAFT_ONLY"
    with factory.begin() as db:
        db.add(ScenarioDraftDecision(
            decision_id="late-pension-allocation", scenario_id="a1",
            source_product_id="p7", source_component_id="post-save-severance-c7",
            component_code="פיצויים_מעסיק_נוכחי",
            amount=Decimal("80.00"), action="pension",
            effective_date=date(2027, 1, 1),
            validation_state="unverified", product_version_at_review=1,
        ))
    with factory() as db:
        item = read_choices(db, 7, "a1")["choices"][0]
        assert item["state"] == "BLOCKED_COMPONENT_OVERALLOCATED"
        assert item["actual_paid_amount_ils"] is None
    bound = build(factory, client=7, scenario="a1")
    assert bound["domain_results"]["severance"]["result"] is None
    assert bound["net_income"]["result"] is None


def test_live_pg16_severance_choice_lifecycle_never_reactivates_stale_source(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    planned = [{
        "source_kind": "grant", "source_id": "choice-grant7",
        "choice": "PLANNED_SEVERANCE_CONTINUITY",
        "planned_amount_ils": "90.00",
    }]
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=planned, actor="test")
    with factory.begin() as db:
        rename_draft(db, 7, "a1", "Metadata only", expected=2, actor="test")
    with factory() as db:
        current = read_choices(db, 7, "a1")["choices"][0]
        assert current["saved_from_scenario_version"] == 3
        assert current["state"] == "DRAFT_ONLY"

    with factory.begin() as db:
        db.get(EmploymentRecord, "choice-work7").notes = "materially revised employment evidence"
    with factory() as db:
        assert read_choices(db, 7, "a1")["choices"][0]["state"] == "BLOCKED_SOURCE_STALE"
    with factory.begin() as db:
        rename_draft(db, 7, "a1", "Rename cannot revive", expected=3, actor="test")
    with factory() as db:
        still_stale = read_choices(db, 7, "a1")["choices"][0]
        assert still_stale["state"] == "BLOCKED_SOURCE_STALE"
    with factory.begin() as db:
        clone = duplicate_draft(db, 7, "a1", "Independent clone", actor="test")
        clone_id = clone["scenario_id"]
    with factory() as db:
        assert read_choices(db, 7, clone_id)["choices"] == []
    with factory.begin() as db:
        archive_draft(db, 7, "a1", expected=4, actor="test")
    with factory() as db:
        archived = read_choices(db, 7, "a1")["choices"][0]
        assert archived["state"] == "BLOCKED_SCENARIO_NOT_ACTIVE"
        assert archived["execution_allowed"] is False


def test_live_pg16_material_draft_change_requires_explicit_severance_resave(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_WITHDRAWAL", "planned_amount_ils": "80.00",
        }], actor="test")
    with factory() as db:
        existing = read_draft(db, 7, "a1")["decisions"][0]
    payload = DraftReplace(
        name="Materially changed draft", expected_version=2,
        decisions=[DraftDecisionWrite(
            decision_id=existing["decision_id"],
            source_product_id=existing["source_product_id"],
            source_component_id=existing["source_component_id"],
            component_code=existing["component_code"], amount=Decimal("50.00"),
            action=existing["action"], effective_date=date.fromisoformat(
                existing["effective_date"]),
        )],
    )
    with factory.begin() as db:
        replace_draft(db, 7, "a1", payload, actor="test")
    with factory() as db:
        stale = read_choices(db, 7, "a1")["choices"][0]
        assert stale["saved_from_scenario_version"] == 2
        assert stale["current_scenario_version"] == 3
        assert stale["state"] == "BLOCKED_SCENARIO_VERSION_STALE"
    with factory.begin() as db:
        rename_draft(db, 7, "a1", "Still stale", expected=3, actor="test")
    with factory() as db:
        still_stale = read_choices(db, 7, "a1")["choices"][0]
        assert still_stale["saved_from_scenario_version"] == 2
        assert still_stale["current_scenario_version"] == 4
        assert still_stale["state"] == "BLOCKED_SCENARIO_VERSION_STALE"


def test_live_pg16_concurrent_severance_replacements_have_one_cas_winner(
        pg16, monkeypatch):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(PensionProductComponent(
            component_id="concurrent-severance-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי", balance=Decimal("100.00"),
        ))
    barrier = Barrier(2)
    real_cas = severance_choices_service._cas

    def synchronized_cas(*args, **kwargs):
        barrier.wait(timeout=10)
        return real_cas(*args, **kwargs)

    monkeypatch.setattr(severance_choices_service, "_cas", synchronized_cas)

    def attempt(amount: str):
        try:
            with factory.begin() as db:
                replace_choices(db, 7, "a1", expected_version=1, choices=[{
                    "source_kind": "pension_component",
                    "source_id": "concurrent-severance-c7",
                    "choice": "PLANNED_WITHDRAWAL",
                    "planned_amount_ils": amount,
                }], actor="concurrent-test")
            return "ACCEPTED"
        except DraftError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(attempt, ("60.00", "70.00")))
    assert outcomes == ["ACCEPTED", "SCENARIO_VERSION_CONFLICT"]
    with factory() as db:
        loaded = read_choices(db, 7, "a1")
        assert loaded["scenario_version"] == 2
        assert len(loaded["choices"]) == 1
        assert loaded["choices"][0]["planned_amount_ils"] in {"60.00", "70.00"}
        assert loaded["choices"][0]["state"] == "DRAFT_ONLY"
        revisions = db.scalars(select(ScenarioDraftRevision).where(
            ScenarioDraftRevision.scenario_id == "a1",
            ScenarioDraftRevision.version == 2,
        )).all()
        assert len(revisions) == 1


def _bound_severance_projection(result):
    cell = result["domain_results"]["severance"]
    assert cell["state"] == "BLOCKED"
    assert cell["result"] is None
    assert cell["result_fingerprint"] is None
    assert cell["professional_authority"] is False
    planning_projection = cell["planning"]
    assert planning_projection["contract"] == "SEVERANCE_SCENARIO_PLANNING_BINDING_V1"
    assert planning_projection["execution_allowed"] is False
    assert planning_projection["professional_authority"] is False
    for key in (
        "approved_withdrawal_ils", "actual_grants_paid_ils", "approved_continuity",
        "exempt_amount_ils", "tax_due_ils", "net_cashflow_ils",
        "withdrawable_capital_ils",
    ):
        assert planning_projection[key] is None
    for row in planning_projection["choices"]:
        assert row["execution_allowed"] is False
        assert row["professional_authority"] is False
        assert all(row[key] is None for key in (
            "actual_payment_ils", "tax_exemption_ils", "tax_due_ils",
            "net_cashflow_ils", "withdrawable_capital_ils",
        ))
    assert result["execution_allowed"] is False
    assert result["professional_authority"] is False
    assert result["net_income"]["state"] == "BLOCKED"
    assert result["net_income"]["result"] is None
    return planning_projection


def test_live_pg16_unified_severance_choices_contract_and_fingerprint(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    before = build(factory, client=7, scenario="a1")
    empty = _bound_severance_projection(before)
    assert empty["choices"] == []
    assert empty["client_id"] == 7 and empty["scenario_id"] == "a1"
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_WITHDRAWAL", "planned_amount_ils": "90.00",
        }], actor="unified-test")
    after = build(factory, client=7, scenario="a1")
    planning_view = _bound_severance_projection(after)
    assert planning_view["scenario_version"] == after["identity"]["scenario_version"] == 2
    assert planning_view["evidence_fingerprint"] == after[
        "financial_evidence"]["severance"]["evidence_fingerprint"]
    assert len(planning_view["choices"]) == 1
    row = planning_view["choices"][0]
    assert row["source_kind"] == "grant" and row["source_id"] == "choice-grant7"
    assert row["choice"] == "PLANNED_WITHDRAWAL"
    assert row["planned_amount_ils"] == "90.00"
    assert len(row["source_fingerprint"]) == 64
    assert row["state"] == "DRAFT_ONLY"
    assert row["saved_from_scenario_version"] == 2
    assert planning_view["planning_fingerprint"] != empty["planning_fingerprint"]
    assert after["result_fingerprint"] != before["result_fingerprint"]
    assert after == build(factory, client=7, scenario="a1")
    _all_unapproved(after)


def test_live_pg16_unified_severance_stale_source_and_renamed_scenario(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_SEVERANCE_CONTINUITY", "planned_amount_ils": "80.00",
        }], actor="unified-test")
    original = build(factory)
    original_view = _bound_severance_projection(original)
    with factory.begin() as db:
        rename_draft(db, 7, "a1", "Renamed only", expected=2, actor="unified-test")
    renamed = build(factory)
    assert _bound_severance_projection(renamed)["choices"][0]["state"] == "DRAFT_ONLY"
    with factory.begin() as db:
        db.get(EmploymentRecord, "choice-work7").notes = "Source change for fingerprint"
    stale = build(factory)
    stale_view = _bound_severance_projection(stale)
    row = stale_view["choices"][0]
    assert row["state"] == "BLOCKED_SOURCE_STALE"
    assert "BLOCKED_SOURCE_STALE" in row["blockers"]
    assert "BLOCKED_SOURCE_STALE" in stale["domain_results"]["severance"]["blockers"]
    assert stale_view["planning_fingerprint"] != original_view["planning_fingerprint"]
    assert stale["result_fingerprint"] != renamed["result_fingerprint"]
    assert stale["net_income"]["result"] is None


def test_live_pg16_unified_severance_overlap_and_overallocation_no_double_count(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        db.add(PensionProductComponent(
            component_id="projection-severance-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי", balance=Decimal("100.00"),
        ))
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[
            {"source_kind": "grant", "source_id": "choice-grant7",
             "choice": "PLANNED_PENSION_CONTINUITY", "planned_amount_ils": "50.00"},
            {"source_kind": "pension_component", "source_id": "projection-severance-c7",
             "choice": "PLANNED_WITHDRAWAL", "planned_amount_ils": "30.00"},
        ], actor="unified-test")
    overlap = build(factory)
    projection = _bound_severance_projection(overlap)
    assert len(projection["choices"]) == 2
    assert "SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in projection["blockers"]
    assert all(
        "SEVERANCE_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in row["blockers"]
        for row in projection["choices"]
    )
    assert projection["choices"][0]["source_kind"] == "grant"
    assert projection["choices"][1]["source_kind"] == "pension_component"
    assert overlap["domain_results"]["capital"]["result"] is None
    assert overlap["domain_results"]["pension_gross"]["result"] is None
    assert overlap["net_income"]["result"] is None
    with factory.begin() as db:
        db.add(ScenarioDraftDecision(
            decision_id="projection-later-alloc", scenario_id="a1",
            source_product_id="p7", source_component_id="projection-severance-c7",
            component_code="פיצויים_מעסיק_נוכחי", amount=Decimal("80.00"),
            action="capital_asset", effective_date=date(2027, 1, 1),
            validation_state="unverified", product_version_at_review=1,
        ))
    later = build(factory)
    later_projection = _bound_severance_projection(later)
    pension_component_row = next(row for row in later_projection["choices"]
                                 if row["source_kind"] == "pension_component")
    assert pension_component_row["state"] == "BLOCKED_COMPONENT_OVERALLOCATED"
    assert "BLOCKED_COMPONENT_OVERALLOCATED" in pension_component_row["blockers"]
    assert later["domain_results"]["severance"]["result"] is None
    assert later["result_fingerprint"] != overlap["result_fingerprint"]
    _all_unapproved(later)


def test_live_pg16_unified_severance_foreign_client_and_archive_isolation(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_WITHDRAWAL", "planned_amount_ils": None,
        }], actor="unified-test")
    first = build(factory, client=7, scenario="a1")
    other_scenario = build(factory, client=7, scenario="a2")
    other_client = build(factory, client=8, scenario="b1")
    assert _bound_severance_projection(other_scenario)["choices"] == []
    assert _bound_severance_projection(other_client)["choices"] == []
    assert len(_bound_severance_projection(first)["choices"]) == 1
    with factory.begin() as db:
        db.add(Grant(
            grant_id="unified-client8-grant", client_id=8,
            nominal_amount=Decimal("500.00"), grant_date=date(2024, 1, 1),
            work_start_date=date(2010, 1, 1), work_end_date=date(2024, 1, 1),
        ))
    assert build(factory, client=7, scenario="a1") == first
    with pytest.raises(DraftError):
        build(factory, client=8, scenario="a1")
    with factory.begin() as db:
        archive_draft(db, 7, "a1", expected=2, actor="unified-test")
    archived = build(factory, client=7, scenario="a1")
    row = _bound_severance_projection(archived)["choices"][0]
    assert row["state"] == "BLOCKED_SCENARIO_NOT_ACTIVE"
    assert "BLOCKED_SCENARIO_NOT_ACTIVE" in row["blockers"]
    assert archived["domain_results"]["severance"]["result"] is None


def test_live_pg16_unified_severance_changed_choice_updates_only_planning_authority(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_WITHDRAWAL", "planned_amount_ils": "50.00",
        }], actor="unified-test")
    first = build(factory)
    first_plan = _bound_severance_projection(first)
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=2, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_SEVERANCE_CONTINUITY", "planned_amount_ils": "50.00",
        }], actor="unified-test")
    second = build(factory)
    second_plan = _bound_severance_projection(second)
    assert first_plan["choices"][0]["source_fingerprint"] == second_plan["choices"][0]["source_fingerprint"]
    assert first_plan["choices"][0]["choice"] != second_plan["choices"][0]["choice"]
    assert first_plan["planning_fingerprint"] != second_plan["planning_fingerprint"]
    assert first["result_fingerprint"] != second["result_fingerprint"]
    assert all(cell["result"] is None for cell in (
        second["domain_results"]["severance"], second["net_income"],
    ))
    _all_unapproved(second)


def _fixation_readiness(result):
    cell = result["domain_results"]["fixation_tax"]
    assert cell["state"] == "BLOCKED"
    assert cell["result"] is None
    assert cell["result_fingerprint"] is None
    assert cell["professional_authority"] is False
    ready = cell["readiness"]
    assert ready["contract"] == "SCENARIO_FIXATION_READINESS_V1"
    assert ready["readiness_state"] == "BLOCKED"
    assert ready["execution_allowed"] is False
    assert ready["professional_authority"] is False
    assert ready["client_id"] == result["identity"]["client_id"]
    assert ready["scenario_id"] == result["identity"]["scenario_id"]
    assert ready["scenario_version"] == result["identity"]["scenario_version"]
    assert ready["manifest_fingerprint"] == result["base"]["manifest_fingerprint"]
    assert len(ready["readiness_fingerprint"]) == 64
    assert ready["approved_monthly_exemption_ils"] is None
    assert ready["tax_due_ils"] is None
    assert ready["net_cashflow_ils"] is None
    assert result["net_income"]["state"] == "BLOCKED"
    assert result["net_income"]["result"] is None
    return ready


def test_live_pg16_fixation_readiness_blocked_contract_and_no_inferred_year(pg16, monkeypatch):
    factory, _ = pg16
    from app.services import fixation_service
    from app.engines import fixation_engine

    def forbidden(*args, **kwargs):
        raise AssertionError("FIXATION_ENGINE_MUST_NOT_BE_CALLED")

    monkeypatch.setattr(fixation_service, "calculate_fixation_payload", forbidden)
    monkeypatch.setattr(fixation_engine, "calculate_fixation", forbidden)
    first = build(factory)
    second = build(factory)
    ready = _fixation_readiness(first)
    assert first == second
    assert ready["source_evidence"]["tax_year"] is None
    assert ready["source_evidence"]["official_parameter_set"] is None
    assert ready["mapping"]["parameter_set"]["present"] is False
    assert ready["mapping"]["parameter_set"]["blocker"] == "FIXATION_SCENARIO_TAX_YEAR_MISSING"
    assert ready["mapping"]["m07_input_reference"]["verified"] is False
    assert "FIXATION_ELIGIBILITY_SCENARIO_BINDING_MISSING" in ready["blockers"]
    assert first["domain_results"]["fixation_tax"]["producer_contract"] == "SCENARIO_FIXATION_READINESS_V1"
    _all_unapproved(first)


def test_live_pg16_fixation_readiness_grant_employment_capitalization_fingerprint(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        db.add(ActualCapitalization(
            capitalization_id="readiness-cap7", client_id=7,
            amount=Decimal("50.00"), capitalization_date=date(2023, 1, 1),
            source_label="Synthetic capitalization", source_basis="reported",
        ))
        db.add(FixationRun(
            client_id=7, calculation_version="historical-only",
            status="success", is_latest=True,
        ))
    first = build(factory)
    before = _fixation_readiness(first)
    # Non-semantic free-text audit notes are deliberately excluded from
    # readiness provenance, even if the general evidence envelope changes.
    with factory.begin() as db:
        db.get(ActualCapitalization, "readiness-cap7").notes = "internal display note only"
    assert _fixation_readiness(build(factory))["readiness_fingerprint"] == before[
        "readiness_fingerprint"]
    assert before["source_evidence"]["historical_fixation_run_references"][0][
        "authority_state"] == "HISTORICAL_CALCULATION_NOT_TAX_AUTHORITY_APPROVAL"
    assert before["mapping"]["tax_authority_approval"]["verified"] is False
    with factory.begin() as db:
        db.get(Grant, "choice-grant7").nominal_amount = Decimal("120.00")
    changed_grant = build(factory)
    second = _fixation_readiness(changed_grant)
    assert second["readiness_fingerprint"] != before["readiness_fingerprint"]
    with factory.begin() as db:
        db.get(EmploymentRecord, "choice-work7").notes = "Changed verified source context"
    changed_employment = build(factory)
    third = _fixation_readiness(changed_employment)
    assert third["readiness_fingerprint"] != second["readiness_fingerprint"]
    with factory.begin() as db:
        db.get(ActualCapitalization, "readiness-cap7").amount = Decimal("70.00")
    changed_capitalization = build(factory)
    fourth = _fixation_readiness(changed_capitalization)
    assert fourth["readiness_fingerprint"] != third["readiness_fingerprint"]
    assert fourth["source_evidence"]["historical_capitalizations"][0]["reported_amount_ils"] == "70.00"
    _all_unapproved(changed_capitalization)


def test_live_pg16_fixation_readiness_severance_choice_overlap_and_client_isolation(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        db.add(PensionProductComponent(
            component_id="readiness-sev-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי", balance=Decimal("100.00"),
        ))
    unselected = build(factory, client=7, scenario="a1")
    with factory.begin() as db:
        replace_choices(db, 7, "a1", expected_version=1, choices=[{
            "source_kind": "grant", "source_id": "choice-grant7",
            "choice": "PLANNED_PENSION_CONTINUITY", "planned_amount_ils": "40.00",
        }], actor="readiness-test")
    selected = build(factory, client=7, scenario="a1")
    ready = _fixation_readiness(selected)
    assert ready["readiness_fingerprint"] != _fixation_readiness(unselected)["readiness_fingerprint"]
    assert ready["mapping"]["future_grant_reservation"]["present"] is True
    assert ready["mapping"]["future_grant_reservation"]["verified"] is False
    assert "FIXATION_GRANT_COMPONENT_OVERLAP_UNRECONCILED" in ready["blockers"]
    assert ready["source_evidence"]["severance_choice_source_ids"][0]["source_kind"] == "grant"
    assert ready["approved_monthly_exemption_ils"] is None
    other_scenario = _fixation_readiness(build(factory, client=7, scenario="a2"))
    other_client = _fixation_readiness(build(factory, client=8, scenario="b1"))
    assert other_scenario["mapping"]["future_grant_reservation"]["present"] is False
    assert other_client["source_evidence"]["grants"] == []
    assert other_client["source_evidence"]["severance_choice_source_ids"] == []
    with factory.begin() as db:
        db.add(Grant(
            grant_id="readiness-foreign-grant8", client_id=8,
            nominal_amount=Decimal("777.00"), grant_date=date(2024, 1, 1),
            work_start_date=date(2010, 1, 1), work_end_date=date(2024, 1, 1),
        ))
    assert build(factory, client=7, scenario="a1") == selected


def test_live_pg16_fixation_readiness_finalized_m07_evidence_is_not_admission(pg16):
    factory, _ = pg16
    t = datetime(2026, 10, 1, tzinfo=timezone.utc)
    def add_revision(db, revision_id, number, fingerprint):
        db.add(M07EvidenceRevision(
            m07_evidence_revision_id=revision_id, profile_id="synthetic-fixation",
            client_id=7, revision_number=number, tax_year=2026,
            event_year=2026, event_type="fixation",
            schema_version="test-v1", rule_version="test-v1",
            status="finalized",
            authority_classification="EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY",
            technical_outcomes=[], canonical_payload={"eligibility_date": "2026-10-01"},
            evidence_fingerprint=fingerprint,
            source_snapshot_fingerprint="a" * 64,
            fingerprint_algorithm_version="sha256-v1",
            created_at=t, created_by="synthetic-test",
            finalized_at=t, finalized_by="synthetic-test",
        ))
    with factory.begin() as db:
        add_revision(db, "readiness-m07-1", 1, "b" * 64)
    first = build(factory)
    one = _fixation_readiness(first)
    assert one["mapping"]["m07_input_reference"]["present"] is True
    assert one["mapping"]["m07_input_reference"]["verified"] is False
    assert one["source_evidence"]["tax_year"] is None
    assert one["source_evidence"]["official_parameter_set"] is None
    assert one["source_evidence"]["m07"][0]["tax_year_on_client_evidence_not_scenario_tax_year"] == 2026
    with factory.begin() as db:
        add_revision(db, "readiness-m07-2", 2, "c" * 64)
    second = build(factory)
    two = _fixation_readiness(second)
    assert two["readiness_fingerprint"] != one["readiness_fingerprint"]
    assert len(two["source_evidence"]["m07"]) == 2
    assert two["readiness_state"] == "BLOCKED"
    assert second["net_income"]["result"] is None
    assert _fixation_readiness(build(factory, client=8, scenario="b1"))[
        "source_evidence"]["m07"] == []


def _review_replace(factory, *, client=7, scenario="a1", version=0,
                    decisions=None, expected_readiness=None, actor="planner-test"):
    latest = build(factory, client=client, scenario=scenario)["domain_results"][
        "fixation_tax"]["readiness"]
    data = FixationProfessionalDraftReplace(
        expected_approval_version=version,
        expected_scenario_version=latest["scenario_version"],
        expected_manifest_fingerprint=latest["manifest_fingerprint"],
        expected_readiness_fingerprint=(
            expected_readiness if expected_readiness is not None else latest["readiness_fingerprint"]
        ),
        decisions=decisions or [],
    )
    with factory.begin() as db:
        return fixation_review.save_draft(db, client, scenario, data, actor)


def test_pg16_fixation_professional_review_save_reload_history_and_blocked_gate(pg16, monkeypatch):
    factory, _ = pg16
    from app.services import fixation_service
    from app.engines import fixation_engine

    def forbidden(*args, **kwargs):
        raise AssertionError("FIXATION_ENGINE_MUST_NOT_RUN")
    monkeypatch.setattr(fixation_service, "calculate_fixation_payload", forbidden)
    monkeypatch.setattr(fixation_engine, "calculate_fixation", forbidden)
    original = build(factory)
    assert original["domain_results"]["fixation_tax"]["professional_review"]["record_status"] == "MISSING"
    selected = [FixationProfessionalDecision(
        group="eligibility", source_id="revision-pending",
        determination="PLANNER_ASSERTED", reason="Reviewer-recorded assertion only",
        eligibility_date=date(2026, 10, 1), evidence_references=["document-ref-1"],
    )]
    first = _review_replace(factory, decisions=selected)
    assert first["approval_version"] == 1
    assert first["record_status"] == "DRAFT"
    assert first["validity_state"] == "BLOCKED"
    assert first["professional_authority"] is False
    assert first["tax_authority_approval"] is None
    assert "FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED" in first["blockers"]
    with factory() as db:
        assert fixation_review.read(db, 7, "a1") == first
        versions = fixation_review.history(db, 7, "a1")
        assert len(versions) == 1
        assert versions[0]["action"] == "SAVE_DRAFT"
        assert versions[0]["actor_id"] == "planner-test"
        denied = fixation_review.request_internal_approval(
            db, 7, "a1", 1, first["approval_fingerprint"], "planner-test")
        assert denied["approval_attempt_state"] == "BLOCKED"
        assert "FIXATION_PROFESSIONAL_GATE_NOT_ADMITTED" in denied["blockers"]
        assert denied["professional_authority"] is False
        assert denied["tax_authority_approval"] is None
    updated = _review_replace(factory, version=1, decisions=[
        FixationProfessionalDecision(
            group="eligibility", source_id="revision-pending",
            determination="REQUIRES_REVIEW", reason="Not yet verified",
        )
    ])
    assert updated["approval_version"] == 2
    assert updated["approval_fingerprint"] != first["approval_fingerprint"]
    with factory() as db:
        assert len(fixation_review.history(db, 7, "a1")) == 2
    bound = build(factory)
    assert bound["domain_results"]["fixation_tax"]["result"] is None
    assert bound["domain_results"]["fixation_tax"]["professional_review"]["approval_version"] == 2
    assert bound["net_income"]["result"] is None
    assert bound["professional_authority"] is False
    assert bound["execution_allowed"] is False


def test_pg16_fixation_professional_review_cas_atomic_and_foreign_isolation(pg16):
    factory, _ = pg16
    first = _review_replace(factory)
    with pytest.raises(DraftError, match="FIXATION_APPROVAL_VERSION_CONFLICT"):
        _review_replace(factory, version=0)
    with factory() as db:
        assert len(fixation_review.history(db, 7, "a1")) == 1
        other_scenario = fixation_review.read(db, 7, "a2")
        other_client = fixation_review.read(db, 8, "b1")
        assert other_scenario["record_status"] == "MISSING"
        assert other_client["record_status"] == "MISSING"
        with pytest.raises(DraftError, match="SCENARIO_NOT_FOUND"):
            fixation_review.read(db, 8, "a1")
    own = _review_replace(factory, client=8, scenario="b1")
    assert own["approval_version"] == 1
    assert own["approval_id"] != first["approval_id"]
    with factory() as db:
        assert fixation_review.read(db, 7, "a1")["approval_version"] == 1
        assert len(fixation_review.history(db, 8, "b1")) == 1


def test_pg16_fixation_professional_review_material_stale_and_no_false_stale(pg16):
    factory, _ = pg16
    _severance_grant_source(factory)
    with factory.begin() as db:
        db.add(ActualCapitalization(
            capitalization_id="approval-cap7", client_id=7,
            amount=Decimal("50.00"), capitalization_date=date(2022, 1, 1),
            source_label="Synthetic", source_basis="recorded",
        ))
    initial = _review_replace(factory)
    with factory.begin() as db:
        db.get(ActualCapitalization, "approval-cap7").notes = "Cosmetic display note"
    with factory() as db:
        stable = fixation_review.read(db, 7, "a1")
    assert stable["validity_state"] == "BLOCKED"
    assert stable["readiness_fingerprint_at_save"] == initial["readiness_fingerprint_at_save"]
    with factory.begin() as db:
        db.get(Grant, "choice-grant7").nominal_amount = Decimal("125.00")
    with factory() as db:
        stale = fixation_review.read(db, 7, "a1")
        assert stale["validity_state"] == "STALE"
        assert "FIXATION_PROFESSIONAL_APPROVAL_STALE" in stale["blockers"]
        with pytest.raises(DraftError, match="FIXATION_PROFESSIONAL_APPROVAL_STALE"):
            fixation_review.request_internal_approval(
                db, 7, "a1", 1, initial["approval_fingerprint"], "planner-test")
    with pytest.raises(DraftError, match="FIXATION_APPROVAL_SOURCE_CONFLICT"):
        _review_replace(
            factory, version=1,
            expected_readiness=initial["readiness_fingerprint_at_save"])
    with factory() as db:
        assert len(fixation_review.history(db, 7, "a1")) == 1
    replacement = _review_replace(factory, version=1)
    assert replacement["approval_version"] == 2
    assert replacement["validity_state"] == "BLOCKED"
    assert replacement["approval_fingerprint"] != initial["approval_fingerprint"]


def test_pg16_fixation_professional_review_concurrent_cas_one_winner(pg16):
    factory, _ = pg16
    initial = _review_replace(factory)
    readiness = build(factory)["domain_results"]["fixation_tax"]["readiness"]
    request = FixationProfessionalDraftReplace(
        expected_approval_version=1,
        expected_scenario_version=readiness["scenario_version"],
        expected_manifest_fingerprint=readiness["manifest_fingerprint"],
        expected_readiness_fingerprint=readiness["readiness_fingerprint"],
        decisions=[],
    )

    def writer():
        try:
            with factory.begin() as db:
                fixation_review.save_draft(db, 7, "a1", request, "planner-test")
            return "COMMITTED"
        except DraftError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(lambda _: writer(), range(2)))
    assert outcomes == ["COMMITTED", "FIXATION_APPROVAL_VERSION_CONFLICT"]
    with factory() as db:
        rows = fixation_review.history(db, 7, "a1")
        assert len(rows) == 2
        assert [r["approval_version"] for r in rows] == [1, 2]
        assert fixation_review.read(db, 7, "a1")["approval_version"] == 2


def test_pg16_fixation_professional_review_selected_foreign_grant_remains_blocked(pg16):
    factory, _ = pg16
    with factory.begin() as db:
        db.add(Grant(
            grant_id="other-client-only-grant", client_id=8,
            nominal_amount=Decimal("175.00"), grant_date=date(2024, 1, 1),
            work_start_date=date(2011, 1, 1), work_end_date=date(2024, 1, 1),
        ))
    record = FixationProfessionalDecision(
        group="historical_grant", source_id="other-client-only-grant",
        determination="PLANNER_ASSERTED", reason="Unverified candidate",
    )
    saved = _review_replace(factory, decisions=[record])
    assert saved["validity_state"] == "BLOCKED"
    assert "FIXATION_REVIEW_GRANT_SOURCE_NOT_FOUND" in saved["blockers"]
    assert saved["selected_source_evidence"][0]["source_evidence"] is None
    assert saved["tax_authority_approval"] is None
    with factory() as db:
        assert fixation_review.read(db, 7, "a1") == saved


def test_pg16_fixation_professional_review_migration_round_trip(pg16):
    """Run the actual new Alembic migration in another disposable PG16 schema."""
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    from uuid import uuid4
    from sqlalchemy import create_engine, inspect
    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext
    from app.models.client import Client
    from tests.test_scenario_unified_result_real_postgresql import _url

    module_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / (
        "e53f1c0a7d23_scenario_fixation_professional_approval.py"
    )
    spec = spec_from_file_location("test_s53_approval_migration", module_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(_url())
    schema = "fixation_approval_" + uuid4().hex[:12]
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        scoped = engine.execution_options(schema_translate_map={None: schema})
        with scoped.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            Base.metadata.create_all(
                connection, tables=[Client.__table__, ScenarioDraft.__table__],
            )
            previous_op = migration.op
            try:
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
                inspector = inspect(connection)
                assert inspector.has_table("scenario_fixation_approval_heads")
                assert inspector.has_table("scenario_fixation_approval_revisions")
                triggers = connection.scalars(text("""
                    SELECT t.tgname FROM pg_trigger AS t
                    JOIN pg_class AS c ON c.oid = t.tgrelid
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = :schema
                      AND c.relname = 'scenario_fixation_approval_revisions'
                      AND NOT t.tgisinternal
                """), {"schema": schema}).all()
                assert "trg_scenario_fixation_approval_revision_immutable" in triggers
                migration.downgrade()
                assert not inspect(connection).has_table("scenario_fixation_approval_heads")
                assert not inspect(connection).has_table("scenario_fixation_approval_revisions")
            finally:
                migration.op = previous_op
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_pg16_fixation_professional_review_get_exposes_server_current_readiness_cas(pg16):
    factory, _ = pg16
    with factory() as db:
        missing = fixation_review.read(db, 7, "a1")
        assert missing["record_status"] == "MISSING"
        current = missing["current_readiness"]
        assert current["scenario_version"] == 1
        assert current["readiness_state"] == "BLOCKED"
        assert len(current["manifest_fingerprint"]) == 64
        assert len(current["readiness_fingerprint"]) == 64
        assert current["professional_authority"] is False
        assert current["execution_allowed"] is False
    # The UI must use this identical server-derived CAS tuple.
    updated = _review_replace(factory)
    assert updated["approval_version"] == 1
    assert updated["current_readiness"]["readiness_fingerprint"] == current["readiness_fingerprint"]
    with factory.begin() as db:
        db.get(ScenarioDraft, "a1").name = "Nonfinancial display title"
    # Re-derive rather than trust client-supplied fingerprints.
    with factory() as db:
        fresh = fixation_review.read(db, 7, "a1")
    assert fresh["current_readiness"]["manifest_fingerprint"] == current["manifest_fingerprint"]
    assert fresh["current_readiness"]["readiness_fingerprint"] == current["readiness_fingerprint"]
    assert fresh["tax_authority_approval"] is None


def _prepared_fixation_sources(factory):
    now = datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
    with factory.begin() as db:
        row = create_official_parameter_set_draft(
            db_session=db,
            request=OfficialParameterSetCreate(
                parameter_set_id="scenario-fixation-2026", tax_year=2026,
                effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
                parameter_set_version="2026-r1",
                values=OfficialParameterValues(
                    monthly_cap="1000", exemption_percentage="0.5",
                    capital_multiplier="180", grant_impact_multiplier="1.35"),
                source_type="official_publication", source_title="Synthetic official source",
                official_source_reference="official://synthetic/2026",
                source_publication_date=date(2025, 12, 15),
                source_recorded_at=now, source_evidence_metadata={"document": "test-only"},
                created_by="test-admin"), timestamp=now)
        verify_official_parameter_set(
            db_session=db, parameter_set_id=row.parameter_set_id,
            request=OfficialParameterVerificationRequest(
                verified_by="test-verifier", verification_note="synthetic verified source"),
            timestamp=now)
        activate_official_parameter_set(
            db_session=db, parameter_set_id=row.parameter_set_id,
            request=OfficialParameterActivationRequest(activated_by="test-activator"),
            timestamp=now)
        revision = M07EvidenceRevision(
            m07_evidence_revision_id="scenario-fixation-m07", profile_id="fixation-profile-7",
            client_id=7, revision_number=1, tax_year=2026, event_year=2026,
            event_type="fixation", schema_version="pkg004b1.m07-evidence.v1",
            rule_version="pkg004b1.technical-assessment.v1",
            status="draft", authority_classification="EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY",
            technical_outcomes=[], canonical_payload={"eligibility_date": "2026-10-01"},
            evidence_fingerprint="1" * 64, source_snapshot_fingerprint="2" * 64,
            fingerprint_algorithm_version="sha256-v1", created_at=now,
            created_by="test", finalized_at=None, finalized_by=None)
        db.add(revision)
        db.flush()
        db.add(M07FactEvidence(
            fact_evidence_id="scenario-fixation-eligibility", m07_evidence_revision_id="scenario-fixation-m07",
            client_id=7, field_code="eligibility_date", fact_identity_key="3" * 64,
            structured_value="2026-10-01", collection_state="recorded", collection_basis=None,
            verification_state="verified", authority_classification="EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY",
            source_type="official_document", source_record_type="document", source_record_id="eligibility-7",
            source_document_reference="document://eligibility-7", source_date=date(2026, 10, 1),
            source_excerpt=None, source_metadata={}, recorded_at=now, recorded_by="test",
            verified_at=now, verified_by="test", verification_basis="synthetic verified document",
            assertion_id=None, content_fingerprint="4" * 64))
        db.flush()
        finalize_m07_revision(
            db_session=db, client_id=7, revision_id="scenario-fixation-m07",
            actor="test", assessment=AssessmentRun(), timestamp=now,
        )


def _prepared_review(factory):
    ready = build(factory)["domain_results"]["fixation_tax"]["readiness"]
    request = FixationProfessionalDraftReplace(
        expected_approval_version=0, expected_scenario_version=ready["scenario_version"],
        expected_manifest_fingerprint=ready["manifest_fingerprint"],
        expected_readiness_fingerprint=ready["readiness_fingerprint"],
        decisions=[
            FixationProfessionalDecision(
                group="eligibility", source_id="scenario-fixation-m07",
                determination="PLANNER_ASSERTED", reason="Verified eligibility evidence selected",
                evidence_references=["document://eligibility-7"], eligibility_date=date(2026, 10, 1)),
            FixationProfessionalDecision(
                group="tax_year_and_parameters", source_id="scenario-fixation-2026",
                determination="PLANNER_ASSERTED", reason="Active official parameters selected",
                evidence_references=["official://synthetic/2026"], tax_year=2026,
                parameter_set_id="scenario-fixation-2026"),
            FixationProfessionalDecision(
                group="pension_classification", source_id="d_a1",
                determination="PLANNER_ASSERTED", reason="Professional pension classification",
                evidence_references=["document://pension-classification-7"],
                tax_classification="QUALIFYING_PENSION_FOR_FIXATION"),
        ],
        admission_controls=FixationAdmissionControls(
            calculation_version="pkg-012-m08d-v1",
            grants_collection={"state": "confirmed_none", "evidence_references": ["review://grants-7"]},
            actual_capitalizations_collection={
                "state": "confirmed_none", "evidence_references": ["review://capitalizations-7"]},
            idf={"applicability": "NOT_APPLICABLE",
                 "evidence_references": ["review://idf-7"], "input": None},
        ),
    )
    with factory.begin() as db:
        fixation_review.save_draft(db, 7, "a1", request, "trusted-planner")


def test_pg16_fixation_admission_preparation_positive_and_no_tax_execution(pg16, monkeypatch):
    factory, _ = pg16
    _prepared_fixation_sources(factory)
    _prepared_review(factory)
    from app.services import fixation_service
    from app.engines import fixation_engine
    def forbidden(*args, **kwargs):
        raise AssertionError("FIXATION_ENGINE_MUST_NOT_RUN")
    monkeypatch.setattr(fixation_service, "calculate_fixation_payload", forbidden)
    monkeypatch.setattr(fixation_engine, "calculate_fixation", forbidden)
    with factory() as db:
        first = fixation_preparation.prepare(db, 7, "a1")
        second = fixation_preparation.prepare(db, 7, "a1")
    assert first == second
    assert first["state"] == "PREPARED"
    assert first["candidate"]["calculation_version"] == "pkg-012-m08d-v1"
    assert first["candidate"]["grants_collection_state"] == "confirmed_none"
    assert first["candidate"]["actual_capitalizations_collection_state"] == "confirmed_none"
    assert first["candidate"]["idf"] is None
    assert first["professional_authority"] is False
    assert first["execution_allowed"] is False
    assert first["tax_authority_approval"] is None


def test_pg16_fixation_admission_preparation_fail_closed_and_isolated(pg16):
    factory, _ = pg16
    with pytest.raises(ValueError):
        FixationProfessionalDecision(
            group="pension_classification", source_id="d_a1",
            determination="PLANNER_ASSERTED", reason="free text must not become admission",
            tax_classification="free-form-tax-opinion")
    with factory() as db:
        old = fixation_preparation.prepare(db, 7, "a1")
        foreign = fixation_preparation.prepare(db, 8, "b1")
    assert old["state"] == "INCOMPLETE"
    assert "FIXATION_PREPARATION_CONTROLS_MISSING" in old["incomplete_reasons"]
    assert foreign["client_id"] == 8 and foreign["scenario_id"] == "b1"
    _prepared_fixation_sources(factory)
    _prepared_review(factory)
    with factory() as db:
        prepared = fixation_preparation.prepare(db, 7, "a1")
    with factory.begin() as db:
        db.add(PensionProductComponent(
            component_id="fixation-overlap-c7", product_id="p7",
            component_code="פיצויים_מעסיק_נוכחי", balance=Decimal("100.00")))
        db.add(Grant(
            grant_id="fixation-overlap-grant7", client_id=7,
            nominal_amount=Decimal("100.00"), grant_date=date(2025, 12, 31),
            work_start_date=date(2020, 1, 1), work_end_date=date(2025, 12, 31)))
    with factory() as db:
        changed = fixation_preparation.prepare(db, 7, "a1")
    assert changed["state"] == "BLOCKED"
    assert "FIXATION_PREPARATION_SOURCE_OVERLAP_UNRESOLVED" in changed["blockers"]
    assert "FIXATION_PREPARATION_GRANTS_CONFIRMED_NONE_CONTRADICTS_SOURCE" in changed["blockers"]
    assert changed["preparation_fingerprint"] != prepared["preparation_fingerprint"]
    assert changed["candidate"] is None


def _prepared_fixation_items(factory, *, grant=True, capitalization=True, idf=True,
                             grant_nominal=True, include_evidence=True):
    """Actual PostgreSQL source rows and versioned reviewer decisions."""
    _prepared_fixation_sources(factory)
    if grant or capitalization:
        with factory.begin() as db:
            if grant:
                db.add(Grant(
                    grant_id="preparation-grant7", client_id=7,
                    employment_record_id=None, employer_name="Synthetic employer",
                    employer_withholding_file_number="synthetic-withholding",
                    nominal_amount=Decimal("125.00") if grant_nominal else None,
                    indexed_amount=Decimal("130.00") if grant_nominal else None,
                    grant_date=date(2025, 12, 31),
                    work_start_date=date(2011, 1, 1), work_end_date=date(2025, 12, 31),
                ))
            if capitalization:
                db.add(ActualCapitalization(
                    capitalization_id="preparation-cap7", client_id=7,
                    amount=Decimal("72.00"), capitalization_date=date(2024, 1, 1),
                    source_label="Synthetic historical commutation",
                    source_basis="official_statement",
                ))
    _prepared_review(factory)
    with factory() as db:
        previous = fixation_review.read(db, 7, "a1")
    current = previous["current_readiness"]
    assertions = [FixationProfessionalDecision.model_validate(item)
                  for item in previous["decisions"]]
    if grant:
        assertions.append(FixationProfessionalDecision(
            group="historical_grant", source_id="preparation-grant7",
            determination="PLANNER_ASSERTED", reason="Reviewed payment and grant origin",
            inclusion_decision="include", support_status="supported",
            accepted_for_use=True, payment_status="PAID",
            evidence_references=["document://synthetic-grant-7"] if include_evidence else [],
        ))
    if capitalization:
        assertions.append(FixationProfessionalDecision(
            group="historical_capitalization", source_id="preparation-cap7",
            determination="PLANNER_ASSERTED", reason="Reviewed actual historical commutation",
            inclusion_decision="include", support_status="supported",
            accepted_for_use=True,
            evidence_references=["document://synthetic-cap-7"] if include_evidence else [],
        ))
    controls = FixationAdmissionControls(
        calculation_version="pkg-012-m08d-v1",
        grants_collection={"state": "items_recorded" if grant else "confirmed_none",
                           "evidence_references": ["document://synthetic-grant-collection"]},
        actual_capitalizations_collection={
            "state": "items_recorded" if capitalization else "confirmed_none",
            "evidence_references": ["document://synthetic-cap-collection"]},
        idf=({
            "applicability": "APPLICABLE",
            "evidence_references": ["document://synthetic-idf"],
            "input": {
                "idf_id": "synthetic-idf-7", "reduction_amount": 50.0,
                "original_commutation_percent": 25.0, "current_commutation_percent": 20.0,
                "commutation_date": date(2024, 1, 1),
                "promoter_age_date": date(2026, 10, 1),
                "source_label": "Synthetic military pension statement",
            },
        } if idf else {
            "applicability": "NOT_APPLICABLE",
            "evidence_references": ["document://synthetic-idf-none"], "input": None,
        }),
    )
    request = FixationProfessionalDraftReplace(
        expected_approval_version=previous["approval_version"],
        expected_scenario_version=current["scenario_version"],
        expected_manifest_fingerprint=current["manifest_fingerprint"],
        expected_readiness_fingerprint=current["readiness_fingerprint"],
        decisions=assertions, admission_controls=controls,
    )
    with factory.begin() as db:
        fixation_review.save_draft(db, 7, "a1", request, "trusted-planner")


def test_pg16_fixation_preparation_recorded_grants_caps_idf_real_positive(pg16, monkeypatch):
    factory, _ = pg16
    _prepared_fixation_items(factory)
    from app.services import fixation_service, fixation_admission_service
    from app.engines import fixation_engine
    def forbidden(*args, **kwargs):
        raise AssertionError("TAX_OR_ADMISSION_ENGINE_MUST_NOT_RUN")
    monkeypatch.setattr(fixation_service, "calculate_fixation_payload", forbidden)
    monkeypatch.setattr(fixation_engine, "calculate_fixation", forbidden)
    monkeypatch.setattr(fixation_admission_service, "parse_and_admit_fixation_payload", forbidden)
    with factory() as db:
        a = fixation_preparation.prepare(db, 7, "a1")
        b = fixation_preparation.prepare(db, 7, "a1")
    assert a == b
    assert a["state"] == "PREPARED", (a["blockers"], a["incomplete_reasons"])
    assert len(a["preparation_fingerprint"]) == 64
    candidate = a["candidate"]
    assert candidate["grants_collection_state"] == "items_recorded"
    assert len(candidate["grants"]) == 1
    assert candidate["grants"][0]["grant_id"] == "preparation-grant7"
    assert candidate["grants"][0]["inclusion_decision"] == "include"
    assert candidate["grants"][0]["status"] == "PAID"
    assert candidate["grants"][0]["indexed_amount"] == "130.00"
    assert candidate["actual_capitalizations_collection_state"] == "items_recorded"
    assert len(candidate["actual_capitalizations"]) == 1
    assert candidate["actual_capitalizations"][0]["capitalization_id"] == "preparation-cap7"
    assert candidate["actual_capitalizations"][0]["inclusion_decision"] == "include"
    assert candidate["idf"]["idf_id"] == "synthetic-idf-7"
    assert candidate["m07_input_reference"]["b1_evidence_revision_id"] == "scenario-fixation-m07"
    assert candidate["parameter_set"]["parameter_set_id"] == "scenario-fixation-2026"
    assert a["professional_authority"] is False
    assert a["execution_allowed"] is False
    assert a["tax_authority_approval"] is None
    with factory.begin() as db:
        db.get(Grant, "preparation-grant7").indexed_amount = Decimal("135.00")
    with factory() as db:
        changed = fixation_preparation.prepare(db, 7, "a1")
    assert changed["state"] == "BLOCKED"
    assert "FIXATION_PREPARATION_PROFESSIONAL_REVIEW_STALE" in changed["blockers"]
    assert changed["preparation_fingerprint"] != a["preparation_fingerprint"]
    assert changed["candidate"] is None


def test_pg16_fixation_preparation_missing_grant_amount_is_controlled(pg16):
    factory, _ = pg16
    _prepared_fixation_items(factory, capitalization=False, idf=False, grant_nominal=False)
    with factory() as db:
        result = fixation_preparation.prepare(db, 7, "a1")
    assert result["state"] == "INCOMPLETE"
    assert "FIXATION_PREPARATION_GRANT_AMOUNT_MISSING" in result["incomplete_reasons"]
    assert result["candidate"] is None


def test_pg16_fixation_preparation_missing_item_evidence_is_controlled(pg16):
    factory, _ = pg16
    _prepared_fixation_items(factory, idf=False, include_evidence=False)
    with factory() as db:
        result = fixation_preparation.prepare(db, 7, "a1")
    assert result["state"] == "INCOMPLETE"
    assert "FIXATION_PREPARATION_GRANT_DECISION_OR_EVIDENCE_INCOMPLETE" in result["incomplete_reasons"]
    assert "FIXATION_PREPARATION_CAPITALIZATION_DECISION_OR_EVIDENCE_INCOMPLETE" in result["incomplete_reasons"]
    assert result["candidate"] is None


def test_pg16_fixation_preparation_no_false_stale_on_nonmaterial_note(pg16):
    factory, _ = pg16
    _prepared_fixation_items(factory)
    with factory() as db:
        before = fixation_preparation.prepare(db, 7, "a1")
    assert before["state"] == "PREPARED", before
    with factory.begin() as db:
        db.get(ActualCapitalization, "preparation-cap7").notes = "Presentation note only"
    with factory() as db:
        after = fixation_preparation.prepare(db, 7, "a1")
    assert after["state"] == "PREPARED", (after["blockers"], after["incomplete_reasons"])
    assert after["preparation_fingerprint"] == before["preparation_fingerprint"]


def test_pg16_fixation_preparation_collection_source_mismatch_blocked(pg16):
    factory, _ = pg16
    _prepared_fixation_sources(factory)
    _prepared_review(factory)  # Both collections are explicitly confirmed_none.
    with factory.begin() as db:
        db.add(ActualCapitalization(
            capitalization_id="unrecorded-preparation-cap7", client_id=7,
            amount=Decimal("90.00"), capitalization_date=date(2025, 2, 1),
            source_label="Unreviewed capitalization", source_basis="synthetic_record",
        ))
    with factory() as db:
        result = fixation_preparation.prepare(db, 7, "a1")
    assert result["state"] == "BLOCKED"
    assert result["candidate"] is None
    assert "FIXATION_PREPARATION_CAPITALIZATIONS_CONFIRMED_NONE_CONTRADICTS_SOURCE" in result["blockers"]


def test_pg16_fixation_preparation_applicable_idf_requires_complete_input(pg16):
    factory, _ = pg16
    _prepared_fixation_sources(factory)
    with pytest.raises(ValueError):
        FixationAdmissionControls(
            calculation_version="pkg-012-m08d-v1",
            grants_collection={"state": "confirmed_none", "evidence_references": ["review://grants"]},
            actual_capitalizations_collection={"state": "confirmed_none", "evidence_references": ["review://caps"]},
            idf={"applicability": "APPLICABLE", "input": None,
                 "evidence_references": ["document://idf"]},
        )
    with pytest.raises(ValueError):
        FixationAdmissionControls(
            calculation_version="pkg-012-m08d-v1",
            grants_collection={"state": "confirmed_none", "evidence_references": ["review://grants"]},
            actual_capitalizations_collection={"state": "confirmed_none", "evidence_references": ["review://caps"]},
            idf={"applicability": "APPLICABLE", "evidence_references": ["document://idf"],
                 "input": {"idf_id": "invalid", "reduction_amount": -1,
                           "original_commutation_percent": 25, "current_commutation_percent": 20,
                           "commutation_date": "2025-01-01", "promoter_age_date": "2026-10-01"}},
        )
    with factory() as db:
        result = fixation_preparation.prepare(db, 7, "a1")
    assert result["state"] == "INCOMPLETE"
    assert result["candidate"] is None
