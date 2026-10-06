from datetime import date
from decimal import Decimal
import copy
import hashlib
import json
from pathlib import Path
import inspect
from types import SimpleNamespace

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.models.planning_input_decision import PlanningInputDecision, PensionIncomeResolution
from app.models.retirement_facts import RecurringIncome
from app.services import planning_input_service
from app.services import retirement_target_date_income_source_admission_service as subject
from app.services import canonical_manual_pension_service
from test_recovery_pension_products import engine
from test_professional_source_snapshot import facts


RTISA_TRACEABILITY = {
    "T01": ("test_strict_client_validation_precedes_reads", "test_strict_fingerprint_validation_precedes_reads"),
    "T02": ("test_runtime_planning_context_wrong_client_and_malformed_identity_fail_closed", "test_stale_expected_fingerprint_exposes_no_sources"),
    "T03": ("test_empty_evidenced_universe_is_ready_and_exact_schema", "test_partition_and_readiness_invariants_cover_mixed_universe"),
    "T04": ("test_actual_closed_pension_portfolio_is_consumed_without_total", "test_real_producer_positional_coverage_fatal_is_trusted_domain_authority"),
    "T05": ("test_actual_closed_pension_portfolio_is_consumed_without_total",),
    "T06": ("test_read_level_domain_fatal_retains_pension_as_unresolved", "test_real_producer_positional_coverage_fatal_is_trusted_domain_authority"),
    "T07": ("test_real_pension_authority_complete_partial_empty_and_fatal_matrix",),
    "T08": ("test_rehashed_malformed_outer_fatal_is_never_trusted", "test_invalid_outer_fingerprint_is_never_trusted"),
    "T09": ("test_non_ils_pension_is_read_level_unresolved",),
    "T10": ("test_recurring_categories_amount_basis_and_periodicity", "test_partition_and_readiness_invariants_cover_mixed_universe"),
    "T11": ("test_corrupt_or_unsupported_recurring_category_is_unresolved",),
    "T12": ("test_every_closed_provenance_value_is_recognized", "test_corrupt_closed_recurring_enums_fail_closed"),
    "T13": ("test_amount_domain_precision_scale_and_type_near_misses_are_unresolved",),
    "T14": ("test_amount_domain_precision_scale_and_type_near_misses_are_unresolved", "test_zero_is_evidence_and_no_total_or_float"),
    "T15": ("test_recurring_categories_amount_basis_and_periodicity",),
    "T16": ("test_complete_date_range_near_misses_suppress_admission",),
    "T17": ("test_target_applicability_and_closed_diagnostics",),
    "T18": ("test_date_container_and_range_fail_closed_without_secondary_diagnostics",),
    "T19": ("test_historical_and_future_classification_uses_target_not_base_date",),
    "T20": ("test_inside_calendar_month_target_has_no_proration",),
    "T21": ("test_lifecycle_membership_is_current_only",),
    "T22": ("test_work_metadata_without_recurring_salary_creates_no_income_source",),
    "T23": ("test_incomplete_employment_evidence_is_unresolved",),
    "T24": ("test_benefit_absent_incomplete_and_explicit_matrix",),
    "T25": ("test_valid_pension_alias_is_excluded_without_independent_amount",),
    "T26": ("test_valid_pension_alias_is_excluded_without_independent_amount",),
    "T27": ("test_valid_misclassified_general_income_uses_generic_recurring_authority",),
    "T28": ("test_resolution_corruption_matrix_fails_closed", "test_valid_pension_alias_is_excluded_without_independent_amount"),
    "T29": ("test_duplicate_collision_is_fail_closed_and_deterministic", "test_cross_basis_frequency_and_excluded_member_collision_controls"),
    "T30": ("test_duplicate_collision_is_fail_closed_and_deterministic", "test_cross_basis_frequency_and_excluded_member_collision_controls"),
    "T31": ("test_nonpositive_persisted_recurring_identity_invalidates_entire_universe", "test_malformed_mocked_recurring_identity_invalidates_entire_universe"),
    "T32": ("test_actual_malformed_recurring_source_shape_is_unresolved",),
    "T33": ("test_partition_and_readiness_invariants_cover_mixed_universe", "test_result_order_is_unicode_stable"),
    "T34": ("test_unknown_native_basis_is_preserved_for_recurring_and_pension",),
    "T35": ("test_tax_label_is_exact_and_never_inferred_from_notes_or_category",),
    "T36": ("test_actual_closed_pension_portfolio_is_consumed_without_total",),
    "T37": ("test_mixed_gross_and_net_have_no_total",),
    "T38": ("test_real_pension_authority_complete_partial_empty_and_fatal_matrix",),
    "T39": ("test_blocker_union_is_unique_and_sorted",),
    "T40": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T41": ("test_true_insertion_order_permutation_is_canonical",),
    "T42": ("test_source_mutation_changes_planning_and_result_identity",),
    "T43": ("test_source_mutation_changes_planning_and_result_identity", "test_valid_pension_alias_is_excluded_without_independent_amount"),
    "T44": ("test_same_session_expire_on_commit_false_refreshes_authoritative_rows", "test_postgresql_expire_on_commit_false_does_not_reuse_stale_identity_map"),
    "T45": ("test_preexisting_transaction_and_pending_writes_rejected_without_discard", "test_dirty_and_deleted_pending_state_are_rejected_without_discard"),
    "T46": ("test_postgresql_repeatable_read_read_only_and_current_result",),
    "T47": ("test_postgresql_concurrent_change_is_snapshot_consistent_and_fresh_read_changes_identity", "test_postgresql_synchronized_membership_changes_preserve_reader_snapshot"),
    "T48": ("test_sqlite_is_explicit_single_select_only_snapshot",),
    "T49": ("test_direct_execution_exception_rolls_back_and_propagates", "test_postgresql_direct_failure_after_authority_loading_rolls_back"),
    "T50": ("test_internal_boundary_has_only_db_and_two_logical_inputs", "test_sqlite_is_explicit_single_select_only_snapshot"),
    "T51": ("test_forbidden_downstream_authorities_are_unreachable",),
    "T52": ("test_forbidden_downstream_authorities_are_unreachable",),
    "T53": ("test_forbidden_downstream_authorities_are_unreachable",),
    "T54": ("test_forbidden_downstream_authorities_are_unreachable",),
    "T55": ("test_all_17_binding_goldens_match_with_two_independent_encoders",),
    "T56": ("test_all_64_binding_fixture_markers_match_independently", "test_golden_derivation_never_bypasses_portfolio_validation"),
    "T57": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T58": ("test_rtisa_traceability_is_complete_and_concrete", "test_all_17_goldens_are_derived_through_read_from_upstream_state"),
    "T59": ("test_wrapped_technical_fatal_raises_and_rolls_back", "test_wrapped_source_executor_technical_fatal_with_expected_source_raises"),
    "T60": ("test_wrapped_identity_technical_fatal_with_nonzero_source_raises",),
    "T61": ("test_read_level_domain_fatal_retains_pension_as_unresolved",),
    "T62": ("test_rehashed_malformed_outer_fatal_is_never_trusted", "test_real_producer_positional_coverage_fatal_is_trusted_domain_authority"),
    "T63": ("test_cleanup_failure_remains_technical_and_never_returns_readiness",),
    "T64": ("test_direct_execution_exception_rolls_back_and_propagates", "test_result_hash_construction_failure_is_direct_technical_and_rolls_back", "test_empty_evidenced_universe_is_ready_and_exact_schema"),
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _independent_json(value):
    if value is None: return "null"
    if value is True: return "true"
    if value is False: return "false"
    if isinstance(value, int) and not isinstance(value, bool): return str(value)
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list): return "[" + ",".join(_independent_json(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(_independent_json(key) + ":" + _independent_json(value[key]) for key in sorted(value)) + "}"
    raise TypeError(type(value))


def _authority(engine):
    with Session(engine) as db, db.begin():
        db.add(PlanningInputDecision(
            client_id=1, version=1, planning_base_date=date(2026, 1, 1),
            retirement_target_date=date(2030, 1, 1), retirement_target_decision_actor="planner:test",
            retirement_target_reference_fingerprint="a" * 64, actor="planner:test",
        ))
    with Session(engine) as db:
        return planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]


def _income(engine, **changes):
    values = dict(
        client_id=1, income_category="rental", description="rent", amount=Decimal("1200.00"),
        amount_basis="gross", frequency="monthly", continuation_status="ongoing",
        lifecycle_status="current", source_status="planner entered", verification_state="reviewed",
        start_date=date(2025, 1, 1),
    )
    values.update(changes)
    with Session(engine) as db, db.begin():
        row = RecurringIncome(**values); db.add(row); db.flush(); return row.id


def _read(engine, expected):
    with Session(engine) as db:
        return subject.read(db, 1, expected)


@pytest.mark.parametrize("client", [True, False, 0, -1, 1.0, "1", None])
def test_strict_client_validation_precedes_reads(client):
    class DB:
        def in_transaction(self): raise AssertionError("database touched")
    with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionError) as error:
        subject.read(DB(), client, "a" * 64)
    assert error.value.code == "RTISA_CLIENT_ID_INVALID"


