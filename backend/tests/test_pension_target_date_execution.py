from decimal import (
    Clamped, DivisionByZero, FloatOperation, Inexact, InvalidOperation,
    Overflow, ROUND_HALF_EVEN, Rounded, Subnormal, Underflow,
)
from fractions import Fraction
import ast
import inspect
from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.services import pension_target_date_execution_service as subject
from app.models.planning_input_decision import PlanningInputDecision
from app.schemas.canonical_manual_pension_source import ManualPensionInput
from app.schemas.planning_input import BaseDateDecision
from app.services import canonical_manual_pension_service, planning_input_service
from test_recovery_pension_products import engine


HASHES = {str(i): str(i) * 64 for i in range(1, 6)}


def inputs(**overrides):
    values = dict(
        source_id="manual:7",
        source_current_state="current",
        monthly_basis={
            "authority_kind": "entered_monthly_amount",
            "base_amount_representation": {"representation_kind": "exact_money", "amount": "1000"},
            "base_amount_semantic_fingerprint": HASHES["1"],
            "base_amount_source_fingerprint": HASHES["2"],
            "basis_authority_ready": True,
            "basis_blockers": [],
        },
        temporal_authority={
            "temporal_authority_kind": "fixed_manual",
            "temporal_origin_date": "2025-01-01",
            "annual_rate": "0.12",
            "temporal_semantic_fingerprint": HASHES["4"],
            "temporal_source_fingerprint": HASHES["5"],
            "temporal_authority_ready": True,
            "temporal_blockers": [],
        },
        retirement_target={"retirement_target_date": "2026-01-01", "retirement_target_ready": True},
        current_planning_calculation_input_fingerprint=HASHES["3"],
        supplied_planning_calculation_input_fingerprint=HASHES["3"],
        supplied_monthly_basis_semantic_fingerprint=HASHES["1"],
        supplied_monthly_basis_source_fingerprint=HASHES["2"],
        supplied_temporal_semantic_fingerprint=HASHES["4"],
        supplied_temporal_source_fingerprint=HASHES["5"],
        pension_start_date="2025-01-01",
        currency="ILS",
    )
    values.update(overrides)
    return values


def execute(**overrides):
    return subject.execute_source(**inputs(**overrides))


@pytest.mark.parametrize(("origin", "target", "expected"), [
    ("2025-06-15", "2025-06-15", Fraction(0, 1)),
    ("2025-01-01", "2025-01-02", Fraction(1, 365)),
    ("2025-01-01", "2026-01-01", Fraction(1, 1)),
    ("2024-01-01", "2025-01-01", Fraction(1, 1)),
    ("2023-12-31", "2024-01-02", Fraction(731, 133590)),
    ("2024-02-28", "2024-03-01", Fraction(1, 183)),
    ("2024-01-01", "2024-07-01", Fraction(91, 183)),
    ("2023-07-01", "2025-07-01", Fraction(2, 1)),
])
def test_all_golden_date_vectors(origin, target, expected):
    assert subject.elapsed_year_fraction(origin, target) == expected


def configured(*, amount="1000", rate="0.12", origin="2025-01-01", target="2026-01-01",
               temporal_kind="fixed_manual", authority="entered_monthly_amount", numerator=None, denominator=None):
    if numerator is None:
        representation = {"representation_kind": "exact_money", "amount": amount}
    else:
        representation = {"representation_kind": "exact_ratio", "numerator": numerator, "denominator": denominator}
    monthly = {**inputs()["monthly_basis"], "authority_kind": authority,
               "base_amount_representation": representation}
    temporal = {**inputs()["temporal_authority"], "temporal_authority_kind": temporal_kind,
                "temporal_origin_date": origin, "annual_rate": None if temporal_kind == "none" else rate}
    return execute(monthly_basis=monthly, temporal_authority=temporal,
                   retirement_target={"retirement_target_date": target, "retirement_target_ready": True})


@pytest.mark.parametrize(("kwargs", "expected"), [
    ({"temporal_kind": "none"}, "1000.00"),
    ({"origin": "2025-01-01", "target": "2025-01-01"}, "1000.00"),
    ({"origin": "2025-01-01", "target": "2025-07-02"}, "1058.14"),
    ({"origin": "2024-01-01", "target": "2024-07-01"}, "1057.97"),
    ({"origin": "2025-01-01", "target": "2026-01-01"}, "1120.00"),
    ({"origin": "2024-01-01", "target": "2025-01-01"}, "1120.00"),
    ({"rate": "0.05", "origin": "2023-07-01", "target": "2025-07-01"}, "1102.50"),
    ({"temporal_kind": "none", "authority": "manual_balance_ratio", "numerator": "120000", "denominator": "120"}, "1000.00"),
    ({"temporal_kind": "none", "authority": "persisted_conversion_ratio", "numerator": "240000", "denominator": "200"}, "1200.00"),
    ({"temporal_kind": "none", "amount": "100.005"}, "100.01"),
    ({"temporal_kind": "none", "amount": "100.0049"}, "100.00"),
])
def test_all_golden_money_vectors(kwargs, expected):
    assert configured(**kwargs)["final_monthly_amount"] == expected


