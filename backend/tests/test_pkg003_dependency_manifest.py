from __future__ import annotations

import copy
import inspect
import os
import subprocess
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
import app.services.fixation_dependency_service as dependency_service
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import load_all_models
from app.db.session import get_db
from app.main import app
from app.models.fixation_dependency_manifest import (
    FixationDependencyManifest as FixationDependencyManifestModel,
)
from app.models.fixation_run import FixationRun
from app.models.grant import Grant
from app.schemas.cbs_indexation import (
    CbsIndexationFailure,
    CbsIndexationFailureEvidence,
    CbsIndexationRequestEvidence,
    CbsIndexationResponseEvidence,
    CbsIndexationSuccess,
)
from app.schemas.fixation_admissibility import AdmissibleFixationInput
from app.schemas.fixation_dependency_manifest import FixationDependencyManifest
from app.services.fixation_admission_service import parse_and_admit_fixation_payload
from app.services.fixation_dependency_service import (
    _build_dependency_manifest,
    build_fixation_dependency_manifest,
    canonical_json,
    compare_fixation_dependency_manifests,
    dependency_fingerprint,
)
from app.services.fixation_service import (
    _dependency_manifest_model,
    _new_dependency_manifest_id,
)
from tests.pkg004d_test_support import resolver_payload, seed_eligibility_revision


load_all_models()
NOW = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def _payload(*, client_id: int = 1, mode: str = "asserted_indexed_amount") -> dict:
    return {
        "calculation_id": "pkg-003",
        "calculation_version": "pkg-003-v1",
        "eligibility_date": "2026-01-01",
        "eligibility_year": 2026,
        "upstream_context": {
            "profile_id": "m07-1",
            "client_id": client_id,
            "state": "warning_reviewed",
            "warnings": [{"code": "W-2", "message": "second"}, {"code": "W-1", "message": "first"}],
            "review_reason": "reviewed warning context",
            "reviewed_by": "planner-1",
            "review_timestamp": "2026-01-01T07:00:00Z",
            "qualification_trace_id": "trace-1",
        },
        "parameter_set": {
            "parameter_set_id": "params-2026",
            "client_id": client_id,
            "tax_year": 2026,
            "effective_from": "2026-01-01",
            "effective_to": "2026-12-31",
            "values": {
                "monthly_cap": 1000.0,
                "exemption_percentage": 0.5,
                "capital_multiplier": 180.0,
                "grant_impact_multiplier": 1.35,
            },
            "source_basis": "accepted fixture",
            "status": "accepted",
            "accepted_for_use": True,
            "accepted_by": "planner-1",
            "decision_timestamp": "2026-01-01T07:00:00Z",
        },
        "grants_collection_state": "items_recorded",
        "grants": [
            {
                "grant_id": "grant-1",
                "client_id": client_id,
                "item_type": "severance_grant",
                "nominal_amount": 1000.0,
                "indexed_amount": 1200.0,
                "grant_date": "2020-02-03",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-31",
                "source_basis": "planner assertion",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "planner-1",
                "decision_timestamp": "2026-01-01T07:01:00Z",
                "indexation_mode": mode,
            }
        ],
        "future_grant_reservation": {
            "amount": 50.0,
            "source_basis": "planner reserve",
            "status": "accepted",
            "accepted_for_use": True,
            "actor": "planner-1",
            "decision_timestamp": "2026-01-01T07:02:00Z",
        },
        "actual_capitalizations_collection_state": "items_recorded",
        "actual_capitalizations": [
            {
                "capitalization_id": "cap-1",
                "item_type": "actual_capitalization",
                "amount": 25.0,
                "capitalization_date": "2025-01-01",
                "recorded_meaning": "accepted historical capitalization",
                "source_basis": "planner assertion",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "planner-1",
                "decision_timestamp": "2026-01-01T07:03:00Z",
            }
        ],
        "idf": None,
    }


def _success() -> CbsIndexationSuccess:
    request = CbsIndexationRequestEvidence(
        amount=Decimal("1000"),
        resolved_base_date=date(2020, 2, 3),
        base_date_source="grant_date",
        target_date=date(2026, 1, 1),
        calculation_timestamp=NOW,
    )
    return CbsIndexationSuccess(
        request=request,
        response=CbsIndexationResponseEvidence(
            raw_to_value=Decimal("1234.5678"),
            from_index_period="01-2020",
            to_index_period="12-2025",
            from_index_value=Decimal("99.1"),
            to_index_value=Decimal("110.2"),
            base_year="Average 2024=100",
            chaining_coefficient=Decimal("1.0012"),
            change_percentage=Decimal("11.2"),
            missing_optional_fields=[],
            calculation_timestamp=NOW,
            response_status=200,
        ),
    )