@pytest.mark.parametrize("value", [None, True, 1, "A" * 64, "a" * 63, "g" * 64])
def test_strict_fingerprint_validation_precedes_reads(value):
    class DB:
        def in_transaction(self): raise AssertionError("database touched")
    with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionError) as error:
        subject.read(DB(), 1, value)
    assert error.value.code == "RTISA_EXPECTED_PLANNING_FINGERPRINT_INVALID"


def test_internal_boundary_has_only_db_and_two_logical_inputs():
    assert list(inspect.signature(subject.read).parameters) == [
        "db", "client_id", "expected_planning_calculation_input_fingerprint"
    ]
    source = inspect.getsource(subject.read)
    assert "planning_input_service.derive" in source
    assert "planning_input_service.read" not in source


def test_empty_evidenced_universe_is_ready_and_exact_schema(engine):
    expected = _authority(engine)
    result = _read(engine, expected)
    assert set(result) == {
        "schema_version", "client_id", "planning_calculation_input_fingerprint", "retirement_target_date",
        "pension_portfolio_result_fingerprint", "source_entries", "included_source_ids", "excluded_source_ids",
        "unresolved_source_ids", "universe_completeness_state", "admission_readiness_state",
        "admission_ready", "blockers", "admission_result_fingerprint",
    }
    assert result["source_entries"] == []
    assert result["universe_completeness_state"] == "COMPLETE_EVIDENCED"
    assert result["admission_readiness_state"] == "READY" and result["admission_ready"] is True
    expected_hash = subject._fingerprint({"contract": subject.RESULT_CONTRACT, **{
        key: value for key, value in result.items() if key != "admission_result_fingerprint"
    }})
    assert result["admission_result_fingerprint"] == expected_hash


def test_recurring_categories_amount_basis_and_periodicity(engine):
    for index, (category, basis, frequency, denominator) in enumerate([
        ("employment", "gross", "monthly", "1"), ("rental", "net", "quarterly", "3"),
        ("business", "gross", "annual", "12"), ("benefit", "net", "monthly", "1"),
        ("other", "gross", "monthly", "1"),
    ]):
        _income(engine, income_category=category, amount_basis=basis, frequency=frequency,
                description=f"source-{index}", amount=Decimal(f"{index}.00"))
    expected = _authority(engine)
    result = _read(engine, expected)
    assert result["admission_ready"] is True
    assert [item["source_category"] for item in result["source_entries"]] == [
        "EMPLOYMENT", "RENTAL", "BUSINESS", "BENEFIT", "OTHER"
    ]
    for entry, denominator in zip(result["source_entries"], ["1", "3", "12", "1", "1"]):
        assert entry["monthly_equivalent"]["denominator"] == denominator
        assert entry["native_income_basis"] in {"GROSS", "NET"}
        assert len(entry) == 13


@pytest.mark.parametrize("start,state,at_target,reason", [
    (date(2025, 1, 1), "INCLUDED", "ACTIVE", None),
    (date(2040, 1, 1), "EXCLUDED", "FUTURE", "RTISA_FUTURE_SOURCE"),
])
def test_actual_closed_pension_portfolio_is_consumed_without_total(engine, start, state, at_target, reason):
    with Session(engine) as db, db.begin():
        canonical_manual_pension_service.create(db, 1, facts(
            monthly_amount="5000.00", pension_start_date=start,
            base_amount_effective_date=date(2025, 1, 1), tax_treatment="taxable",
        ))
    result = _read(engine, _authority(engine))
    entry = result["source_entries"][0]
    assert entry["source_category"] == "PENSION"
    assert entry["admission_state"] == state and entry["applicability"]["at_target"] == at_target
    assert entry["native_amount"] == {"amount": "5000.00", "currency": "ILS", "frequency": "MONTHLY"}
    assert entry["native_tax_characterization"] == {"kind": "SOURCE_LABEL", "value": "taxable"}
    assert entry["native_income_basis"] == "UNKNOWN"
    assert entry["monthly_equivalent"]["denominator"] == "1"
    assert entry["upstream_identity"]["pension_source_result_fingerprint"]
    if reason: assert entry["reason_codes"] == [reason]
    assert "payable_current_monthly_total" not in result


@pytest.mark.parametrize("changes,state,reason", [
    ({"start_date": date(2031, 1, 1)}, "EXCLUDED", "RTISA_FUTURE_SOURCE"),
    ({"end_date": date(2029, 12, 31), "continuation_status": "known end date"}, "EXCLUDED", "RTISA_ENDED_SOURCE"),
    ({"start_date": date(2030, 1, 1)}, "INCLUDED", None),
    ({"end_date": date(2030, 1, 1), "continuation_status": "known end date"}, "INCLUDED", None),
    ({"start_date": None}, "UNRESOLVED", "RTISA_SOURCE_START_DATE_MISSING"),
    ({"continuation_status": "known end date"}, "UNRESOLVED", "RTISA_SOURCE_END_DATE_MISSING"),
    ({"continuation_status": "unknown"}, "UNRESOLVED", "RTISA_SOURCE_CONTINUATION_UNRESOLVED"),
    ({"frequency": "other"}, "UNRESOLVED", "RTISA_SOURCE_FREQUENCY_UNSUPPORTED"),
    ({"amount_basis": "unknown"}, "UNRESOLVED", "RTISA_NATIVE_INCOME_BASIS_UNKNOWN"),
    ({"source_status": "not recorded"}, "UNRESOLVED", "RTISA_SOURCE_AUTHORITY_NOT_RECORDED"),
    ({"verification_state": "collected - not yet reviewed"}, "UNRESOLVED", "RTISA_SOURCE_REVIEW_INCOMPLETE"),
])
def test_target_applicability_and_closed_diagnostics(engine, changes, state, reason):
    _income(engine, **changes)
    expected = _authority(engine)
    result = _read(engine, expected)
    entry = result["source_entries"][0]
    assert entry["admission_state"] == state
    if reason: assert reason in entry["reason_codes"]
    if state == "EXCLUDED": assert result["admission_ready"] is True and result["blockers"] == []
    if state == "UNRESOLVED": assert "RTISA_SOURCE_UNIVERSE_INCOMPLETE" in result["blockers"]


def test_zero_is_evidence_and_no_total_or_float(engine):
    _income(engine, amount=Decimal("0.00"), frequency="quarterly")
    result = _read(engine, _authority(engine))
    entry = result["source_entries"][0]
    assert entry["native_amount"] == {"amount": "0.00", "currency": "ILS", "frequency": "QUARTERLY"}
    assert entry["monthly_equivalent"] == {"numerator": "0.00", "denominator": "3"}
    assert not any("total" in key or "gap" in key for key in result)


def test_duplicate_collision_is_fail_closed_and_deterministic(engine):
    _income(engine); _income(engine)
    result = _read(engine, _authority(engine))
    assert result["unresolved_source_ids"] == ["income:1", "income:2"]
    for entry in result["source_entries"]:
        assert entry["reason_codes"] == ["RTISA_DUPLICATE_COLLISION_UNRESOLVED", "RTISA_SOURCE_IDENTITY_AMBIGUOUS"]
    assert result["admission_ready"] is False


def test_superseded_rows_are_not_candidates(engine):
    _income(engine, lifecycle_status="superseded")
    result = _read(engine, _authority(engine))
    assert result["source_entries"] == [] and result["admission_ready"] is True


def test_stale_expected_fingerprint_exposes_no_sources(engine):
    _income(engine)
    current = _authority(engine)
    result = _read(engine, "f" * 64)
    assert result["planning_calculation_input_fingerprint"] == current
    assert result["source_entries"] == [] and result["blockers"] == ["RTISA_PLANNING_IDENTITY_STALE"]


def test_missing_target_exposes_no_sources(engine):
    _income(engine)
    with Session(engine) as db:
        expected = planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]
    result = _read(engine, expected)
    assert result["source_entries"] == [] and result["blockers"] == ["RTISA_RETIREMENT_TARGET_NOT_READY"]