def test_published_temporal_factor_strings_are_exact():
    assert configured(origin="2025-01-01", target="2025-07-02")["temporal_factor"] == (
        "1.058136241552040376784439174828953678395708436714408793277507571576879286570095558382343050040636768"
    )
    assert configured(origin="2024-01-01", target="2024-07-01")["temporal_factor"] == (
        "1.057972881692298926536925506672394874902380386082494437610059326882656252657173540816189622125214713"
    )


def test_ready_golden_fingerprints_a_and_b_and_schema():
    result = execute()
    assert result["source_execution_fingerprint"] == "ac70d16be714dc3efab8da86b0b2cc1e6d7896eb1317a3fb57a767601e7234f8"
    assert result["source_result_fingerprint"] == "d7a5be935c7672f3ced74f0ff783dbb5402b9a8b890123d41bb975a7dff30b92"
    assert result["result_state"] == "result_ready"
    assert result["elapsed_year_fraction"] == {"numerator": "1", "denominator": "1"}
    assert result["final_monthly_amount"] == "1120.00"
    assert set(result) == {
        "schema_version", "source_id", "result_state", "execution_identity_state",
        "source_execution_fingerprint", "source_result_fingerprint", "authority_kind",
        "temporal_authority_kind", "temporal_origin_date", "retirement_target_date", "currency",
        "applicability_state", "blockers", "monthly_basis_blockers", "temporal_blockers",
        "execution_identity_evidence", "elapsed_year_fraction", "base_amount_representation",
        "derived_base_monthly_amount", "annual_rate", "temporal_factor",
        "unquantized_target_monthly_amount", "final_monthly_amount", "decimal_execution_contract",
    }


@pytest.mark.parametrize(("overrides", "execution_hash", "result_hash", "blocker"), [
    ({"temporal_authority": {**inputs()["temporal_authority"], "temporal_origin_date": "2027-01-01"}},
     "7ea28d663c49c40c622b58ff261495273e1a64a7fda79b497fae3d8cebe8fc6b",
     "c766698c78eb5d80ead8a218174a3311abdbfe36b195aa16d2050b62d0cb9193", "RETIREMENT_TARGET_BEFORE_TEMPORAL_ORIGIN"),
    ({"retirement_target": {"retirement_target_date": None, "retirement_target_ready": False}, "pension_start_date": None},
     None, "eb70866855f6f7ee7813cb1153970c3df4cef33d845dc0d8a2076c6d9e2fef16", "RETIREMENT_TARGET_NOT_READY"),
    ({"source_current_state": "unresolved"}, None,
     "cf0e26943ee130657294b45463ea4ca4faa740f8ba12a65219238bf34bbf6f82", "SOURCE_NOT_CURRENT"),
    ({"monthly_basis": {**inputs()["monthly_basis"], "base_amount_semantic_fingerprint": None}}, None,
     "4c2f182784fb8944bcba8ce57e0ef3c1502c667f513aeb8cf4ab33b4683176cd", "MONTHLY_BASIS_NOT_READY"),
    ({"current_planning_calculation_input_fingerprint": None}, None,
     "debf68d3a32331c331dc185daae8d341b95e9a526568aaa48c9f56d95a9b94b8", "PLANNING_INPUT_IDENTITY_STALE"),
])
def test_golden_fingerprint_vectors_c_through_h(overrides, execution_hash, result_hash, blocker):
    result = execute(**overrides)
    assert result["source_execution_fingerprint"] == execution_hash
    assert result["source_result_fingerprint"] == result_hash
    assert result["blockers"] == [blocker]
    assert result["result_state"] == "block_no_result"
    assert not subject.NUMERICAL_FIELDS.intersection(result)


@pytest.mark.parametrize(("start", "expected"), [
    ("2025-01-01", "payable_current"),
    ("2027-01-01", "future_start"),
    (None, "unresolved"),
])
def test_applicability_is_independent_of_amount_execution(start, expected):
    result = execute(pension_start_date=start)
    assert result["result_state"] == "result_ready"
    assert result["applicability_state"] == expected


