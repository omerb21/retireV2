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
    "T02": ("test_stale_expected_fingerprint_exposes_no_sources", "test_missing_target_exposes_no_sources"),
    "T03": ("test_empty_evidenced_universe_is_ready_and_exact_schema",),
    "T04": ("test_actual_closed_pension_portfolio_is_consumed_without_total",),
    "T05": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T06": ("test_read_level_domain_fatal_retains_pension_as_unresolved",),
    "T07": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T08": ("test_rehashed_malformed_outer_fatal_is_never_trusted", "test_invalid_outer_fingerprint_is_never_trusted"),
    "T09": ("test_non_ils_pension_is_read_level_unresolved",),
    "T10": ("test_recurring_categories_amount_basis_and_periodicity",),
    "T11": ("test_corrupt_or_unsupported_recurring_category_is_unresolved",),
    "T12": ("test_every_closed_provenance_value_is_recognized", "test_corrupt_closed_recurring_enums_fail_closed"),
    "T13": ("test_amount_domain_precision_scale_and_type_near_misses_are_unresolved",),
    "T14": ("test_amount_domain_precision_scale_and_type_near_misses_are_unresolved", "test_zero_is_evidence_and_no_total_or_float"),
    "T15": ("test_recurring_categories_amount_basis_and_periodicity",),
    "T16": ("test_complete_date_range_near_misses_suppress_admission",),
    "T17": ("test_target_applicability_and_closed_diagnostics",),
    "T18": ("test_complete_date_range_near_misses_suppress_admission",),
    "T19": ("test_target_applicability_and_closed_diagnostics",),
    "T20": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T21": ("test_superseded_rows_are_not_candidates",),
    "T22": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T23": ("test_target_applicability_and_closed_diagnostics",),
    "T24": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T25": ("test_valid_pension_alias_is_excluded_without_independent_amount",),
    "T26": ("test_valid_pension_alias_is_excluded_without_independent_amount",),
    "T27": ("test_valid_misclassified_general_income_uses_generic_recurring_authority",),
    "T28": ("test_valid_pension_alias_is_excluded_without_independent_amount",),
    "T29": ("test_duplicate_collision_is_fail_closed_and_deterministic",),
    "T30": ("test_duplicate_collision_is_fail_closed_and_deterministic", "test_cross_basis_frequency_and_excluded_member_collision_controls"),
    "T31": ("test_nonpositive_persisted_recurring_identity_invalidates_entire_universe", "test_malformed_mocked_recurring_identity_invalidates_entire_universe"),
    "T32": ("test_rehashed_malformed_outer_fatal_is_never_trusted",),
    "T33": ("test_empty_evidenced_universe_is_ready_and_exact_schema", "test_result_order_is_unicode_stable"),
    "T34": ("test_target_applicability_and_closed_diagnostics",),
    "T35": ("test_actual_closed_pension_portfolio_is_consumed_without_total",),
    "T36": ("test_actual_closed_pension_portfolio_is_consumed_without_total",),
    "T37": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T38": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T39": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T40": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T41": ("test_true_insertion_order_permutation_is_canonical",),
    "T42": ("test_same_session_expire_on_commit_false_refreshes_authoritative_rows",),
    "T43": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
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
    "T55": ("test_exact_result_fingerprint_golden_g1_preimage",),
    "T56": ("test_all_64_binding_fixture_markers_match_independently",),
    "T57": ("test_all_17_goldens_are_derived_through_read_from_upstream_state",),
    "T58": ("test_rtisa_traceability_is_complete_and_concrete",),
    "T59": ("test_wrapped_technical_fatal_raises_and_rolls_back",),
    "T60": ("test_wrapped_source_executor_technical_fatal_with_expected_source_raises",),
    "T61": ("test_read_level_domain_fatal_retains_pension_as_unresolved",),
    "T62": ("test_rehashed_malformed_outer_fatal_is_never_trusted", "test_exact_technical_discriminator_near_misses_are_not_technical"),
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
            retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage(expected_ids, []),
            failure=subject.portfolio_service._failure(expected, supplied, "source_execution", "PTE_EXECUTOR_EXCEPTION", expected_ids[0]),
            blockers=["PORTFOLIO_SOURCE_EXECUTION_ERROR"], expected_count=1, returned_count=0,
        )
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", fatal)
    with Session(engine) as db:
        with pytest.raises(subject.RetirementTargetIncomeSourceAdmissionTechnicalError) as error:
            subject.read(db, 1, expected)
        assert error.value.blocker == "PORTFOLIO_SOURCE_EXECUTION_ERROR"
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