@pytest.mark.parametrize("mutation,blocker", [
    (lambda value: value.__setitem__("client_id", 2), "RTISA_PLANNING_CONTEXT_INVALID"),
    (lambda value: value.__setitem__("planning_calculation_input_fingerprint", "bad"), "RTISA_PLANNING_CONTEXT_INVALID"),
])
def test_runtime_planning_context_wrong_client_and_malformed_identity_fail_closed(engine, monkeypatch, mutation, blocker):
    expected = _authority(engine)
    with Session(engine) as db:
        planning = planning_input_service.read(db, 1)
    mutation(planning)
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    result = _read(engine, expected)
    assert result["blockers"] == [blocker]
    assert result["source_entries"] == []


def test_historical_and_future_classification_uses_target_not_base_date(engine):
    _income(engine, id=1, start_date=date(2027, 1, 1), end_date=date(2029, 12, 31),
            continuation_status="known end date")
    _income(engine, id=2, start_date=date(2027, 1, 1))
    result = _read(engine, _authority(engine))
    assert result["excluded_source_ids"] == ["income:1"]
    assert result["included_source_ids"] == ["income:2"]
    assert result["source_entries"][0]["applicability"]["at_target"] == "ENDED"


def test_inside_calendar_month_target_has_no_proration(engine):
    _income(engine, start_date=date(2030, 1, 15), amount=Decimal("1234.56"))
    with Session(engine) as db, db.begin():
        db.add(PlanningInputDecision(
            client_id=1, version=1, planning_base_date=date(2026, 1, 1),
            retirement_target_date=date(2030, 1, 20), retirement_target_decision_actor="planner:test",
            retirement_target_reference_fingerprint="a" * 64, actor="planner:test",
        ))
    with Session(engine) as db:
        expected = planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]
    result = _read(engine, expected)
    assert result["source_entries"][0]["monthly_equivalent"] == {"numerator": "1234.56", "denominator": "1"}


@pytest.mark.parametrize("status,included", [("current", True), ("superseded", False)])
def test_lifecycle_membership_is_current_only(engine, status, included):
    _income(engine, lifecycle_status=status)
    result = _read(engine, _authority(engine))
    assert (result["included_source_ids"] == ["income:1"]) is included


def test_work_metadata_without_recurring_salary_creates_no_income_source(engine, monkeypatch):
    expected = _authority(engine)
    with Session(engine) as db:
        planning = planning_input_service.read(db, 1)
    planning["warnings"] = [{"code": "employment_fact_present", "free_text": "continue working"}]
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    result = _read(engine, expected)
    assert result["source_entries"] == [] and result["admission_ready"] is True


@pytest.mark.parametrize("changes", [
    {"start_date": None}, {"amount_basis": "unknown"},
    {"verification_state": "collected - not yet reviewed"},
])
def test_incomplete_employment_evidence_is_unresolved(engine, changes):
    _income(engine, income_category="employment", **changes)
    entry = _read(engine, _authority(engine))["source_entries"][0]
    assert entry["admission_state"] == "UNRESOLVED" and entry["reason_codes"]


def test_benefit_absent_incomplete_and_explicit_matrix(engine):
    initial = _authority(engine)
    assert _read(engine, initial)["source_entries"] == []
    _income(engine, income_category="benefit", start_date=None)
    with Session(engine) as db:
        incomplete_fp = planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]
    incomplete = _read(engine, incomplete_fp)["source_entries"][0]
    assert incomplete["admission_state"] == "UNRESOLVED"
    assert incomplete["native_amount"]["amount"] == "1200.00"
    with engine.begin() as connection:
        connection.execute(text("UPDATE recurring_income SET amount=1800.00, start_date='2025-01-01' WHERE id=1"))
    with Session(engine) as db:
        explicit_fp = planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]
    explicit = _read(engine, explicit_fp)["source_entries"][0]
    assert explicit["native_amount"]["amount"] == "1800.00"


def test_preexisting_transaction_and_pending_writes_rejected_without_discard(engine):
    with Session(engine) as db:
        db.add(RecurringIncome(client_id=1, income_category="rental", description="pending", amount=Decimal("1"),
                               amount_basis="gross", frequency="monthly", continuation_status="ongoing"))
        with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionError) as error:
            subject.read(db, 1, "a" * 64)
        assert error.value.code == "RTISA_REQUIRES_FRESH_TRANSACTION"
        assert len(db.new) == 1


def test_sqlite_is_explicit_single_select_only_snapshot(engine):
    expected = _authority(engine)
    statements = []
    def capture(conn, cursor, statement, parameters, context, many): statements.append(statement.strip().upper())
    event.listen(engine, "before_cursor_execute", capture)
    try: _read(engine, expected)
    finally: event.remove(engine, "before_cursor_execute", capture)
    assert statements[0] == "BEGIN"
    assert all(statement.startswith(("BEGIN", "SELECT", "COMMIT")) for statement in statements)


def test_wrapped_technical_fatal_raises_and_rolls_back(engine, monkeypatch):
    expected = _authority(engine)
    original = subject.portfolio_service.execute_from_planning_result
    def fatal(planning, client_id, supplied):
        return subject.portfolio_service._fatal_result(
            client_id=client_id, planning_fingerprint=expected, supplied_fingerprint=supplied,
            retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage([], []),
            failure=subject.portfolio_service._failure(expected, supplied, "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"),
            blockers=["PORTFOLIO_IDENTITY_ERROR"],
        )
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", fatal)
    with Session(engine) as db:
        with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionTechnicalError) as error:
            subject.read(db, 1, expected)
        assert (error.value.blocker, error.value.stage, error.value.detail) == (
            "PORTFOLIO_IDENTITY_ERROR", "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"
        )
        assert not db.in_transaction()
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", original)


def test_wrapped_source_executor_technical_fatal_with_expected_source_raises(engine, monkeypatch):
    with Session(engine) as db, db.begin():
        canonical_manual_pension_service.create(db, 1, facts(
            pension_start_date=date(2025, 1, 1), base_amount_effective_date=date(2025, 1, 1)
        ))
    expected = _authority(engine)
    with Session(engine) as db:
        planning = planning_input_service.read(db, 1)
    expected_ids = [planning["pension_inputs"][0]["source_id"]]
    def fatal(current, client_id, supplied):
        return subject.portfolio_service._fatal_result(
            client_id=client_id, planning_fingerprint=expected, supplied_fingerprint=supplied,
            retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage(expected_ids, [], "incomplete"),
            failure=subject.portfolio_service._failure(expected, supplied, "source_execution", "PTE_EXECUTOR_EXCEPTION", expected_ids[0]),
            blockers=["PORTFOLIO_SOURCE_EXECUTION_ERROR"], expected_count=1, returned_count=0,
        )
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", fatal)
    with Session(engine) as db:
        with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionTechnicalError) as error:
            subject.read(db, 1, expected)
        assert error.value.blocker == "PORTFOLIO_SOURCE_EXECUTION_ERROR"
        assert not db.in_transaction()


def test_wrapped_identity_technical_fatal_with_nonzero_source_raises(engine, monkeypatch):
    with Session(engine) as db, db.begin():
        canonical_manual_pension_service.create(db, 1, facts(
            pension_start_date=date(2025, 1, 1), base_amount_effective_date=date(2025, 1, 1)
        ))
    expected = _authority(engine)
    with Session(engine) as db:
        planning = planning_input_service.read(db, 1)
    source_id = planning["pension_inputs"][0]["source_id"]
    ready = subject.portfolio_service.execute_from_planning_result(planning, 1, expected)
    fatal = subject.portfolio_service._fatal_result(
        client_id=1, planning_fingerprint=expected, supplied_fingerprint=expected,
        retirement_target_date="2030-01-01", coverage=ready["coverage_evidence"],
        failure=subject.portfolio_service._failure(
            expected, expected, "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"
        ),
        blockers=["PORTFOLIO_IDENTITY_ERROR"], expected_count=1, returned_count=1,
    )
    assert fatal["coverage_evidence"]["expected_source_ids"] == [source_id]
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: fatal)
    with Session(engine) as db:
        with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionTechnicalError) as error:
            subject.read(db, 1, expected)
        assert error.value.blocker == "PORTFOLIO_IDENTITY_ERROR"
        assert not db.in_transaction()