def test_missing_and_stale_identities_accumulate_in_unicode_order():
    monthly = {**inputs()["monthly_basis"], "base_amount_semantic_fingerprint": None}
    temporal = {**inputs()["temporal_authority"], "temporal_source_fingerprint": "9" * 64}
    result = execute(
        source_current_state="not_current",
        monthly_basis=monthly,
        temporal_authority=temporal,
        supplied_planning_calculation_input_fingerprint=None,
        supplied_temporal_source_fingerprint=HASHES["5"],
        retirement_target={"retirement_target_date": None, "retirement_target_ready": False},
    )
    assert result["blockers"] == sorted(set(result["blockers"]))
    assert result["blockers"] == [
        "MONTHLY_BASIS_NOT_READY", "PLANNING_INPUT_IDENTITY_STALE",
        "RETIREMENT_TARGET_NOT_READY", "SOURCE_NOT_CURRENT", "TEMPORAL_AUTHORITY_IDENTITY_STALE",
    ]
    assert result["execution_identity_state"] == "incomplete"
    assert result["source_execution_fingerprint"] is None


@pytest.mark.parametrize(("field", "blocker"), [
    ("supplied_monthly_basis_semantic_fingerprint", "MONTHLY_BASIS_NOT_READY"),
    ("supplied_monthly_basis_source_fingerprint", "MONTHLY_BASIS_NOT_READY"),
    ("supplied_temporal_semantic_fingerprint", "TEMPORAL_AUTHORITY_NOT_READY"),
    ("supplied_temporal_source_fingerprint", "TEMPORAL_AUTHORITY_NOT_READY"),
    ("supplied_planning_calculation_input_fingerprint", "PLANNING_INPUT_IDENTITY_STALE"),
])
def test_missing_supplied_identity_maps_to_not_ready_or_stale(field, blocker):
    result = execute(**{field: None})
    assert blocker in result["blockers"]


def test_missing_temporal_origin_is_distinct_and_blocked_shape_is_exact():
    temporal = {**inputs()["temporal_authority"], "temporal_origin_date": None}
    result = execute(temporal_authority=temporal)
    assert result["blockers"] == ["TEMPORAL_ORIGIN_MISSING"]
    assert result["result_state"] == "block_no_result"
    assert not subject.NUMERICAL_FIELDS.intersection(result)


def test_stale_monthly_and_temporal_identities_are_separate():
    result = execute(supplied_monthly_basis_source_fingerprint="a" * 64,
                     supplied_temporal_semantic_fingerprint="b" * 64)
    assert result["blockers"] == ["MONTHLY_BASIS_IDENTITY_STALE", "TEMPORAL_AUTHORITY_IDENTITY_STALE"]


def test_numeric_error_is_exclusive_and_preserves_complete_identity():
    monthly = {**inputs()["monthly_basis"], "authority_kind": "manual_balance_ratio",
               "base_amount_representation": {"representation_kind": "exact_ratio", "numerator": "1000", "denominator": "0"}}
    result = execute(monthly_basis=monthly)
    assert result["blockers"] == ["NUMERIC_EXECUTION_ERROR"]
    assert result["execution_identity_state"] == "complete"
    assert result["source_execution_fingerprint"] is not None
    assert not subject.NUMERICAL_FIELDS.intersection(result)


def test_decimal_context_is_exact_fresh_and_has_binding_traps():
    first, second = subject.decimal_context(), subject.decimal_context()
    assert first is not second
    assert (first.prec, first.rounding, first.Emin, first.Emax, first.clamp) == (100, ROUND_HALF_EVEN, -999999, 999999, 0)
    for signal in (InvalidOperation, DivisionByZero, Overflow, FloatOperation):
        assert first.traps[signal]
    for signal in (Inexact, Rounded, Underflow, Subnormal, Clamped):
        assert not first.traps[signal]
    assert not any(first.flags.values())


def test_binary_float_authority_is_rejected_without_float_execution():
    monthly = {**inputs()["monthly_basis"],
               "base_amount_representation": {"representation_kind": "exact_money", "amount": 1000.0}}
    result = execute(monthly_basis=monthly)
    assert result["blockers"] == ["MONTHLY_BASIS_NOT_READY"]
    temporal = {**inputs()["temporal_authority"], "annual_rate": 0.12}
    result = execute(temporal_authority=temporal)
    assert result["blockers"] == ["TEMPORAL_AUTHORITY_NOT_READY"]
    assert result["execution_identity_evidence"]["annual_rate"] is None


