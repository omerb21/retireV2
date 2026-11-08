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
from app.models.m07_evidence import (
    M07EvidenceRevision, M07FactEvidence, M07PlannerAssertion, M07AssessmentFinding,
)
from app.models.official_parameter_set import OfficialParameterSet
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