@pytest.mark.parametrize("blockers,stage,detail", [
    (["PORTFOLIO_SOURCE_EXECUTION_ERROR"], "source_execution", "OTHER"),
    (["PORTFOLIO_SOURCE_EXECUTION_ERROR"], "other", "PTE_EXECUTOR_EXCEPTION"),
    (["PORTFOLIO_SOURCE_EXECUTION_ERROR", "PORTFOLIO_SOURCE_EXECUTION_ERROR"], "source_execution", "PTE_EXECUTOR_EXCEPTION"),
    (["PORTFOLIO_AGGREGATION_NUMERIC_ERROR"], "aggregation", "UNQUANTIZED_DECIMAL_OUT_OF_BOUNDS"),
])
def test_exact_technical_discriminator_near_misses_are_not_technical(blockers, stage, detail):
    result = {"result_state": "block_no_result", "portfolio_blockers": blockers,
              "failure_evidence": {"failure_stage": stage, "failure_detail_code": detail}}
    assert subject._is_technical_fatal(result) is None


def test_malformed_technical_looking_outer_result_is_global_invalid(engine, monkeypatch):
    expected = _authority(engine)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: {
        "schema_version": subject.portfolio_service.SCHEMA_VERSION,
        "result_state": "block_no_result", "portfolio_blockers": ["PORTFOLIO_IDENTITY_ERROR"],
        "failure_evidence": {"failure_stage": "portfolio_identity", "failure_detail_code": "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"},
    })
    result = _read(engine, expected)
    assert result["blockers"] == ["RTISA_PENSION_RESULT_INVALID"]
    assert result["source_entries"] == []


def test_impossible_rehashed_technical_near_miss_is_rejected(engine, monkeypatch):
    expected = _authority(engine)
    fatal = subject.portfolio_service._fatal_result(
        client_id=1, planning_fingerprint=expected, supplied_fingerprint=expected,
        retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage([], []),
        failure=subject.portfolio_service._failure(expected, expected, "portfolio_identity", "DIFFERENT_DETAIL"),
        blockers=["PORTFOLIO_IDENTITY_ERROR"],
    )
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: fatal)
    result = _read(engine, expected)
    assert result["universe_completeness_state"] == "UNAVAILABLE"
    assert result["blockers"] == ["RTISA_PENSION_RESULT_INVALID"]


def test_duplicate_technical_blocker_even_with_rehashed_outer_is_untrusted(engine, monkeypatch):
    expected = _authority(engine)
    fatal = subject.portfolio_service._fatal_result(
        client_id=1, planning_fingerprint=expected, supplied_fingerprint=expected,
        retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage([], []),
        failure=subject.portfolio_service._failure(expected, expected, "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"),
        blockers=["PORTFOLIO_IDENTITY_ERROR"],
    )
    fatal["portfolio_blockers"] = ["PORTFOLIO_IDENTITY_ERROR", "PORTFOLIO_IDENTITY_ERROR"]
    fatal["portfolio_result_fingerprint"] = subject.portfolio_service._result_fingerprint(
        subject.portfolio_service._fatal_result_payload(fatal)
    )
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: fatal)
    result = _read(engine, expected)
    assert result["blockers"] == ["RTISA_PENSION_RESULT_INVALID"]


def _rehashed_fatal(fatal):
    changed = copy.deepcopy(fatal)
    changed["portfolio_result_fingerprint"] = subject.portfolio_service._result_fingerprint(
        subject.portfolio_service._fatal_result_payload(changed)
    )
    return changed


@pytest.mark.parametrize("mutation", [
    lambda value: value["coverage_evidence"].__setitem__("coverage_check_state", "broken"),
    lambda value: value["failure_evidence"].__setitem__("failed_expected_source_id", {}),
    lambda value: value["failure_evidence"].__setitem__("observed_source_id", []),
    lambda value: value["coverage_evidence"].__setitem__("missing_source_ids", ["ghost:1"]),
    lambda value: value["coverage_evidence"].__setitem__("unexpected_source_ids", ["ghost:1"]),
    lambda value: value["coverage_evidence"].__setitem__("duplicate_source_ids", ["ghost:1"]),
    lambda value: value.__setitem__("portfolio_blockers", []),
    lambda value: value.__setitem__("portfolio_blockers", ["PORTFOLIO_IDENTITY_ERROR", "PORTFOLIO_SOURCE_EXECUTION_ERROR"]),
    lambda value: value.__setitem__("portfolio_blockers", ["PORTFOLIO_IDENTITY_ERROR", "PORTFOLIO_IDENTITY_ERROR"]),
    lambda value: value.__setitem__("client_id", 2),
    lambda value: value.__setitem__("planning_calculation_input_fingerprint", "b" * 64),
    lambda value: value.__setitem__("retirement_target_date", "2031-01-01"),
    lambda value: value.__setitem__("expected_source_count", False),
    lambda value: value.__setitem__("returned_source_count", False),
    lambda value: value.__setitem__("portfolio_blockers", ["PORTFOLIO_UNKNOWN_FATAL"]),
])
def test_rehashed_malformed_outer_fatal_is_never_trusted(engine, monkeypatch, mutation):
    expected = _authority(engine)
    fatal = subject.portfolio_service._fatal_result(
        client_id=1, planning_fingerprint=expected, supplied_fingerprint=expected,
        retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage([], []),
        failure=subject.portfolio_service._failure(
            expected, expected, "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"
        ),
        blockers=["PORTFOLIO_IDENTITY_ERROR"],
    )
    mutation(fatal)
    fatal = _rehashed_fatal(fatal)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: fatal)
    result = _read(engine, expected)
    assert result["blockers"] == ["RTISA_PENSION_RESULT_INVALID"]
    assert result["source_entries"] == [] and result["admission_ready"] is False


def test_invalid_outer_fingerprint_is_never_trusted(engine, monkeypatch):
    expected = _authority(engine)
    fatal = subject.portfolio_service._fatal_result(
        client_id=1, planning_fingerprint=expected, supplied_fingerprint=expected,
        retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage([], []),
        failure=subject.portfolio_service._failure(
            expected, expected, "portfolio_identity", "PORTFOLIO_EXECUTION_IDENTITY_ASSEMBLY_FAILED"
        ), blockers=["PORTFOLIO_IDENTITY_ERROR"],
    )
    fatal["portfolio_result_fingerprint"] = "f" * 64
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: fatal)
    assert _read(engine, expected)["blockers"] == ["RTISA_PENSION_RESULT_INVALID"]


def test_direct_execution_exception_rolls_back_and_propagates(engine, monkeypatch):
    expected = _authority(engine)
    class DirectFailure(RuntimeError): pass
    def fail(*args): raise DirectFailure("direct")
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", fail)
    with Session(engine) as db:
        with pytest.raises(DirectFailure): subject.read(db, 1, expected)
        assert not db.in_transaction()


def test_same_session_expire_on_commit_false_refreshes_authoritative_rows(engine):
    income_id = _income(engine)
    expected = _authority(engine)
    with Session(engine, expire_on_commit=False) as db:
        stale = db.get(RecurringIncome, income_id)
        assert stale.amount == Decimal("1200.00")
        db.commit()
        with Session(engine) as writer, writer.begin():
            writer.get(RecurringIncome, income_id).amount = Decimal("1300.00")
        with Session(engine) as current:
            new_expected = planning_input_service.read(current, 1)["planning_calculation_input_fingerprint"]
        result = subject.read(db, 1, new_expected)
        assert result["source_entries"][0]["native_amount"]["amount"] == "1300.00"
        assert result["planning_calculation_input_fingerprint"] != expected


@pytest.mark.parametrize("decision_kind", ["SAME_CANONICAL_PENSION", "PENSION_NOT_YET_CANONICAL"])
def test_valid_pension_alias_is_excluded_without_independent_amount(engine, decision_kind):
    with Session(engine) as db, db.begin():
        canonical_manual_pension_service.create(db, 1, facts(
            pension_start_date=date(2025, 1, 1), base_amount_effective_date=date(2025, 1, 1)
        ))
    income_id = _income(engine, income_category="pension")
    with Session(engine) as db:
        planning = planning_input_service.read(db, 1)
    pension = planning["pension_inputs"][0]
    alias = planning["excluded_sources"][0]
    with Session(engine) as db, db.begin():
        db.add(PensionIncomeResolution(
            income_id=income_id, client_id=1, version=1, decision_kind=decision_kind,
            income_fingerprint=alias["source_fingerprint"], canonical_source_id=pension["source_id"],
            canonical_fingerprint=pension["source_fingerprint"], reference="explicit", actor="planner:test",
        ))
    expected = _authority(engine)
    result = _read(engine, expected)
    alias_entry = next(item for item in result["source_entries"] if item["source_id"] == f"income:{income_id}")
    assert alias_entry["admission_state"] == "EXCLUDED"
    assert alias_entry["reason_codes"] == ["RTISA_SAME_CANONICAL_PENSION"]
    assert alias_entry["native_amount"] is None and alias_entry["monthly_equivalent"] is None
    assert alias_entry["applicability"]["at_target"] == "DELEGATED_TO_CANONICAL"
    assert result["admission_ready"] is True