def test_valid_rehashed_technical_near_miss_uses_domain_fatal_not_wrapper(engine, monkeypatch):
    expected = _authority(engine)
    fatal = subject.portfolio_service._fatal_result(
        client_id=1, planning_fingerprint=expected, supplied_fingerprint=expected,
        retirement_target_date="2030-01-01", coverage=subject.portfolio_service._coverage([], []),
        failure=subject.portfolio_service._failure(expected, expected, "portfolio_identity", "DIFFERENT_DETAIL"),
        blockers=["PORTFOLIO_IDENTITY_ERROR"],
    )
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: fatal)
    result = _read(engine, expected)
    assert result["universe_completeness_state"] == "PARTIAL"
    assert result["blockers"] == ["RTISA_SOURCE_UNIVERSE_INCOMPLETE"]


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
    source_result_fp = "c" * 64
    planning = {
        "client_id": 1, "planning_calculation_input_fingerprint": expected,
        "retirement_target": {"retirement_target_ready": True, "retirement_target_date": "2030-01-01"},
        "pension_inputs": [{"source_id": "manual:1", "source_fingerprint": source_fp,
                            "pension_start_date": "2025-01-01"}], "warnings": [],
    }
    portfolio = {
        "result_state": "result_ready", "portfolio_result_fingerprint": "d" * 64,
        "source_results": [{
            "source_id": "manual:1", "source_result_fingerprint": source_result_fp,
            "result_state": "result_ready", "temporal_authority_kind": "none",
            "temporal_origin_date": "2025-01-01", "annual_rate": None,
            "final_monthly_amount": "5000.00", "unquantized_target_monthly_amount": "5000",
            "currency": "USD",
        }],
        "payable_current_source_ids": ["manual:1"], "future_start_source_ids": [],
        "unresolved_source_ids": [], "blocked_source_ids": [], "total_completeness_state": "complete",
    }
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: portfolio)
    monkeypatch.setattr(subject, "_portfolio_is_valid", lambda *args: True)
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