def test_none_still_computes_elapsed_fraction_and_has_null_rate():
    result = configured(temporal_kind="none", target="2025-07-02")
    assert result["elapsed_year_fraction"] == {"numerator": "182", "denominator": "365"}
    assert result["annual_rate"] is None
    assert result["temporal_factor"] == "1"


@pytest.mark.parametrize(("numerator", "expected"), [
    ("1000049", "100.00"),
    ("100005", "100.01"),
])
def test_ratio_authority_rounds_immediately_below_and_at_half_cent(numerator, expected):
    denominator = "10000" if numerator == "1000049" else "1000"
    result = configured(
        temporal_kind="none",
        authority="manual_balance_ratio",
        numerator=numerator,
        denominator=denominator,
    )
    assert result["derived_base_monthly_amount"] in {"100.0049", "100.005"}
    assert result["final_monthly_amount"] == expected


@pytest.mark.parametrize(("amount", "expected_unquantized", "expected"), [
    ("90.91363", "100.004993", "100.00"),
    ("90.91364", "100.005004", "100.01"),
])
def test_fixed_temporal_compounding_rounds_on_both_sides_of_half_cent(
    amount, expected_unquantized, expected
):
    result = configured(amount=amount, rate="0.1", origin="2025-01-01", target="2026-01-01")
    assert result["temporal_factor"] == "1.1"
    assert result["unquantized_target_monthly_amount"] == expected_unquantized
    assert result["final_monthly_amount"] == expected


def test_unavailable_current_temporal_fingerprint_is_not_misclassified_as_stale():
    temporal = {**inputs()["temporal_authority"], "temporal_semantic_fingerprint": None}
    result = execute(temporal_authority=temporal)
    assert result["result_state"] == "block_no_result"
    assert result["execution_identity_state"] == "incomplete"
    assert result["source_execution_fingerprint"] is None
    assert result["blockers"] == ["TEMPORAL_AUTHORITY_NOT_READY"]
    assert "TEMPORAL_AUTHORITY_IDENTITY_STALE" not in result["blockers"]
    assert not subject.NUMERICAL_FIELDS.intersection(result)


def test_unequal_available_planning_fingerprints_are_stale_and_incomplete():
    result = execute(supplied_planning_calculation_input_fingerprint="a" * 64)
    assert result["blockers"] == ["PLANNING_INPUT_IDENTITY_STALE"]
    assert result["result_state"] == "block_no_result"
    assert result["execution_identity_state"] == "incomplete"
    assert result["source_execution_fingerprint"] is None


def test_null_currency_is_legitimate_for_complete_ready_identity():
    result = execute(currency=None)
    assert result["currency"] is None
    assert result["execution_identity_evidence"]["currency"] is None
    assert result["execution_identity_state"] == "complete"
    assert result["source_execution_fingerprint"] is not None
    assert result["result_state"] == "result_ready"
    assert result["blockers"] == []


def test_stale_supplied_identities_never_replace_current_top_level_provenance():
    current_monthly = {**inputs()["monthly_basis"], "authority_kind": "manual_balance_ratio",
                       "base_amount_representation": {"representation_kind": "exact_ratio",
                                                       "numerator": "120000", "denominator": "120"}}
    current_temporal = {**inputs()["temporal_authority"], "temporal_authority_kind": "none",
                        "annual_rate": None, "temporal_origin_date": "2025-02-03"}
    current_target = {"retirement_target_date": "2028-04-05", "retirement_target_ready": True}
    result = execute(
        monthly_basis=current_monthly,
        temporal_authority=current_temporal,
        retirement_target=current_target,
        pension_start_date="2029-06-07",
        currency="ILS",
        supplied_monthly_basis_semantic_fingerprint="a" * 64,
        supplied_temporal_source_fingerprint="b" * 64,
        supplied_planning_calculation_input_fingerprint="c" * 64,
    )
    assert result["result_state"] == "block_no_result"
    assert result["authority_kind"] == "manual_balance_ratio"
    assert result["temporal_authority_kind"] == "none"
    assert result["temporal_origin_date"] == "2025-02-03"
    assert result["retirement_target_date"] == "2028-04-05"
    assert result["currency"] == "ILS"
    assert result["execution_identity_evidence"]["current_monthly_basis_semantic_fingerprint"] == HASHES["1"]
    assert result["execution_identity_evidence"]["current_temporal_source_fingerprint"] == HASHES["5"]
    assert result["execution_identity_evidence"]["current_planning_calculation_input_fingerprint"] == HASHES["3"]