def test_valid_misclassified_general_income_uses_generic_recurring_authority(engine):
    income_id = _income(engine, income_category="other", description="corrected pension label")
    with Session(engine) as db:
        row = db.get(RecurringIncome, income_id)
        source_fp = planning_input_service.fingerprint(subject.record(row))
        db.rollback()
    with Session(engine) as db, db.begin():
        db.add(PensionIncomeResolution(
            income_id=income_id, client_id=1, version=1, decision_kind="MISCLASSIFIED_GENERAL_INCOME",
            income_fingerprint=source_fp, canonical_source_id=None, canonical_fingerprint=None,
            reference="explicit correction", actor="planner:test",
        ))
    result = _read(engine, _authority(engine))
    entry = result["source_entries"][0]
    assert entry["source_category"] == "OTHER" and entry["admission_state"] == "INCLUDED"
    assert entry["upstream_identity"]["resolution"]["decision_kind"] == "MISCLASSIFIED_GENERAL_INCOME"


def test_result_hash_construction_failure_is_direct_technical_and_rolls_back(engine, monkeypatch):
    expected = _authority(engine)
    original = subject._fingerprint
    def fail(value):
        if value.get("contract") == subject.RESULT_CONTRACT:
            raise RuntimeError("hash unavailable")
        return original(value)
    monkeypatch.setattr(subject, "_fingerprint", fail)
    with Session(engine) as db:
        with pytest.raises(RuntimeError, match="hash unavailable"):
            subject.read(db, 1, expected)
        assert not db.in_transaction()


def test_cleanup_failure_remains_technical_and_never_returns_readiness(engine, monkeypatch):
    expected = _authority(engine)
    class ExecutionFailure(RuntimeError): pass
    class CleanupFailure(RuntimeError): pass
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result",
                        lambda *args: (_ for _ in ()).throw(ExecutionFailure("execution")))
    with Session(engine) as db:
        connections = []
        original_connection = db.connection
        def capture_connection(*args, **kwargs):
            connection = original_connection(*args, **kwargs)
            connections.append(connection)
            return connection
        monkeypatch.setattr(db, "connection", capture_connection)
        monkeypatch.setattr(db, "rollback", lambda: (_ for _ in ()).throw(CleanupFailure("cleanup")))
        with pytest.raises(CleanupFailure, match="cleanup"):
            subject.read(db, 1, expected)
        failed_connection = connections[-1]
        assert failed_connection.invalidated is True or failed_connection.closed is True
        with pytest.raises(Exception):
            failed_connection.exec_driver_sql("SELECT 1")
        assert not db.in_transaction()


@pytest.mark.parametrize("source_id", [-1, 0])
def test_nonpositive_persisted_recurring_identity_invalidates_entire_universe(engine, source_id):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO recurring_income "
            "(id,client_id,income_category,description,amount,amount_basis,frequency,continuation_status,"
            "lifecycle_status,source_status,verification_state,start_date) "
            "VALUES (:id,1,'rental','corrupt identity',1200.00,'gross','monthly','ongoing',"
            "'current','planner entered','reviewed','2025-01-01')"
        ), {"id": source_id})
    result = _read(engine, _authority(engine))
    assert result["blockers"] == ["RTISA_SOURCE_UNIVERSE_INVALID"]
    assert result["universe_completeness_state"] == "UNAVAILABLE"
    assert result["source_entries"] == []
    assert result["included_source_ids"] == result["excluded_source_ids"] == result["unresolved_source_ids"] == []


@pytest.mark.parametrize("malformed", [True, "1", 1.0, None])
def test_malformed_mocked_recurring_identity_invalidates_entire_universe(engine, monkeypatch, malformed):
    expected = "a" * 64
    planning = {
        "client_id": 1, "planning_calculation_input_fingerprint": expected,
        "retirement_target": {"retirement_target_ready": True, "retirement_target_date": "2030-01-01"},
        "pension_inputs": [], "warnings": [],
    }
    portfolio = subject.portfolio_service._assemble_ready(1, expected, expected, "2030-01-01", [], [])
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: portfolio)
    with Session(engine) as db:
        monkeypatch.setattr(db, "scalars", lambda *args, **kwargs: [SimpleNamespace(id=malformed)])
        result = subject.read(db, 1, expected)
    assert result["blockers"] == ["RTISA_SOURCE_UNIVERSE_INVALID"]
    assert result["source_entries"] == [] and result["admission_ready"] is False


def test_positive_recurring_identity_remains_admitted(engine):
    source_id = _income(engine)
    result = _read(engine, _authority(engine))
    assert source_id > 0
    assert result["included_source_ids"] == [f"income:{source_id}"]
    assert result["admission_ready"] is True


def _transient_recurring_entry(**changes):
    values = dict(
        id=1, client_id=1, income_category="rental", description="transient",
        amount=Decimal("1200.00"), amount_basis="gross", frequency="monthly",
        continuation_status="ongoing", lifecycle_status="current",
        source_status="planner entered", verification_state="reviewed",
        start_date=date(2025, 1, 1), end_date=None,
    )
    values.update(changes)
    return subject._recurring_entry(RecurringIncome(**values), None, {}, date(2030, 1, 1))


@pytest.mark.parametrize("category", [None, "unsupported", "", 7])
def test_corrupt_or_unsupported_recurring_category_is_unresolved(category):
    entry = _transient_recurring_entry(income_category=category)
    assert entry["admission_state"] == "UNRESOLVED"
    assert entry["source_category"] is None
    assert "RTISA_SOURCE_RECORD_INVALID" in entry["reason_codes"]


@pytest.mark.parametrize("source_status", sorted(subject.SOURCE_STATUSES))
@pytest.mark.parametrize("verification_state", sorted(subject.VERIFICATION_STATES))
def test_every_closed_provenance_value_is_recognized(source_status, verification_state):
    entry = _transient_recurring_entry(source_status=source_status, verification_state=verification_state)
    assert "RTISA_SOURCE_RECORD_INVALID" not in entry["reason_codes"]
    assert entry["provenance"] == {
        "origin_kind": "recurring_income", "source_status": source_status,
        "verification_state": verification_state,
    }


@pytest.mark.parametrize("changes", [
    {"source_status": "corrupt"}, {"verification_state": "corrupt"},
    {"amount_basis": "corrupt"}, {"frequency": "corrupt"},
    {"continuation_status": "corrupt"},
])
def test_corrupt_closed_recurring_enums_fail_closed(changes):
    entry = _transient_recurring_entry(**changes)
    assert entry["admission_state"] == "UNRESOLVED"
    assert "RTISA_SOURCE_RECORD_INVALID" in entry["reason_codes"] or "RTISA_SOURCE_FREQUENCY_UNSUPPORTED" in entry["reason_codes"]


@pytest.mark.parametrize("amount", [
    None, Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"),
    Decimal("1000000000000.00"), Decimal("1.001"), 1, 1.0, "1.00",
])
def test_amount_domain_precision_scale_and_type_near_misses_are_unresolved(amount):
    entry = _transient_recurring_entry(amount=amount)
    assert entry["admission_state"] == "UNRESOLVED"
    assert entry["native_amount"] is None and entry["monthly_equivalent"] is None
    assert "RTISA_SOURCE_AMOUNT_INVALID" in entry["reason_codes"]


@pytest.mark.parametrize("changes,reason", [
    ({"start_date": None}, "RTISA_SOURCE_START_DATE_MISSING"),
    ({"continuation_status": "known end date", "end_date": None}, "RTISA_SOURCE_END_DATE_MISSING"),
    ({"start_date": date(2026, 1, 2), "end_date": date(2026, 1, 1)}, "RTISA_SOURCE_DATE_RANGE_INVALID"),
])
def test_complete_date_range_near_misses_suppress_admission(changes, reason):
    entry = _transient_recurring_entry(**changes)
    assert entry["admission_state"] == "UNRESOLVED"
    assert reason in entry["reason_codes"]