def _failure() -> CbsIndexationFailure:
    success = _success()
    return CbsIndexationFailure(
        request=success.request,
        failure=CbsIndexationFailureEvidence(
            outcome_status="calculation_failed",
            failure_category="timeout",
            timeout=True,
            calculation_timestamp=NOW,
            safe_technical_message="CBS calculator request timed out",
        ),
    )


def _admitted(payload: dict, *, calculator=None) -> AdmissibleFixationInput:
    context = AdmissibleFixationInput(**payload)
    for grant in context.grants:
        if grant.inclusion_decision == "exclude":
            continue
        if grant.indexation_mode == "asserted_indexed_amount":
            selected = (
                grant.accepted_value
                if grant.conflict_indicator
                else grant.indexed_amount
            )
            grant.asserted_indexed_amount = selected
            grant.selected_calculation_amount = selected
            grant.resolved_base_date = grant.grant_date
            grant.base_date_source = "grant_date"
            grant.target_date = context.eligibility_date
            grant.indexation_calculation_status = "asserted"
            continue
        assert calculator is not None
        outcome = calculator()
        assert isinstance(outcome, CbsIndexationSuccess)
        grant.indexation_mode = "cbs_system_calculated"
        grant.asserted_indexed_amount = grant.indexed_amount
        grant.system_calculated_amount = round(
            float(outcome.response.raw_to_value), 2
        )
        grant.selected_calculation_amount = grant.system_calculated_amount
        grant.resolved_base_date = outcome.request.resolved_base_date
        grant.base_date_source = outcome.request.base_date_source
        grant.target_date = outcome.request.target_date
        grant.cpi_code = outcome.request.cpi_code
        grant.cbs_request_evidence = outcome.request
        grant.cbs_response_evidence = outcome.response
        grant.indexation_calculation_status = "calculated"
    return context


def _manifest(
    context: AdmissibleFixationInput,
    *,
    run_id: int = 1,
    input_contract_version: str | None = None,
    result_contract_version: str | None = None,
):
    return build_fixation_dependency_manifest(
        run_id=run_id,
        run_identity=f"run-{run_id}",
        client_id=context.upstream_context.client_id,
        calculation_version=context.calculation_version,
        input_contract_version=input_contract_version or context.calculation_version,
        result_contract_version=result_contract_version or context.calculation_version,
        context=context,
    )


def _persisted_manifest(
    context: AdmissibleFixationInput,
    *,
    run_id: int = 1,
    input_contract_version: str | None = None,
    result_contract_version: str | None = None,
):
    return _build_dependency_manifest(
        run_id=run_id,
        run_identity=f"run-{run_id}",
        client_id=context.upstream_context.client_id,
        calculation_version=context.calculation_version,
        input_contract_version=input_contract_version or context.calculation_version,
        result_contract_version=result_contract_version or context.calculation_version,
        context=context,
    )


def _comparison_request(
    current_context: dict | None,
    *,
    input_contract_version: str | None = "pkg-003-v1",
    result_contract_version: str | None = "pkg-003-v1",
) -> dict:
    return {
        "current_context": current_context,
        "current_input_contract_version": input_contract_version,
        "current_result_contract_version": result_contract_version,
    }