def test_incomplete_blocked_result_has_exact_returned_field_set():
    result = execute(current_planning_calculation_input_fingerprint=None)
    expected = {
        "schema_version", "source_id", "result_state", "execution_identity_state",
        "source_execution_fingerprint", "source_result_fingerprint", "authority_kind",
        "temporal_authority_kind", "temporal_origin_date", "retirement_target_date",
        "currency", "applicability_state", "blockers", "monthly_basis_blockers",
        "temporal_blockers", "execution_identity_evidence",
    }
    assert set(result) == expected
    assert result["result_state"] == "block_no_result"
    assert result["blockers"]
    assert result["monthly_basis_blockers"] == []
    assert result["temporal_blockers"] == []
    assert result["source_execution_fingerprint"] is None
    assert result["source_result_fingerprint"]
    assert result["execution_identity_evidence"]
    assert not subject.NUMERICAL_FIELDS.intersection(result)


def test_planning_adapter_uses_unique_current_recomputed_source_and_current_authorities():
    source = {
        "source_id": "manual:7", "pension_start_date": None,
        "monthly_amount_basis": inputs()["monthly_basis"],
        "temporal_authority": inputs()["temporal_authority"],
    }
    planning = {
        "pension_inputs": [source],
        "retirement_target": inputs()["retirement_target"],
        "planning_calculation_input_fingerprint": HASHES["3"],
    }
    supplied = {key: value for key, value in inputs().items() if key.startswith("supplied_")}
    result = subject.execute_from_planning_result(planning, "manual:7", **supplied)
    assert result["result_state"] == "result_ready"
    assert result["applicability_state"] == "unresolved"
    assert result["execution_identity_evidence"]["source_current_state"] == "current"


def test_planning_adapter_marks_absent_or_duplicate_source_not_current():
    planning = {"pension_inputs": [], "retirement_target": inputs()["retirement_target"],
                "planning_calculation_input_fingerprint": HASHES["3"]}
    supplied = {key: value for key, value in inputs().items() if key.startswith("supplied_")}
    absent = subject.execute_from_planning_result(planning, "manual:7", **supplied)
    assert "SOURCE_NOT_CURRENT" in absent["blockers"]
    planning["pension_inputs"] = [{"source_id": "manual:7"}, {"source_id": "manual:7"}]
    duplicate = subject.execute_from_planning_result(planning, "manual:7", **supplied)
    assert duplicate["execution_identity_evidence"]["source_current_state"] == "not_current"


def test_current_database_snapshot_integration_executes_without_persistence(engine):
    with Session(engine) as db, db.begin():
        planning_input_service.set_base_date(
            db, 1, BaseDateDecision(expected_version=0, planning_base_date=date(2030, 1, 1)))
        created = canonical_manual_pension_service.create(db, 1, ManualPensionInput(
            input_mode="entered", payer_name="משלם", monthly_amount="100.00",
            pension_start_date=None, base_amount_effective_date=date(2030, 1, 1),
            tax_treatment="taxable", temporal_authority={"authority_kind": "none"}))
        decision = db.get(PlanningInputDecision, 1)
        decision.retirement_target_date = date(2031, 1, 1)
    with Session(engine) as db:
        current = planning_input_service.read(db, 1)
    source = next(item for item in current["pension_inputs"]
                  if item["source_id"] == "manual:" + created["manual_pension_source_id"])
    supplied = {
        "supplied_planning_calculation_input_fingerprint": current["planning_calculation_input_fingerprint"],
        "supplied_monthly_basis_semantic_fingerprint": source["monthly_amount_basis"]["base_amount_semantic_fingerprint"],
        "supplied_monthly_basis_source_fingerprint": source["monthly_amount_basis"]["base_amount_source_fingerprint"],
        "supplied_temporal_semantic_fingerprint": source["temporal_authority"]["temporal_semantic_fingerprint"],
        "supplied_temporal_source_fingerprint": source["temporal_authority"]["temporal_source_fingerprint"],
    }
    result = subject.execute_from_planning_result(current, source["source_id"], **supplied)
    assert result["result_state"] == "result_ready"
    assert result["final_monthly_amount"] == "100.00"
    assert result["applicability_state"] == "unresolved"
    with Session(engine) as db:
        assert db.query(PlanningInputDecision).count() == 1


def test_service_has_no_cpi_persistence_schema_or_float_math_dependency():
    source = inspect.getsource(subject).lower()
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Import) and any(name.name == "math" for name in node.names) for node in ast.walk(tree))
    assert not any(isinstance(node, ast.ImportFrom) and node.module == "math" for node in ast.walk(tree))
    assert not any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) for node in ast.walk(tree))
    assert "sqlalchemy" not in source
    assert "requests" not in source and "http" not in source
    assert "alembic" not in source