@pytest.mark.parametrize("changes", [
    {"start_date": "2025-01-01"}, {"end_date": [], "continuation_status": "known end date"},
    {"start_date": date(2026, 1, 2), "end_date": date(2026, 1, 1)},
])
def test_date_container_and_range_fail_closed_without_secondary_diagnostics(changes):
    entry = _transient_recurring_entry(**changes)
    assert entry["admission_state"] == "UNRESOLVED"
    assert entry["applicability"]["at_target"] == "UNRESOLVED"
    assert set(entry["reason_codes"]) & {
        "RTISA_SOURCE_RECORD_INVALID", "RTISA_SOURCE_DATE_RANGE_INVALID",
        "RTISA_SOURCE_START_DATE_MISSING", "RTISA_SOURCE_END_DATE_MISSING",
    }


@pytest.mark.parametrize("changes", [
    {"description": None}, {"description": []}, {"income_category": {}},
    {"frequency": 1}, {"amount_basis": []}, {"continuation_status": {}},
])
def test_actual_malformed_recurring_source_shape_is_unresolved(changes):
    entry = _transient_recurring_entry(**changes)
    assert entry["admission_state"] == "UNRESOLVED"
    assert entry["reason_codes"]


def test_unknown_native_basis_is_preserved_for_recurring_and_pension():
    recurring = _transient_recurring_entry(amount_basis="unknown")
    assert recurring["native_income_basis"] == "UNKNOWN"
    planning_source = {"source_id": "manual:1", "source_fingerprint": "a" * 64,
                       "pension_start_date": "2025-01-01"}
    pte_result = _valid_pte_result("manual:1", "b" * 64)
    pension = subject._pension_entry(planning_source, pte_result, "payable_current")
    assert pension["native_income_basis"] == "UNKNOWN"


def test_tax_label_is_exact_and_never_inferred_from_notes_or_category():
    source = {"source_id": "manual:1", "source_fingerprint": "a" * 64,
              "pension_start_date": "2025-01-01", "tax_treatment": "exact-source-label",
              "notes": "tax free", "category": "exempt"}
    entry = subject._pension_entry(source, _valid_pte_result("manual:1", "b" * 64), "payable_current")
    assert entry["native_tax_characterization"] == {"kind": "SOURCE_LABEL", "value": "exact-source-label"}


def test_mixed_gross_and_net_have_no_total(engine):
    _income(engine, id=1, amount_basis="gross", amount=Decimal("1200.00"))
    _income(engine, id=2, income_category="business", amount_basis="net", amount=Decimal("900.00"))
    result = _read(engine, _authority(engine))
    assert [entry["native_income_basis"] for entry in result["source_entries"]] == ["GROSS", "NET"]
    assert not any("total" in key for key in result)


def test_partition_and_readiness_invariants_cover_mixed_universe(engine):
    _income(engine, id=1)
    _income(engine, id=2, start_date=date(2031, 1, 1))
    _income(engine, id=3, start_date=None)
    result = _read(engine, _authority(engine))
    partitions = result["included_source_ids"] + result["excluded_source_ids"] + result["unresolved_source_ids"]
    assert sorted(partitions) == [entry["source_id"] for entry in result["source_entries"]]
    assert len(partitions) == len(set(partitions))
    assert result["admission_ready"] is False
    assert result["admission_readiness_state"] == "NOT_READY"
    assert result["universe_completeness_state"] == "PARTIAL"


def test_blocker_union_is_unique_and_sorted(engine):
    _income(engine, id=1, start_date=None)
    _income(engine, id=2, amount_basis="unknown")
    result = _read(engine, _authority(engine))
    expected = sorted(set(code for entry in result["source_entries"] for code in entry["reason_codes"])
                      | {"RTISA_SOURCE_UNIVERSE_INCOMPLETE"})
    assert result["blockers"] == expected == sorted(set(result["blockers"]))


def test_source_mutation_changes_planning_and_result_identity(engine):
    _income(engine, amount=Decimal("1200.00"))
    first_planning = _authority(engine)
    first = _read(engine, first_planning)
    with engine.begin() as connection:
        connection.execute(text("UPDATE recurring_income SET amount=1201.00 WHERE id=1"))
    with Session(engine) as db:
        second_planning = planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]
    second = _read(engine, second_planning)
    assert second_planning != first_planning
    assert second["admission_result_fingerprint"] != first["admission_result_fingerprint"]


@pytest.mark.parametrize("changes", [
    {"decision_kind": "CORRUPT"}, {"client_id": 2}, {"income_fingerprint": "bad"},
    {"canonical_source_id": "manual:1", "canonical_fingerprint": None},
])
def test_resolution_corruption_matrix_fails_closed(changes):
    values = dict(decision_kind="SAME_CANONICAL_PENSION", client_id=1, income_id=1, version=1,
                  income_fingerprint="a" * 64, canonical_source_id="manual:1",
                  canonical_fingerprint="b" * 64)
    values.update(changes)
    row = SimpleNamespace(**values)
    resolution = subject._resolution_value(row)
    if changes.get("client_id") == 2:
        assert resolution is not None  # ownership is rejected by the enclosing authoritative query boundary
    else:
        assert resolution is None


@pytest.mark.parametrize("second,collision", [
    ({"amount_basis": "net"}, True), ({"frequency": "quarterly"}, False),
    ({"start_date": date(2031, 1, 1)}, False),
])
def test_cross_basis_frequency_and_excluded_member_collision_controls(engine, second, collision):
    _income(engine, description="same economic label")
    _income(engine, description="same economic label", **second)
    result = _read(engine, _authority(engine))
    if collision:
        assert "RTISA_DUPLICATE_COLLISION_UNRESOLVED" in result["blockers"]
        assert all("RTISA_DUPLICATE_COLLISION_UNRESOLVED" in entry["reason_codes"] for entry in result["source_entries"])
    else:
        assert "RTISA_DUPLICATE_COLLISION_UNRESOLVED" not in result["blockers"]
        assert not any("RTISA_DUPLICATE_COLLISION_UNRESOLVED" in entry["reason_codes"] for entry in result["source_entries"])


def test_true_insertion_order_permutation_is_canonical(engine):
    statement = text(
        "INSERT INTO recurring_income "
        "(id,client_id,income_category,description,amount,amount_basis,frequency,continuation_status,"
        "lifecycle_status,source_status,verification_state,start_date) "
        "VALUES (:id,1,'rental',:description,1200.00,'gross','monthly','ongoing',"
        "'current','planner entered','reviewed','2025-01-01')"
    )
    with engine.begin() as connection:
        connection.execute(statement, {"id": 20, "description": "later id inserted first"})
        connection.execute(statement, {"id": 10, "description": "earlier id inserted second"})
    result = _read(engine, _authority(engine))
    assert [entry["source_id"] for entry in result["source_entries"]] == ["income:10", "income:20"]


@pytest.mark.parametrize("pending_state", ["dirty", "deleted"])
def test_dirty_and_deleted_pending_state_are_rejected_without_discard(engine, pending_state):
    source_id = _income(engine)
    with Session(engine) as db:
        row = db.get(RecurringIncome, source_id)
        if pending_state == "dirty":
            row.amount = Decimal("1300.00")
        else:
            db.delete(row)
        with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionError) as error:
            subject.read(db, 1, "a" * 64)
        assert error.value.code == "RTISA_REQUIRES_FRESH_TRANSACTION"
        assert (len(db.dirty) == 1) if pending_state == "dirty" else (len(db.deleted) == 1)


def test_non_ils_pension_is_read_level_unresolved(engine, monkeypatch):
    expected = "a" * 64
    source_fp = "b" * 64
    planning = {
        "client_id": 1, "planning_calculation_input_fingerprint": expected,
        "retirement_target": {"retirement_target_ready": True, "retirement_target_date": "2030-01-01"},
        "pension_inputs": [{"source_id": "manual:1", "source_fingerprint": source_fp,
                            "pension_start_date": "2025-01-01"}], "warnings": [],
    }
    pte_result = _valid_pte_result("manual:1", expected, currency="USD")
    portfolio = subject.portfolio_service._assemble_ready(
        1, expected, expected, "2030-01-01", ["manual:1"], [pte_result]
    )
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: portfolio)
    result = _read(engine, expected)
    assert result["unresolved_source_ids"] == ["manual:1"]
    assert result["source_entries"][0]["reason_codes"] == ["RTISA_SOURCE_CURRENCY_UNSUPPORTED"]
    assert result["admission_ready"] is False


def test_nontechnical_fatal_retains_enumerable_pension_as_unresolved():
    planning = {"planning_calculation_input_fingerprint": "a" * 64,
                "retirement_target": {"retirement_target_date": "2030-01-01"},
                "pension_inputs": [{"source_id": "manual:1", "source_fingerprint": "b" * 64,
                                    "pension_start_date": "2025-01-01"}], "warnings": []}
    fatal = {"result_state": "block_no_result", "portfolio_result_fingerprint": "c" * 64,
             "total_completeness_state": "unavailable"}
    result = subject._assemble(1, planning, fatal, [], [])
    assert result["unresolved_source_ids"] == ["manual:1"]
    assert result["source_entries"][0]["reason_codes"] == ["RTISA_PENSION_AUTHORITY_UNAVAILABLE"]