def _upgrade_database(db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_canonicalization_is_stable_and_transport_noise_is_ignored() -> None:
    instant = datetime(2026, 1, 1, 10, 0, tzinfo=timezone(timedelta(hours=2)))
    utc_instant = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
    first = {
        "amount": Decimal("100.00"),
        "instant": instant,
        "warnings": [{"code": "B"}, {"code": "A"}],
        "optional": None,
    }
    second = {
        "optional": None,
        "warnings": [{"code": "A"}, {"code": "B"}],
        "instant": utc_instant,
        "amount": Decimal("100"),
    }
    assert canonical_json(first) == canonical_json(second)
    assert dependency_fingerprint(first) == dependency_fingerprint(second)
    assert dependency_fingerprint(first) != dependency_fingerprint({**second, "amount": Decimal("101")})
    assert dependency_fingerprint({"optional": None}) != dependency_fingerprint({})
    assert dependency_fingerprint(first) == dependency_fingerprint(first)


def test_manifest_is_typed_readable_versioned_and_order_independent() -> None:
    payload = _payload()
    second_grant = copy.deepcopy(payload["grants"][0])
    second_grant["grant_id"] = "grant-2"
    payload["grants"].append(second_grant)
    second_cap = copy.deepcopy(payload["actual_capitalizations"][0])
    second_cap["capitalization_id"] = "cap-2"
    payload["actual_capitalizations"].append(second_cap)

    original = _manifest(_admitted(payload))
    reordered_payload = copy.deepcopy(payload)
    reordered_payload["grants"].reverse()
    reordered_payload["actual_capitalizations"].reverse()
    reordered_payload["upstream_context"]["warnings"].reverse()
    reordered = _manifest(_admitted(reordered_payload))

    assert original.manifest_schema_version == "pkg003.fixation-dependency-manifest.v1"
    assert original.fingerprint_algorithm_version == "sha256-canonical-json-v1"
    assert original.manifest_fingerprint == reordered.manifest_fingerprint
    assert [entry.stable_identity for entry in original.dependencies if entry.dependency_type == "grant"] == [
        "grant-1",
        "grant-2",
    ]
    parameter = next(entry for entry in original.dependencies if entry.dependency_type == "parameter_set")
    assert parameter.canonical_content is not None
    assert parameter.canonical_content.values.monthly_cap == Decimal("1000.0")
    assert parameter.fingerprint is not None


@pytest.mark.parametrize(
    ("path", "value", "dependency_type"),
    [
        (("grants", 0, "nominal_amount"), 1001.0, "grant"),
        (("grants", 0, "grant_date"), "2020-02-04", "grant"),
        (("grants", 0, "work_start_date"), "2010-01-02", "grant"),
        (("grants", 0, "work_end_date"), "2020-02-01", "grant"),
        (("grants", 0, "inclusion_decision"), "exclude", "grant"),
        (("grants", 0, "accepted_for_use"), False, "grant"),
        (("grants", 0, "support_status"), "unsupported", "grant"),
        (("grants", 0, "indexed_amount"), 1201.0, "grant"),
        (("grants", 0, "source_basis"), "changed basis", "grant"),
        (("grants", 0, "accepted_value"), 1002.0, "grant"),
        (("actual_capitalizations", 0, "amount"), 26.0, "capitalization"),
        (("actual_capitalizations", 0, "capitalization_date"), "2025-01-02", "capitalization"),
        (("actual_capitalizations", 0, "recorded_meaning"), "changed meaning", "capitalization"),
        (("actual_capitalizations", 0, "inclusion_decision"), "exclude", "capitalization"),
        (("actual_capitalizations", 0, "accepted_for_use"), False, "capitalization"),
        (("actual_capitalizations", 0, "support_status"), "unsupported", "capitalization"),
        (("future_grant_reservation", "amount"), 51.0, "future_reserve"),
        (("future_grant_reservation", "source_basis"), "changed reserve basis", "future_reserve"),
        (("future_grant_reservation", "accepted_for_use"), False, "future_reserve"),
        (("future_grant_reservation", "actor"), "planner-2", "future_reserve"),
        (("future_grant_reservation", "decision_timestamp"), "2026-01-01T07:02:01Z", "future_reserve"),
        (("upstream_context", "state"), "qualified", "m07"),
        (("upstream_context", "warnings", 0, "message"), "changed warning", "m07"),
        (("upstream_context", "review_reason"), "changed review", "m07"),
        (("upstream_context", "reviewed_by"), "planner-2", "m07"),
        (("upstream_context", "review_timestamp"), "2026-01-01T07:00:01Z", "m07"),
        (("upstream_context", "qualification_trace_id"), "trace-2", "m07"),
        (("parameter_set", "parameter_set_id"), "params-2026-b", "parameter_set"),
        (("parameter_set", "values", "monthly_cap"), 1001.0, "parameter_set"),
        (("parameter_set", "effective_from"), "2025-12-31", "parameter_set"),
        (("parameter_set", "accepted_by"), "planner-2", "parameter_set"),
        (("parameter_set", "decision_timestamp"), "2026-01-01T07:00:01Z", "parameter_set"),
        (("eligibility_date",), "2026-01-02", "calculation_context"),
        (("calculation_version",), "pkg-003-v2", "calculation_context"),
    ],
)
def test_semantic_dependency_changes_are_detected(path: tuple, value: object, dependency_type: str) -> None:
    baseline_context = _admitted(_payload())
    historical = _manifest(baseline_context)
    changed_payload = baseline_context.model_dump(mode="json")
    target = changed_payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    current = _manifest(AdmissibleFixationInput(**changed_payload))

    comparison = compare_fixation_dependency_manifests(historical, current, assessment_timestamp=NOW)
    assert comparison.technical_result == "changed"
    assert dependency_type in comparison.changed_dependency_types
    assert comparison.changed_fields


@pytest.mark.parametrize(
    ("input_version", "result_version"),
    [("input-v2", "pkg-003-v1"), ("pkg-003-v1", "result-v2")],
)
def test_contract_version_changes_are_detected(
    input_version: str,
    result_version: str,
) -> None:
    context = _admitted(_payload())
    comparison = compare_fixation_dependency_manifests(
        _manifest(context),
        _manifest(
            context,
            input_contract_version=input_version,
            result_contract_version=result_version,
        ),
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "changed"
    assert comparison.changed_dependency_types == ["calculation_context"]


def test_eligibility_year_change_is_fingerprinted() -> None:
    baseline_context = _admitted(_payload())
    changed_payload = baseline_context.model_dump(mode="json")
    changed_payload["eligibility_date"] = "2027-01-01"
    changed_payload["eligibility_year"] = 2027
    changed_payload["parameter_set"]["tax_year"] = 2027
    changed_payload["parameter_set"]["effective_from"] = "2027-01-01"
    changed_payload["parameter_set"]["effective_to"] = "2027-12-31"
    comparison = compare_fixation_dependency_manifests(
        _manifest(baseline_context),
        _manifest(AdmissibleFixationInput(**changed_payload)),
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "changed"
    assert "calculation_context" in comparison.changed_dependency_types
    assert any("eligibility_year" in field for field in comparison.changed_fields)


def test_parameter_acceptance_status_change_is_detected() -> None:
    baseline_context = _admitted(_payload())
    historical = _manifest(baseline_context)
    changed_payload = baseline_context.model_dump(mode="json")
    changed_payload["parameter_set"]["status"] = "rejected"
    changed_payload["parameter_set"]["accepted_for_use"] = False
    current = _manifest(AdmissibleFixationInput(**changed_payload))

    comparison = compare_fixation_dependency_manifests(historical, current, assessment_timestamp=NOW)
    assert comparison.technical_result == "changed"
    assert "parameter_set" in comparison.changed_dependency_types
    assert any("status" in field for field in comparison.changed_fields)


@pytest.mark.parametrize(
    ("field_path", "value"),
    [
        (("cbs_request_evidence", "amount"), "1001"),
        (("cbs_request_evidence", "resolved_base_date"), "2020-02-04"),
        (("system_calculated_amount",), 1235.0),
        (("selected_calculation_amount",), 1235.0),
        (("cbs_response_evidence", "raw_to_value"), "1235"),
    ],
)
def test_caller_cbs_dependency_changes_remain_unknown(field_path: tuple, value: object) -> None:
    context = _admitted(
        _payload(mode="cbs_system_calculation_required"),
        calculator=lambda **_kwargs: _success(),
    )
    historical = _persisted_manifest(context)
    current_payload = context.model_dump(mode="json")
    target = current_payload["grants"][0]
    for part in field_path[:-1]:
        target = target[part]
    target[field_path[-1]] = value
    current = _persisted_manifest(AdmissibleFixationInput(**current_payload))

    comparison = compare_fixation_dependency_manifests(
        historical,
        current,
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["current_cbs_evidence_unavailable"]
    assert comparison.unavailable_dependencies == ["cbs:grant-1"]


def test_missing_cbs_dependency_is_unknown_not_unchanged_or_changed() -> None:
    historical_context = AdmissibleFixationInput(
        **_payload(mode="cbs_system_calculation_required")
    )
    failure = _failure()
    historical_grant = historical_context.grants[0]
    historical_grant.asserted_indexed_amount = historical_grant.indexed_amount
    historical_grant.cbs_request_evidence = failure.request
    historical_grant.indexation_failure_evidence = failure.failure
    historical_grant.indexation_calculation_status = "failed"
    current_payload = _payload(mode="cbs_system_calculation_required")
    current_payload["grants"][0]["asserted_indexed_amount"] = 1200.0
    current_context = AdmissibleFixationInput(**current_payload)
    comparison = compare_fixation_dependency_manifests(
        _persisted_manifest(historical_context),
        _manifest(current_context),
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["current_cbs_evidence_unavailable"]
    assert comparison.unavailable_dependencies == ["cbs:grant-1"]


def test_direct_caller_cbs_manifest_cannot_bypass_trust_boundary() -> None:
    context = _admitted(
        _payload(mode="cbs_system_calculation_required"),
        calculator=lambda **_kwargs: _success(),
    )
    historical = _persisted_manifest(context)
    current = _manifest(context)
    assert current.context_availability == "unavailable"
    comparison = compare_fixation_dependency_manifests(
        historical,
        historical.model_copy(deep=True),
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["current_cbs_evidence_unavailable"]
    assert comparison.unavailable_dependencies == ["cbs:grant-1"]


def test_public_dependency_signatures_have_no_caller_controlled_trust_flags() -> None:
    build_parameters = inspect.signature(build_fixation_dependency_manifest).parameters
    compare_parameters = inspect.signature(compare_fixation_dependency_manifests).parameters
    assert "trusted_system_evidence" not in build_parameters
    assert "current_context_is_trusted" not in compare_parameters
    assert not any("trust" in name or "provenance" in name for name in build_parameters)
    assert not any("trust" in name or "provenance" in name for name in compare_parameters)

    context = _admitted(_payload())
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        _manifest(context, trusted_system_evidence=True)
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        compare_fixation_dependency_manifests(
            _manifest(context),
            _manifest(context),
            current_context_is_trusted=True,
        )
    removed_symbols = {
        "_SERVER_PROVENANCE_TOKEN",
        "_ServerAdmittedDependencyContext",
        "_ServerProducedDependencyManifest",
        "_build_server_admitted_dependency_manifest",
    }
    assert all(not hasattr(dependency_service, symbol) for symbol in removed_symbols)


@pytest.mark.parametrize(
    "evidence_field",
    ["cbs_request_evidence", "cbs_response_evidence"],
)
def test_direct_service_rejects_caller_supplied_cbs_evidence(evidence_field: str) -> None:
    server_context = _admitted(
        _payload(mode="cbs_system_calculation_required"),
        calculator=lambda **_kwargs: _success(),
    )
    historical = _persisted_manifest(server_context)
    caller_payload = server_context.model_dump(mode="json")
    assert caller_payload["grants"][0][evidence_field] is not None
    caller_context = AdmissibleFixationInput(**caller_payload)
    current = _manifest(caller_context)

    assert current.context_availability == "unavailable"
    comparison = compare_fixation_dependency_manifests(
        historical,
        current,
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["current_cbs_evidence_unavailable"]
    assert comparison.unavailable_dependencies == ["cbs:grant-1"]


def test_saved_cbs_manifest_cannot_be_reused_as_current_and_comparison_makes_no_live_call() -> None:
    calls = 0

    def calculator(**_kwargs):
        nonlocal calls
        calls += 1
        return _success()

    server_context = _admitted(
        _payload(mode="cbs_system_calculation_required"),
        calculator=calculator,
    )
    assert calls == 1
    historical = _persisted_manifest(server_context)
    current = historical.model_copy(deep=True)
    comparison = compare_fixation_dependency_manifests(
        historical,
        current,
        assessment_timestamp=NOW,
    )
    assert calls == 1
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["current_cbs_evidence_unavailable"]
    assert comparison.unavailable_dependencies == ["cbs:grant-1"]


@pytest.mark.parametrize(
    ("dependency_type", "missing_label"),
    [
        ("calculation_context", "current:calculation_context"),
        ("m07", "current:m07"),
        ("parameter_set", "current:parameter_set"),
        ("grant", "current:grant:grant-1"),
        ("capitalization", "current:capitalization:cap-1"),
    ],
)
def test_missing_mandatory_dependency_is_unknown(
    dependency_type: str,
    missing_label: str,
) -> None:
    context = _admitted(_payload())
    historical = _manifest(context)
    current = _manifest(context).model_copy(
        update={
            "dependencies": [
                entry
                for entry in _manifest(context).dependencies
                if entry.dependency_type != dependency_type
            ]
        }
    )
    comparison = compare_fixation_dependency_manifests(
        historical,
        current,
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["mandatory_dependency_missing"]
    assert missing_label in comparison.unavailable_dependencies
    assert comparison.changed_dependency_types == []


def test_missing_required_cbs_dependency_is_unknown() -> None:
    server_context = _admitted(
        _payload(mode="cbs_system_calculation_required"),
        calculator=lambda **_kwargs: _success(),
    )
    historical = _persisted_manifest(server_context)
    current = _manifest(_admitted(_payload()))
    comparison = compare_fixation_dependency_manifests(
        historical,
        current,
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["mandatory_dependency_missing"]
    assert comparison.unavailable_dependencies == ["current:cbs:grant-1"]
    assert comparison.changed_dependency_types == []


@pytest.mark.parametrize("dependency_type", ["grant", "capitalization"])
def test_duplicate_stable_identities_fail_closed(dependency_type: str) -> None:
    historical_payload = _payload()
    collection_name = "grants" if dependency_type == "grant" else "actual_capitalizations"
    duplicate = copy.deepcopy(historical_payload[collection_name][0])
    duplicate_id = duplicate[
        "grant_id" if dependency_type == "grant" else "capitalization_id"
    ]
    historical_payload[collection_name].append(duplicate)
    current_payload = copy.deepcopy(historical_payload)
    amount_field = "nominal_amount" if dependency_type == "grant" else "amount"
    current_payload[collection_name][1][amount_field] += 1

    historical = _manifest(AdmissibleFixationInput(**historical_payload))
    current = _manifest(AdmissibleFixationInput(**current_payload))
    assert historical.manifest_fingerprint != current.manifest_fingerprint
    comparison = compare_fixation_dependency_manifests(
        historical,
        current,
        assessment_timestamp=NOW,
    )
    assert comparison.technical_result == "unknown"
    assert comparison.reason_codes == ["duplicate_dependency_identity"]
    assert comparison.unavailable_dependencies == [f"{dependency_type}:{duplicate_id}"]


def test_manifest_identifier_and_client_run_invariant_are_enforced() -> None:
    generated_ids = {_new_dependency_manifest_id() for _ in range(20)}
    assert len(generated_ids) == 20
    assert all(identifier.startswith("dependency-manifest-") for identifier in generated_ids)
    assert all(len(identifier) <= 64 for identifier in generated_ids)

    context = _admitted(_payload())
    manifest = _manifest(context)
    run = FixationRun(
        id=manifest.run_id,
        fixation_run_id=manifest.run_identity,
        client_id=manifest.client_id,
        calculation_version=manifest.calculation_version,
        status="success",
        is_latest=True,
    )
    model = _dependency_manifest_model(run, manifest)
    assert model.client_id == run.client_id
    assert model.fixation_run_id == run.id
    assert len(model.fixation_dependency_manifest_id) <= 64

    mismatched = manifest.model_copy(update={"client_id": manifest.client_id + 1})
    with pytest.raises(ValueError, match="client identity"):
        _dependency_manifest_model(run, mismatched)


def test_context_availability_contract_has_no_professional_lifecycle_implication() -> None:
    description = FixationDependencyManifest.model_json_schema()["properties"][
        "context_availability"
    ]["description"]
    assert "could be parsed and stored" in description
    assert "does not assert professional acceptance" in description
    manifest_payload = _manifest(_admitted(_payload())).model_dump(mode="json")
    serialized = canonical_json(manifest_payload)
    assert '"eligible"' not in serialized
    assert '"stale"' not in serialized
    assert '"superseded"' not in serialized


def test_api_persists_immutable_manifest_and_compares_without_side_effects_or_live_cbs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "pkg003-api.db"
    _upgrade_database(db_path)
    session_local = sessionmaker(bind=create_engine(f"sqlite:///{db_path.as_posix()}"))

    def override_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        owner = client.post(
            "/api/clients",
            json={"full_name": "Manifest Owner", "id_number": "manifest-owner", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        other = client.post(
            "/api/clients",
            json={"full_name": "Manifest Other", "id_number": "manifest-other", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        with session_local() as session:
            owner_revision, _ = seed_eligibility_revision(
                session,
                client_id=owner,
            )
            other_revision, _ = seed_eligibility_revision(
                session,
                client_id=other,
            )
            session.commit()

        def api_payload(*, client_id: int = owner, mode: str = "asserted_indexed_amount") -> dict:
            revision_id = owner_revision if client_id == owner else other_revision
            payload = resolver_payload(
                _payload(client_id=client_id, mode=mode),
                revision_id=revision_id,
            )
            payload["grants_collection_state"] = "confirmed_none"
            payload["grants"] = []
            return payload

        payload = api_payload()
        saved = client.post("/api/fixation/save", json={"client_id": owner, "input_data": payload})
        assert saved.status_code == 200 and saved.json()["status"] == "success"
        run_id = saved.json()["run_id"]
        detail_before = client.get(f"/api/clients/{owner}/fixation/runs/{run_id}").json()
        history_before = client.get(f"/api/clients/{owner}/fixation/history").json()
        latest_before = client.get(f"/api/clients/{owner}/fixation/latest").json()

        manifest_response = client.get(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-manifest"
        )
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()["manifest"]
        assert manifest_response.json()["availability"] == "available"
        assert manifest["run_id"] == run_id and manifest["client_id"] == owner
        assert manifest["result_contract_version"] == "pkg-003-v1"
        assert manifest["manifest_fingerprint"]

        monkeypatch.setattr(
            "app.services.fixation_admission_service.calculate_cbs_indexation",
            lambda **_kwargs: (_ for _ in ()).throw(AssertionError("comparison made a live CBS call")),
        )
        unchanged = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(payload),
        )
        assert unchanged.status_code == 200
        assert unchanged.json()["technical_result"] == "unchanged", unchanged.json()

        changed_context = copy.deepcopy(payload)
        changed_context["parameter_set"]["values"]["monthly_cap"] = 1001.0
        changed = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(changed_context),
        )
        assert changed.status_code == 200
        assert changed.json()["technical_result"] == "changed"
        assert "parameter_set" in changed.json()["changed_dependency_types"]

        unknown = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(None),
        )
        assert unknown.status_code == 200
        assert unknown.json()["technical_result"] == "unknown"
        assert unknown.json()["reason_codes"] == ["current_dependency_context_unavailable"]

        blocked_context = copy.deepcopy(payload)
        blocked_context["upstream_context"] = {
            "profile_id": "legacy-m07",
            "client_id": owner,
            "state": "blocked",
        }
        blocked = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(blocked_context),
        )
        assert blocked.status_code == 200
        assert blocked.json()["technical_result"] == "unknown"
        assert blocked.json()["reason_codes"] == ["current_admitted_context_unavailable"]

        mismatch_context = copy.deepcopy(payload)
        mismatch_context["m07_input_reference"]["b1_evidence_revision_id"] = (
            other_revision
        )
        mismatch = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(mismatch_context),
        )
        assert mismatch.status_code == 200
        assert mismatch.json()["technical_result"] == "unknown"
        assert mismatch.json()["reason_codes"] == [
            "current_admitted_context_unavailable"
        ]
        assert client.get(
            f"/api/clients/{other}/fixation/runs/{run_id}/dependency-manifest"
        ).status_code == 404
        assert client.post(
            f"/api/clients/{other}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(payload),
        ).status_code == 404

        missing_input_version = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(payload, input_contract_version=None),
        )
        assert missing_input_version.status_code == 200
        assert missing_input_version.json()["technical_result"] == "unknown"
        assert missing_input_version.json()["reason_codes"] == [
            "current_contract_version_unavailable"
        ]
        missing_result_version = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(payload, result_contract_version=None),
        )
        assert missing_result_version.status_code == 200
        assert missing_result_version.json()["technical_result"] == "unknown"
        assert missing_result_version.json()["reason_codes"] == [
            "current_contract_version_unavailable"
        ]

        historical_snapshot_as_current = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(detail_before["input_snapshot"]),
        )
        assert historical_snapshot_as_current.status_code == 200
        assert historical_snapshot_as_current.json()["technical_result"] == "unknown"
        assert historical_snapshot_as_current.json()["reason_codes"] == [
            "current_admitted_context_unavailable"
        ]

        forged_cbs_context = resolver_payload(
            _payload(client_id=owner, mode="cbs_system_calculated"),
            revision_id=owner_revision,
        )
        forged_cbs_context["grants"][0]["system_calculated_amount"] = 777777.0
        forged_cbs_context["grants"][0]["selected_calculation_amount"] = 777777.0
        forged_cbs_context["grants"][0]["cbs_request_evidence"] = _success().request.model_dump(
            mode="json"
        )
        forged_cbs_context["grants"][0]["cbs_response_evidence"] = _success().response.model_dump(
            mode="json"
        )
        forged = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(forged_cbs_context),
        )
        assert forged.status_code == 200
        assert forged.json()["technical_result"] == "unknown"
        assert forged.json()["reason_codes"] == ["current_cbs_evidence_unavailable"]

        cbs_required = client.post(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-comparison",
            json=_comparison_request(
                resolver_payload(
                    _payload(client_id=owner, mode="cbs_system_calculation_required"),
                    revision_id=owner_revision,
                )
            ),
        )
        assert cbs_required.status_code == 200
        assert cbs_required.json()["technical_result"] == "unknown"
        assert cbs_required.json()["reason_codes"] == ["current_cbs_evidence_unavailable"]

        detached_current_context = copy.deepcopy(detail_before["input_snapshot"])
        detached_current_context["parameter_set"]["values"]["monthly_cap"] = 999999.0
        manifest_after = client.get(
            f"/api/clients/{owner}/fixation/runs/{run_id}/dependency-manifest"
        ).json()["manifest"]
        assert manifest_after == manifest
        assert client.get(f"/api/clients/{owner}/fixation/runs/{run_id}").json() == detail_before
        assert client.get(f"/api/clients/{owner}/fixation/history").json() == history_before
        assert client.get(f"/api/clients/{owner}/fixation/latest").json() == latest_before

        with session_local() as session:
            assert session.scalar(select(func.count()).select_from(FixationDependencyManifestModel)) == 1
            saved_run = session.get(FixationRun, run_id)
            assert saved_run is not None and saved_run.is_latest is True
            persisted_manifest = session.scalar(
                select(FixationDependencyManifestModel).where(
                    FixationDependencyManifestModel.fixation_run_id == run_id
                )
            )
            assert persisted_manifest is not None
            assert len(persisted_manifest.fixation_dependency_manifest_id) <= 64
            assert (
                FixationDependencyManifestModel.__table__
                .c.fixation_dependency_manifest_id.type.length
                == 64
            )
    finally:
        app.dependency_overrides.clear()


def test_new_failure_runs_have_explicit_manifest_behavior_and_legacy_run_is_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "pkg003-statuses.db"
    _upgrade_database(db_path)
    session_local = sessionmaker(bind=create_engine(f"sqlite:///{db_path.as_posix()}"))

    def override_db():
        with session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        owner = client.post(
            "/api/clients",
            json={"full_name": "Status Owner", "id_number": "status-owner", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        with session_local() as session:
            owner_revision, _ = seed_eligibility_revision(
                session,
                client_id=owner,
            )
            session.add(
                Grant(
                    grant_id="grant-1",
                    client_id=owner,
                    employer_name="Employer",
                    employer_withholding_file_number="WF-1",
                    nominal_amount=Decimal("1000.00"),
                    indexed_amount=None,
                    grant_date=date(2020, 2, 3),
                    work_start_date=date(2010, 1, 1),
                    work_end_date=date(2020, 1, 31),
                    notes=None,
                )
            )
            session.commit()

        def api_payload(*, mode: str = "asserted_indexed_amount") -> dict:
            payload = resolver_payload(
                _payload(client_id=owner, mode=mode),
                revision_id=owner_revision,
            )
            payload["grants_collection_state"] = "confirmed_none"
            payload["grants"] = []
            return payload

        monkeypatch.setattr(
            "app.services.fixation_admission_service.calculate_cbs_indexation",
            lambda **_kwargs: _success(),
        )
        cbs_success = client.post(
            "/api/fixation/save",
            json={
                "client_id": owner,
                "input_data": api_payload(mode="cbs_system_calculation_required"),
            },
        ).json()
        assert cbs_success["status"] == "success"
        cbs_manifest_url = (
            f"/api/clients/{owner}/fixation/runs/{cbs_success['run_id']}/dependency-manifest"
        )
        saved_cbs_manifest = client.get(cbs_manifest_url).json()["manifest"]
        saved_cbs_entry = next(
            entry
            for entry in saved_cbs_manifest["dependencies"]
            if entry["dependency_type"] == "cbs"
        )
        assert saved_cbs_entry["canonical_content"]["response_evidence"]["raw_to_value"] == (
            "1234.5678"
        )
        comparison = client.post(
            f"/api/clients/{owner}/fixation/runs/{cbs_success['run_id']}/dependency-comparison",
            json=_comparison_request(
                resolver_payload(
                    _payload(client_id=owner, mode="cbs_system_calculation_required"),
                    revision_id=owner_revision,
                )
            ),
        ).json()
        assert comparison["technical_result"] == "unknown"
        assert comparison["reason_codes"] == ["current_cbs_evidence_unavailable"]
        assert comparison["unavailable_dependencies"] == ["cbs:grant-1"]
        assert client.get(cbs_manifest_url).json()["manifest"] == saved_cbs_manifest

        structural = api_payload()
        structural.pop("parameter_set")
        validation_failed = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": structural},
        ).json()
        assert validation_failed["status"] == "validation_failed"
        validation_manifest = client.get(
            f"/api/clients/{owner}/fixation/runs/{validation_failed['run_id']}/dependency-manifest"
        ).json()
        assert validation_manifest["availability"] == "available"
        assert validation_manifest["manifest"]["context_availability"] == "unavailable"

        monkeypatch.setattr(
            "app.services.fixation_admission_service.calculate_cbs_indexation",
            lambda **_kwargs: _failure(),
        )
        calculation_failed = client.post(
            "/api/fixation/save",
            json={
                "client_id": owner,
                "input_data": api_payload(mode="cbs_system_calculation_required"),
            },
        ).json()
        assert calculation_failed["status"] == "calculation_failed"
        failure_manifest = client.get(
            f"/api/clients/{owner}/fixation/runs/{calculation_failed['run_id']}/dependency-manifest"
        ).json()["manifest"]
        cbs = next(entry for entry in failure_manifest["dependencies"] if entry["dependency_type"] == "cbs")
        assert cbs["canonical_content"]["failure_evidence"]["failure_category"] == "timeout"

        special_payload = api_payload()
        special_payload["idf"] = {
            "idf_id": "idf-pkg003",
            "reduction_amount": 1000.0,
            "original_commutation_percent": 25.0,
            "current_commutation_percent": 20.0,
            "commutation_date": "2025-01-01",
            "promoter_age_date": "2027-01-01",
        }
        special = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": special_payload},
        ).json()
        assert special["status"] == "requires_special_handling"
        assert client.get(
            f"/api/clients/{owner}/fixation/runs/{special['run_id']}/dependency-manifest"
        ).json()["manifest"]["context_availability"] == "available"

        with session_local() as session:
            legacy = FixationRun(
                fixation_run_id="legacy-without-manifest",
                client_id=owner,
                calculation_version="legacy-v1",
                status="validation_failed",
                is_latest=False,
            )
            session.add(legacy)
            session.commit()
            legacy_id = legacy.id

        legacy_manifest = client.get(
            f"/api/clients/{owner}/fixation/runs/{legacy_id}/dependency-manifest"
        )
        assert legacy_manifest.status_code == 200
        assert legacy_manifest.json() == {
            "run_id": legacy_id,
            "client_id": owner,
            "availability": "unavailable",
            "reason_codes": ["manifest_unavailable_for_legacy_run"],
            "manifest": None,
        }
        legacy_comparison = client.post(
            f"/api/clients/{owner}/fixation/runs/{legacy_id}/dependency-comparison",
            json={"current_context": api_payload()},
        )
        assert legacy_comparison.status_code == 200
        assert legacy_comparison.json()["technical_result"] == "unknown"
        assert legacy_comparison.json()["reason_codes"] == ["manifest_unavailable_for_legacy_run"]
    finally:
        app.dependency_overrides.clear()