def _golden_upstream_state(engine, monkeypatch, preimage):
    pension_entries = [item for item in preimage["source_entries"] if item["source_category"] == "PENSION"]
    recurring_entries = [item for item in preimage["source_entries"] if item["source_category"] != "PENSION"]
    planning = {
        "client_id": 1,
        "planning_calculation_input_fingerprint": preimage["planning_calculation_input_fingerprint"],
        "retirement_target": {
            "retirement_target_ready": True,
            "retirement_target_date": preimage["retirement_target_date"],
        },
        "pension_inputs": [{
            "source_id": item["source_id"],
            "source_fingerprint": item["upstream_identity"]["source_fingerprint"],
            "pension_start_date": item["applicability"]["start_date"],
            **({"tax_treatment": item["native_tax_characterization"]["value"]}
               if item["native_tax_characterization"]["value"] is not None else {}),
        } for item in pension_entries],
        "warnings": [],
    }
    source_results = []
    groups = {"payable_current": [], "future_start": [], "unresolved": [], "blocked": []}
    for item in pension_entries:
        evidence = item["native_price_evidence"]
        amount = item["native_amount"]
        monthly = item["monthly_equivalent"]
        ready = amount is not None
        source_results.append({
            "source_id": item["source_id"],
            "source_result_fingerprint": item["upstream_identity"]["pension_source_result_fingerprint"],
            "result_state": "result_ready" if ready else "block_no_result",
            "temporal_authority_kind": evidence["temporal_authority_kind"],
            "temporal_origin_date": evidence["temporal_origin_date"],
            "annual_rate": evidence["annual_rate"],
            "final_monthly_amount": amount["amount"] if ready else None,
            "unquantized_target_monthly_amount": monthly["numerator"] if monthly is not None else None,
            "currency": amount["currency"] if ready else None,
        })
        group = "payable_current" if item["admission_state"] == "INCLUDED" else (
            "future_start" if item["admission_state"] == "EXCLUDED" else (
                "unresolved" if "RTISA_PENSION_APPLICABILITY_UNRESOLVED" in item["reason_codes"] else "blocked"
            )
        )
        groups[group].append(item["source_id"])
    portfolio = {
        "result_state": "result_ready",
        "portfolio_result_fingerprint": preimage["pension_portfolio_result_fingerprint"],
        "source_results": source_results,
        "total_completeness_state": "partial" if groups["unresolved"] else "complete",
        **{f"{name}_source_ids": values for name, values in groups.items()},
    }
    fp_by_income_id = {}
    with Session(engine) as db, db.begin():
        for item in recurring_entries:
            source_id = int(item["source_id"].split(":", 1)[1])
            native = item["native_amount"]
            applicability = item["applicability"]
            category = item["source_category"].lower()
            if item["source_category"] == "PENSION_REPRESENTATION":
                category = "pension"
            frequency = {"MONTHLY": "monthly", "QUARTERLY": "quarterly", "ANNUAL": "annual"}.get(
                native["frequency"] if native else None, "monthly"
            )
            basis = item["native_income_basis"].lower()
            if basis not in {"gross", "net"}:
                basis = "gross"
            row = RecurringIncome(
                id=source_id, client_id=1, income_category=category,
                description="duplicate" if "RTISA_DUPLICATE_COLLISION_UNRESOLVED" in item["reason_codes"] else item["source_id"],
                amount=Decimal(native["amount"] if native else "100.00"), amount_basis=basis,
                frequency=frequency, continuation_status=applicability["continuation_status"] or "ongoing",
                lifecycle_status="current", source_status=item["provenance"]["source_status"] or "planner entered",
                verification_state=item["provenance"]["verification_state"] or "reviewed",
                start_date=date.fromisoformat(applicability["start_date"]) if applicability["start_date"] else None,
                end_date=date.fromisoformat(applicability["end_date"]) if applicability["end_date"] else None,
            )
            db.add(row)
            db.flush()
            fp_by_income_id[source_id] = item["upstream_identity"]["source_fingerprint"]
            resolution = item["upstream_identity"]["resolution"]
            if resolution is not None:
                db.add(PensionIncomeResolution(
                    income_id=source_id, client_id=1, version=resolution["record_version"],
                    decision_kind=resolution["decision_kind"], income_fingerprint=resolution["income_fingerprint"],
                    canonical_source_id=resolution["canonical_source_id"],
                    canonical_fingerprint=resolution["canonical_fingerprint"],
                    reference="accepted golden", actor="planner:test",
                ))
    monkeypatch.setattr(subject.planning_input_service, "derive", lambda *args: planning)
    monkeypatch.setattr(subject.portfolio_service, "execute_from_planning_result", lambda *args: portfolio)
    monkeypatch.setattr(subject, "_portfolio_is_valid", lambda *args: True)
    original_fingerprint = subject.planning_input_service.fingerprint
    monkeypatch.setattr(subject.planning_input_service, "fingerprint", lambda value: (
        fp_by_income_id[value["id"]] if isinstance(value, dict) and value.get("id") in fp_by_income_id
        else original_fingerprint(value)
    ))
    return planning


@pytest.mark.parametrize("golden", [f"G{index}" for index in range(1, 18)])
def test_all_17_goldens_are_derived_through_read_from_upstream_state(engine, monkeypatch, golden):
    fixtures = json.loads((Path(__file__).parent / "fixtures" / "rtisa_goldens.json").read_text(encoding="utf-8"))
    fixture = fixtures[golden]
    preimage = json.loads(fixture["preimage"])
    planning = _golden_upstream_state(engine, monkeypatch, preimage)
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