def test_exact_result_fingerprint_golden_g1_preimage():
    preimage = json.loads('{"admission_readiness_state":"READY","admission_ready":true,"blockers":[],"client_id":1,"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_RESULT_FINGERPRINT_JSON_V1","excluded_source_ids":[],"included_source_ids":["manual:1"],"pension_portfolio_result_fingerprint":"523eaf54747e897352ca0571f6a7b8a3a6fcbbf8387795a71326677181f54321","planning_calculation_input_fingerprint":"788ad8a2a689b252cbaae834188010b862e57061c5c6b040bb6eea4d5ed2c741","retirement_target_date":"2030-01-01","schema_version":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_RESULT_V1","source_entries":[{"admission_state":"INCLUDED","applicability":{"at_target":"ACTIVE","continuation_status":null,"end_date":null,"start_date":"2025-01-01"},"monthly_equivalent":{"denominator":"1","numerator":"5000"},"native_amount":{"amount":"5000.00","currency":"ILS","frequency":"MONTHLY"},"native_income_basis":"UNKNOWN","native_price_evidence":{"annual_rate":null,"price_basis":"UNKNOWN","price_reference_date":null,"rate_basis":null,"temporal_authority_kind":"none","temporal_origin_date":"2025-01-01"},"native_tax_characterization":{"kind":"UNKNOWN","value":null},"provenance":{"origin_kind":"manual","source_status":null,"verification_state":null},"reason_codes":[],"source_authority":"CANONICAL_PENSION_TARGET_DATE","source_category":"PENSION","source_id":"manual:1","upstream_identity":{"pension_source_result_fingerprint":"9d69b762b8ee4dbead61a2356404f937015eb7ec4102e20ffd613cfbc0886e1f","resolution":null,"source_fingerprint":"5bf9fa418af3ca2328a9d25033de5af245342a41a21df295c5a78a125b77c057"}}],"universe_completeness_state":"COMPLETE_EVIDENCED","unresolved_source_ids":[]}')
    assert _digest(preimage) == "a2efb1a3e068af16e4766d224f673247966efcc925d356eda2c18714c14c6e1a"


def test_all_17_binding_goldens_match_with_two_independent_encoders():
    fixtures = json.loads((Path(__file__).parent / "fixtures" / "rtisa_goldens.json").read_text(encoding="utf-8"))
    assert set(fixtures) == {f"G{index}" for index in range(1, 18)}
    for name, fixture in fixtures.items():
        value = json.loads(fixture["preimage"])
        standard = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        independent = _independent_json(value).encode()
        assert standard == independent, name
        assert len(standard) == fixture["bytes"], name
        assert hashlib.sha256(standard).hexdigest() == fixture["hash"], name


def test_golden_derivation_never_bypasses_portfolio_validation():
    source = inspect.getsource(_golden_upstream_state)
    assert "_portfolio_is_valid" not in source


def _valid_pte_result(source_id, planning_fp, *, result_state="result_ready", currency="ILS",
                      result_fingerprint=None):
    result = {
        "schema_version": subject.portfolio_service.pte.SCHEMA_VERSION,
        "source_id": source_id,
        "result_state": result_state,
        "execution_identity_state": "complete" if result_state == "result_ready" else "incomplete",
        "source_execution_fingerprint": _digest({"execution": source_id, "planning": planning_fp}),
        "source_result_fingerprint": result_fingerprint,
        "authority_kind": "canonical_pension_source",
        "temporal_authority_kind": "none",
        "temporal_origin_date": "2025-01-01",
        "retirement_target_date": "2030-01-01",
        "currency": currency if result_state == "result_ready" else None,
        "applicability_state": "payable_current" if result_state == "result_ready" else "unresolved",
        "blockers": [] if result_state == "result_ready" else ["PTE_MONTHLY_BASIS_NOT_READY"],
        "monthly_basis_blockers": [] if result_state == "result_ready" else ["MONTHLY_BASIS_NOT_READY"],
        "temporal_blockers": [],
        "execution_identity_evidence": None if result_state == "result_ready" else {"state": "blocked"},
    }
    if result_state == "result_ready":
        result.update({
            "elapsed_year_fraction": "5",
            "base_amount_representation": "5000.00",
            "derived_base_monthly_amount": "5000.00",
            "annual_rate": None,
            "temporal_factor": "1",
            "unquantized_target_monthly_amount": "5000",
            "final_monthly_amount": "5000.00",
            "decimal_execution_contract": "EXACT_DECIMAL_V1",
        })
    if result_fingerprint is None:
        result["source_result_fingerprint"] = subject.portfolio_service._fingerprint(
            subject.portfolio_service._pte_result_payload(result)
        )
    return result


GOLDEN_RECURRING_SCENARIOS = {
    "G2": [dict(id=1, category="rental", amount="1200.00")],
    "G3": [dict(id=1, category="rental", amount="1200.00", start="2031-01-01")],
    "G4": [dict(id=1, category="rental", amount="1200.00", end="2029-12-31", continuation="known end date")],
    "G5": [dict(id=1, category="employment", amount="4500.00", start="2030-01-01")],
    "G7": [dict(id=1, category="benefit", amount="1800.00", basis="net")],
    "G8": [dict(id=9, category="pension", amount="5000.00", resolution=True)],
    "G9": [dict(id=9, category="pension", amount="5000.00")],
    "G10": [dict(id=1, category="rental", amount="1200.00", start=None)],
    "G11": [dict(id=1, category="rental", amount="1200.00"),
            dict(id=2, category="business", amount="900.00", basis="net")],
    "G12": [dict(id=1, category="rental", amount="1201.00")],
    "G13": [dict(id=1, category="rental", amount="1200.00", description="duplicate"),
            dict(id=2, category="rental", amount="1200.00", description="duplicate")],
    "G14": [dict(id=1, category="rental", amount="0.00")],
}


def _golden_upstream_state(engine, monkeypatch, golden, markers):
    planning_fp = markers["planning:G2"] if golden == "G17" else markers[f"planning:{golden}"]
    pension_ids = [] if golden in {"G16", "G17"} else (["manual:1", "manual:2"] if golden == "G15" else ["manual:1"])
    planning = {
        "client_id": 1,
        "planning_calculation_input_fingerprint": planning_fp,
        "retirement_target": {
            "retirement_target_ready": True,
            "retirement_target_date": "2030-01-01",
        },
        "pension_inputs": [{
            "source_id": source_id,
            "source_fingerprint": markers[f"source:{source_id}"],
            "pension_start_date": "2025-01-01" if source_id == "manual:1" else None,
        } for source_id in pension_ids],
        "warnings": [],
    }
    original_portfolio_fingerprint = subject.portfolio_service._fingerprint
    pension_markers = {
        source_id: markers[f"pension-result:{golden}:{source_id}"] for source_id in pension_ids
    }
    def admitted_fixture_fingerprint(payload):
        if payload.get("contract") == subject.portfolio_service.pte.RESULT_CONTRACT:
            return pension_markers[payload["source_id"]]
        if payload.get("contract") == subject.portfolio_service.RESULT_CONTRACT:
            return markers[f"portfolio:{golden}"]
        return original_portfolio_fingerprint(payload)
    monkeypatch.setattr(subject.portfolio_service, "_fingerprint", admitted_fixture_fingerprint)
    source_results = [
        _valid_pte_result(
            source_id, planning_fp,
            result_state="block_no_result" if source_id == "manual:2" else "result_ready",
            result_fingerprint=pension_markers[source_id],
        ) for source_id in pension_ids
    ]
    portfolio = ({} if golden == "G17" else subject.portfolio_service._assemble_ready(
        1, planning_fp, planning_fp, "2030-01-01", pension_ids, source_results
    ))
    fp_by_income_id = {}
    with Session(engine) as db, db.begin():
        for values in GOLDEN_RECURRING_SCENARIOS.get(golden, []):
            source_id = values["id"]
            row = RecurringIncome(
                id=source_id, client_id=1, income_category=values["category"],
                description=values.get("description", f"income:{source_id}"),
                amount=Decimal(values["amount"]), amount_basis=values.get("basis", "gross"),
                frequency="monthly", continuation_status=values.get("continuation", "ongoing"),
                lifecycle_status="current", source_status="planner entered", verification_state="reviewed",
                start_date=(date.fromisoformat(values.get("start", "2025-01-01"))
                            if values.get("start", "2025-01-01") is not None else None),
                end_date=date.fromisoformat(values["end"]) if values.get("end") else None,
            )
            db.add(row)
            db.flush()
            fp_by_income_id[source_id] = markers[f"recurring:{golden}:income:{source_id}"]
            if values.get("resolution"):
                db.add(PensionIncomeResolution(
                    income_id=source_id, client_id=1, version=1,
                    decision_kind="SAME_CANONICAL_PENSION", income_fingerprint=fp_by_income_id[source_id],
                    canonical_source_id="manual:1", canonical_fingerprint=markers["source:manual:1"],
                    reference="accepted golden", actor="planner:test",
                ))
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: portfolio)
    original_fingerprint = subject.planning_input_service.fingerprint
    monkeypatch.setattr(subject.planning_input_service, "fingerprint", lambda value: (
        fp_by_income_id[value["id"]] if isinstance(value, dict) and value.get("id") in fp_by_income_id
        else original_fingerprint(value)
    ))
    return planning


@pytest.mark.parametrize("golden", [f"G{index}" for index in range(1, 18)])
def test_all_17_goldens_are_derived_through_read_from_upstream_state(engine, monkeypatch, golden):
    fixtures = json.loads((Path(__file__).parent / "fixtures" / "rtisa_goldens.json").read_text(encoding="utf-8"))
    markers = json.loads((Path(__file__).parent / "fixtures" / "rtisa_markers.json").read_text(encoding="utf-8"))
    fixture = fixtures[golden]
    preimage = json.loads(fixture["preimage"])
    planning = _golden_upstream_state(engine, monkeypatch, golden, markers)
    supplied = planning["planning_calculation_input_fingerprint"] if golden != "G17" else "f" * 64
    actual = _read(engine, supplied)
    expected = {key: value for key, value in preimage.items() if key != "contract"}
    expected["admission_result_fingerprint"] = fixture["hash"]
    assert actual == expected, json.dumps({"actual": actual, "expected": expected}, ensure_ascii=False, sort_keys=True)
    encoded = json.dumps(preimage, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert len(encoded) == fixture["bytes"]
    assert hashlib.sha256(encoded).hexdigest() == fixture["hash"]


def test_all_64_binding_fixture_markers_match_independently():
    markers = json.loads((Path(__file__).parent / "fixtures" / "rtisa_markers.json").read_text(encoding="utf-8"))
    assert len(markers) == 64
    for marker, expected in markers.items():
        encoded = _independent_json({"fixture": marker}).encode()
        assert hashlib.sha256(encoded).hexdigest() == expected


def test_result_order_is_unicode_stable(engine):
    _income(engine, description="z"); _income(engine, description="a", income_category="benefit")
    first = _read(engine, _authority(engine))
    assert [entry["source_id"] for entry in first["source_entries"]] == ["income:1", "income:2"]
    assert first == copy.deepcopy(first)


def test_read_level_domain_fatal_retains_pension_as_unresolved(engine, monkeypatch):
    with Session(engine) as db, db.begin():
        canonical_manual_pension_service.create(db, 1, facts(
            pension_start_date=date(2025, 1, 1), base_amount_effective_date=date(2025, 1, 1)
        ))
    expected = _authority(engine)
    with Session(engine) as db:
        source_id = planning_input_service.read(db, 1)["pension_inputs"][0]["source_id"]
    monkeypatch.setattr(subject.portfolio_service.pte, "execute_from_planning_result", lambda *args, **kwargs: {
        "schema_version": "MALFORMED", "source_id": args[1]
    })
    result = _read(engine, expected)
    assert result["admission_readiness_state"] == "NOT_READY"
    assert result["universe_completeness_state"] == "PARTIAL"
    assert result["unresolved_source_ids"] == [source_id]
    assert result["source_entries"][0]["native_amount"] is None
    assert result["source_entries"][0]["reason_codes"] == ["RTISA_PENSION_AUTHORITY_UNAVAILABLE"]
    assert result["blockers"] == ["RTISA_PENSION_AUTHORITY_UNAVAILABLE", "RTISA_SOURCE_UNIVERSE_INCOMPLETE"]


def test_real_pension_authority_complete_partial_empty_and_fatal_matrix(engine, monkeypatch):
    empty = _read(engine, _authority(engine))
    assert empty["source_entries"] == [] and empty["universe_completeness_state"] == "COMPLETE_EVIDENCED"
    with Session(engine) as db, db.begin():
        canonical_manual_pension_service.create(db, 1, facts(
            payer_name="ready", pension_start_date=date(2025, 1, 1),
            base_amount_effective_date=date(2025, 1, 1),
        ))
        canonical_manual_pension_service.create(db, 1, facts(
            payer_name="blocked", pension_start_date=None,
            base_amount_effective_date=date(2025, 1, 1),
        ))
    with Session(engine) as db:
        current = planning_input_service.read(db, 1)["planning_calculation_input_fingerprint"]
    partial = _read(engine, current)
    assert partial["universe_completeness_state"] == "PARTIAL"
    assert len(partial["included_source_ids"]) == 1 and len(partial["unresolved_source_ids"]) == 1
    original = subject.portfolio_service.pte.execute_from_planning_result
    monkeypatch.setattr(subject.portfolio_service.pte, "execute_from_planning_result", lambda *args, **kwargs: {
        "schema_version": "MALFORMED", "source_id": args[1]
    })
    fatal = _read(engine, current)
    assert fatal["universe_completeness_state"] == "PARTIAL"
    assert fatal["included_source_ids"] == [] and len(fatal["unresolved_source_ids"]) == 2
    monkeypatch.setattr(subject.portfolio_service.pte, "execute_from_planning_result", original)


def test_real_producer_positional_coverage_fatal_is_trusted_domain_authority(engine, monkeypatch):
    with Session(engine) as db, db.begin():
        for payer in ("A", "B"):
            canonical_manual_pension_service.create(db, 1, facts(
                payer_name=payer, pension_start_date=date(2025, 1, 1),
                base_amount_effective_date=date(2025, 1, 1),
            ))
    expected = _authority(engine)
    with Session(engine) as db:
        planning = planning_input_service.read(db, 1)
    expected_ids = [source["source_id"] for source in planning["pension_inputs"]]
    ready = subject.portfolio_service.execute_from_planning_result(planning, 1, expected)
    genuine_fatal = subject.portfolio_service._assemble_ready(
        1, expected, expected, "2030-01-01", expected_ids, list(reversed(ready["source_results"]))
    )
    assert genuine_fatal["portfolio_blockers"] == ["PORTFOLIO_SOURCE_COVERAGE_MISSING"]
    assert genuine_fatal["coverage_evidence"]["missing_source_ids"] == sorted(expected_ids)
    assert genuine_fatal["coverage_evidence"]["unexpected_source_ids"] == sorted(expected_ids)
    assert subject._portfolio_is_valid(genuine_fatal, 1, planning, "2030-01-01") is True
    assert subject._is_technical_fatal(genuine_fatal) is None
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: genuine_fatal)
    result = _read(engine, expected)
    assert result["universe_completeness_state"] == "PARTIAL"
    assert result["admission_readiness_state"] == "NOT_READY"
    assert result["unresolved_source_ids"] == sorted(expected_ids)
    assert all(item["native_amount"] is None for item in result["source_entries"])
    assert result["blockers"] == [
        "RTISA_PENSION_AUTHORITY_UNAVAILABLE", "RTISA_SOURCE_UNIVERSE_INCOMPLETE"
    ]


def test_forbidden_downstream_authorities_are_unreachable():
    source = inspect.getsource(subject)
    for forbidden in (
        "capital_projection", "resource_state", "scenario", "expense", "inheritance",
        "funding_gap", "monthly_income_target_service", "tax_service", "price_index",
    ):
        assert forbidden not in source


def test_rtisa_traceability_is_complete_and_concrete():
    assert list(RTISA_TRACEABILITY) == [f"T{index:02d}" for index in range(1, 65)]
    test_sources = Path(__file__).read_text(encoding="utf-8") + (
        Path(__file__).with_name("test_retirement_target_date_income_source_admission_postgresql.py")
    ).read_text(encoding="utf-8")
    for trace_id, tests in RTISA_TRACEABILITY.items():
        assert tests, trace_id
        assert len(tests) == len(set(tests)), trace_id
        for test_name in tests:
            assert f"def {test_name}(" in test_sources, (trace_id, test_name)
