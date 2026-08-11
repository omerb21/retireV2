from __future__ import annotations

import copy
import inspect
import os
import subprocess
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.engines.fixation_engine import calculate_fixation
import app.engines.fixation_engine as fixation_engine_module
from app.main import app
from app.models.client import Client
from app.schemas.cbs_indexation import (
    CBS_CALCULATOR_ENDPOINT,
    CBS_CPI_CODE,
    CbsIndexationFailure,
    CbsIndexationFailureEvidence,
    CbsIndexationRequestEvidence,
    CbsIndexationResponseEvidence,
    CbsIndexationSuccess,
)
from app.services.cbs_indexation_adapter import (
    CBS_MAX_TRANSPORT_RETRIES,
    build_cbs_indexation_request,
    calculate_cbs_indexation,
)
from app.services.fixation_admission_service import parse_and_admit_fixation_payload
from app.services.fixation_service import calculate_fixation_payload
from tests.pkg004d_test_support import resolver_payload, seed_eligibility_revision


load_all_models()
NOW = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
_UNIT_ENGINE = create_engine("sqlite:///:memory:")
Base.metadata.create_all(_UNIT_ENGINE)
_UNIT_SESSION = sessionmaker(bind=_UNIT_ENGINE)()
_UNIT_SESSION.add_all(
    [
        Client(client_id=1, display_name="Client 1", id_number="pkg002-client-1"),
        Client(client_id=2, display_name="Client 2", id_number="pkg002-client-2"),
    ]
)
_UNIT_SESSION.commit()
_UNIT_REVISIONS = {
    client_id: seed_eligibility_revision(
        _UNIT_SESSION,
        client_id=client_id,
    )[0]
    for client_id in (1, 2)
}


def _legacy_payload(
    *, client_id: int = 1, mode: str = "asserted_indexed_amount"
) -> dict:
    return {
        "calculation_id": "pkg-002",
        "calculation_version": "pkg-002-v1",
        "eligibility_date": "2026-01-01",
        "eligibility_year": 2026,
        "upstream_context": {"profile_id": "m07-1", "client_id": client_id, "state": "qualified"},
        "parameter_set": {
            "parameter_set_id": "params-2026",
            "client_id": client_id,
            "tax_year": 2026,
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
                "grant_id": "grant-cbs-1",
                "client_id": client_id,
                "item_type": "severance_grant",
                "nominal_amount": 1000.0,
                "indexed_amount": 9999.0,
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
        "future_grant_reservation": None,
        "actual_capitalizations_collection_state": "confirmed_none",
        "actual_capitalizations": [],
        "idf": None,
    }


def _payload(
    *, client_id: int = 1, mode: str = "asserted_indexed_amount"
) -> dict:
    return resolver_payload(
        _legacy_payload(client_id=client_id, mode=mode),
        revision_id=_UNIT_REVISIONS[client_id],
    )


def _success(*, raw: str = "1234.5678") -> CbsIndexationSuccess:
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
            raw_to_value=Decimal(raw),
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


def _failure(*, unsupported: bool = False) -> CbsIndexationFailure:
    success = _success()
    return CbsIndexationFailure(
        request=success.request,
        failure=CbsIndexationFailureEvidence(
            outcome_status="unsupported_calculation" if unsupported else "calculation_failed",
            failure_category="unsupported_calculation" if unsupported else "timeout",
            timeout=not unsupported,
            calculation_timestamp=NOW,
            safe_technical_message=(
                "CBS calculator does not support this request"
                if unsupported
                else "CBS calculator request timed out"
            ),
        ),
    )


def test_adapter_uses_only_approved_endpoint_code_mapping_and_evidence() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(
            200,
            json={
                "answer": {
                    "to_value": "1234.5678",
                    "from_index_period": "01-2020",
                    "to_index_period": "12-2025",
                    "from_index_value": "99.1",
                    "to_index_value": "110.2",
                    "base_year": "Average 2024=100",
                    "chaining_coefficient": "1.0012",
                    "change_percentage": "11.2",
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        outcome = calculate_cbs_indexation(
            amount=Decimal("1000"),
            grant_date=date(2020, 2, 3),
            work_end_date=date(2020, 1, 31),
            eligibility_date=date(2026, 1, 1),
            client=client,
        )

    assert isinstance(outcome, CbsIndexationSuccess)
    assert captured["url"].startswith(CBS_CALCULATOR_ENDPOINT)
    assert CBS_CPI_CODE == "120010"
    assert captured["params"] == {
        "value": "1000",
        "date": "2020-02-03",
        "toDate": "2026-01-01",
        "format": "json",
        "download": "false",
        "lang": "en",
    }
    assert outcome.response.raw_to_value == Decimal("1234.5678")
    assert outcome.response.chaining_coefficient == Decimal("1.0012")
    assert outcome.response.missing_optional_fields == []


def test_request_builder_uses_work_end_fallback_and_rejects_missing_dates() -> None:
    request = build_cbs_indexation_request(
        amount=Decimal("1000"),
        grant_date=None,
        work_end_date=date(2020, 1, 31),
        eligibility_date=date(2026, 1, 1),
        calculation_timestamp=NOW,
    )
    assert isinstance(request, CbsIndexationRequestEvidence)
    assert request.resolved_base_date == date(2020, 1, 31)
    assert request.base_date_source == "work_end_date"

    failure = build_cbs_indexation_request(
        amount=Decimal("1000"),
        grant_date=None,
        work_end_date=None,
        eligibility_date=date(2026, 1, 1),
        calculation_timestamp=NOW,
    )
    assert isinstance(failure, CbsIndexationFailure)
    assert failure.failure.failure_category == "missing_base_date"

    unsupported = build_cbs_indexation_request(
        amount=Decimal("0"),
        grant_date=date(2020, 1, 1),
        work_end_date=date(2020, 1, 1),
        eligibility_date=date(2026, 1, 1),
        calculation_timestamp=NOW,
    )
    assert isinstance(unsupported, CbsIndexationFailure)
    assert unsupported.failure.outcome_status == "unsupported_calculation"


@pytest.mark.parametrize(
    ("response", "category"),
    [
        (httpx.Response(200, text="not-json"), "malformed_response"),
        (httpx.Response(200, json={}), "missing_answer"),
        (httpx.Response(200, json={"answer": {}}), "missing_to_value"),
        (
            httpx.Response(200, json={"answer": {"to_value": "1", "from_index_period": {"bad": "shape"}}}),
            "malformed_response",
        ),
        (httpx.Response(503, json={"answer": {"to_value": 1}}), "http_error"),
    ],
)
def test_adapter_fails_closed_without_retry_for_response_failures(
    response: httpx.Response,
    category: str,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        outcome = calculate_cbs_indexation(
            amount=Decimal("1000"),
            grant_date=date(2020, 1, 1),
            work_end_date=date(2020, 1, 1),
            eligibility_date=date(2026, 1, 1),
            client=client,
        )
    assert isinstance(outcome, CbsIndexationFailure)
    assert outcome.failure.failure_category == category
    assert calls == 1


@pytest.mark.parametrize("raw_value", ["NaN", "Infinity", "-Infinity"])
def test_adapter_rejects_non_finite_result_without_retry(raw_value: str) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"answer": {"to_value": raw_value}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        outcome = calculate_cbs_indexation(
            amount=Decimal("1000"),
            grant_date=date(2020, 1, 1),
            work_end_date=date(2020, 1, 1),
            eligibility_date=date(2026, 1, 1),
            client=client,
        )

    assert isinstance(outcome, CbsIndexationFailure)
    assert outcome.failure.failure_category == "malformed_response"
    assert outcome.failure.malformed_response is True
    assert outcome.request is not None
    assert calls == 1


def test_adapter_retries_once_only_for_transport_failure() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ReadTimeout("transient timeout", request=request)
        return httpx.Response(200, json={"answer": {"to_value": "1001.25"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        outcome = calculate_cbs_indexation(
            amount=Decimal("1000"),
            grant_date=date(2020, 1, 1),
            work_end_date=date(2020, 1, 1),
            eligibility_date=date(2026, 1, 1),
            client=client,
        )
    assert isinstance(outcome, CbsIndexationSuccess)
    assert calls == CBS_MAX_TRANSPORT_RETRIES + 1 == 2
    assert set(outcome.response.missing_optional_fields) == {
        "from_index_period",
        "to_index_period",
        "from_index_value",
        "to_index_value",
        "base_year",
        "chaining_coefficient",
        "change_percentage",
    }


def test_adapter_final_timeout_is_typed_and_unexpected_exceptions_are_not_swallowed() -> None:
    timeout_calls = 0

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        nonlocal timeout_calls
        timeout_calls += 1
        raise httpx.ReadTimeout("timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout_handler)) as client:
        outcome = calculate_cbs_indexation(
            amount=Decimal("1000"),
            grant_date=date(2020, 1, 1),
            work_end_date=date(2020, 1, 1),
            eligibility_date=date(2026, 1, 1),
            client=client,
        )
    assert isinstance(outcome, CbsIndexationFailure)
    assert outcome.failure.timeout is True
    assert timeout_calls == 2

    def unexpected_handler(_request: httpx.Request) -> httpx.Response:
        raise RuntimeError("unexpected programming failure")

    with httpx.Client(transport=httpx.MockTransport(unexpected_handler)) as client:
        with pytest.raises(RuntimeError, match="unexpected programming failure"):
            calculate_cbs_indexation(
                amount=Decimal("1000"),
                grant_date=date(2020, 1, 1),
                work_end_date=date(2020, 1, 1),
                eligibility_date=date(2026, 1, 1),
                client=client,
            )


@pytest.mark.parametrize("gate", ["excluded", "unsupported", "unaccepted"])
def test_non_admissible_grants_never_call_cbs(gate: str) -> None:
    payload = _payload(mode="cbs_system_calculation_required")
    grant = payload["grants"][0]
    if gate == "excluded":
        grant["inclusion_decision"] = "exclude"
    elif gate == "unsupported":
        grant["support_status"] = "unsupported"
    else:
        grant["accepted_for_use"] = False
    calls = 0

    def calculator(**_kwargs):
        nonlocal calls
        calls += 1
        return _success()

    _, _, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=calculator,
    )
    assert calls == 0
    if gate == "excluded":
        assert errors == []
    else:
        assert errors


def test_blocked_m07_never_calls_cbs() -> None:
    payload = _payload(mode="cbs_system_calculation_required")
    payload["upstream_context"] = {"state": "blocked"}
    calls = 0

    def calculator(**_kwargs):
        nonlocal calls
        calls += 1
        return _success()

    _, engine_input, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=calculator,
    )
    assert engine_input is None
    assert calls == 0
    assert {error.path for error in errors} == {"upstream_context"}


def test_asserted_and_cbs_modes_remain_distinct_without_fallback() -> None:
    asserted = _payload()
    asserted["grants"][0]["asserted_indexed_amount"] = 9999.0
    context, engine_input, errors, _ = parse_and_admit_fixation_payload(
        asserted,
        client_id=1,
        db_session=_UNIT_SESSION,
    )
    assert errors == []
    assert context is not None and engine_input is not None
    assert context.grants[0].asserted_indexed_amount == 9999.0
    assert context.grants[0].system_calculated_amount is None
    assert context.grants[0].indexation_calculation_status == "asserted"

    required = _payload(mode="cbs_system_calculation_required")
    context, engine_input, errors, _ = parse_and_admit_fixation_payload(
        required,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=lambda **_kwargs: _success(),
    )
    assert errors == []
    assert context is not None and engine_input is not None
    grant = context.grants[0]
    assert grant.indexation_mode == "cbs_system_calculated"
    assert grant.asserted_indexed_amount == 9999.0
    assert grant.system_calculated_amount == Decimal("1234.57")
    assert grant.selected_calculation_amount == Decimal("1234.57")
    assert grant.cbs_response_evidence is not None
    assert grant.cbs_response_evidence.raw_to_value == Decimal("1234.5678")
    result = calculate_fixation(engine_input)
    assert result.grant_results[0].indexed_amount == Decimal("1234.57")

    failed = calculate_fixation_payload(
        required,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=lambda **_kwargs: _failure(),
    )
    assert failed.status == "calculation_failed"
    assert failed.grant_results is None
    assert failed.validation_errors[0].code == "CBS_CALCULATION_FAILED"


def test_grant_client_mismatch_fails_before_cbs() -> None:
    payload = _payload(mode="cbs_system_calculation_required")
    payload["grants"][0]["client_id"] = 2
    calls = 0

    def calculator(**_kwargs):
        nonlocal calls
        calls += 1
        return _success()

    _, _, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=calculator,
    )
    assert calls == 0
    assert {error.path for error in errors} == {"grants[0].client_id"}


def test_system_calculated_input_cannot_bypass_adapter_and_engine_has_no_http_client() -> None:
    payload = _payload(mode="cbs_system_calculated")
    calls = 0

    def calculator(**_kwargs):
        nonlocal calls
        calls += 1
        return _success()

    _, engine_input, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=calculator,
    )
    assert engine_input is None
    assert calls == 0
    assert {error.path for error in errors} == {"grants[0].indexation_mode"}
    engine_source = inspect.getsource(fixation_engine_module)
    assert "httpx" not in engine_source
    assert CBS_CALCULATOR_ENDPOINT not in engine_source
    assert "fixation_date" not in engine_source

    forged = _payload(mode="cbs_system_calculation_required")
    forged["grants"][0]["system_calculated_amount"] = 777777.0
    (
        forged_context,
        forged_engine_input,
        forged_errors,
        _,
    ) = parse_and_admit_fixation_payload(
        forged,
        client_id=1,
        db_session=_UNIT_SESSION,
        cbs_calculator=calculator,
    )
    assert forged_context is not None
    assert forged_engine_input is None
    assert calls == 0
    assert {error.path for error in forged_errors} == {"grants[0].system_calculated_amount"}


@pytest.mark.parametrize("gate", ["included", "excluded", "unsupported"])
def test_caller_calculated_mode_is_rejected_before_grant_branching(gate: str) -> None:
    payload = _payload(mode="cbs_system_calculated")
    grant = payload["grants"][0]
    if gate == "excluded":
        grant["inclusion_decision"] = "exclude"
    elif gate == "unsupported":
        grant["support_status"] = "unsupported"

    context, engine_input, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
    )

    assert context is not None
    assert engine_input is None
    assert "grants[0].indexation_mode" in {error.path for error in errors}
    assert context.grants[0].indexation_mode == "cbs_system_calculation_required"


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("system_calculated_amount", 777777.0),
        ("selected_calculation_amount", 777777.0),
        ("resolved_base_date", "2020-02-03"),
        ("base_date_source", "grant_date"),
        ("target_date", "2026-01-01"),
        ("cpi_code", "120010"),
        ("cbs_request_evidence", _success().request.model_dump(mode="json")),
        ("cbs_response_evidence", _success().response.model_dump(mode="json")),
        ("indexation_failure_evidence", _failure().failure.model_dump(mode="json")),
        ("indexation_warnings", ["forged system warning"]),
        ("indexation_calculation_status", "calculated"),
    ],
)
def test_caller_system_evidence_fields_are_rejected_and_scrubbed(
    field_name: str,
    field_value: object,
) -> None:
    payload = _payload(mode="cbs_system_calculation_required")
    payload["grants"][0][field_name] = field_value

    context, engine_input, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
    )

    assert context is not None
    assert engine_input is None
    assert {error.path for error in errors} == {f"grants[0].{field_name}"}
    snapshot_grant = context.model_dump(mode="json")["grants"][0]
    if field_name == "indexation_warnings":
        assert snapshot_grant[field_name] == []
    elif field_name == "indexation_calculation_status":
        assert snapshot_grant[field_name] == "pending"
    else:
        assert snapshot_grant[field_name] is None


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


def test_success_and_failure_evidence_is_immutable_and_client_scoped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "pkg002.db"
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
            json={"full_name": "CBS Owner", "id_number": "cbs-owner", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        other = client.post(
            "/api/clients",
            json={"full_name": "CBS Other", "id_number": "cbs-other", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        with session_local() as session:
            owner_revision, _ = seed_eligibility_revision(
                session, client_id=owner
            )
            seed_eligibility_revision(session, client_id=other)
            session.commit()

        def owner_payload(mode: str, *, caller_grant: bool = False) -> dict:
            payload = resolver_payload(
                _legacy_payload(client_id=owner, mode=mode),
                revision_id=owner_revision,
            )
            if not caller_grant:
                payload["grants_collection_state"] = "confirmed_none"
                payload["grants"] = []
            return payload

        forged = owner_payload("cbs_system_calculated", caller_grant=True)
        forged_grant = forged["grants"][0]
        forged_grant["inclusion_decision"] = "exclude"
        forged_grant["system_calculated_amount"] = 777777.0
        forged_grant["selected_calculation_amount"] = 777777.0
        forged_grant["cbs_response_evidence"] = _success(raw="777777").response.model_dump(mode="json")
        forged_save = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": forged},
        )
        assert forged_save.status_code == 200
        assert forged_save.json()["status"] == "validation_failed"
        forged_detail = client.get(
            f"/api/clients/{owner}/fixation/runs/{forged_save.json()['run_id']}"
        ).json()
        assert forged_detail["result"] is None
        assert forged_detail["audit_rows"] == []
        assert forged_detail["input_snapshot"]["grants"] == []
        assert all(
            run["status"] != "success"
            for run in client.get(f"/api/clients/{owner}/fixation/history").json()
        )

        created_grant = client.post(
            f"/api/clients/{owner}/grants",
            json={
                "employer_name": "CBS Employer",
                "employer_withholding_file_number": "WF-CBS",
                "employment_start_date": "2010-01-01",
                "employment_end_date": "2020-01-31",
                "grant_receipt_date": "2020-02-03",
                "exempt_grant_amount": "1000",
            },
        )
        assert created_grant.status_code == 200

        monkeypatch.setattr(
            "app.services.fixation_admission_service.calculate_cbs_indexation",
            lambda **_kwargs: _success(),
        )
        payload = owner_payload("cbs_system_calculation_required")
        saved = client.post("/api/fixation/save", json={"client_id": owner, "input_data": payload})
        assert saved.status_code == 200 and saved.json()["status"] == "success"
        run_id = saved.json()["run_id"]
        payload_before_mutation = copy.deepcopy(payload)

        detail = client.get(f"/api/clients/{owner}/fixation/runs/{run_id}")
        cross_client = client.get(f"/api/clients/{other}/fixation/runs/{run_id}")
        assert detail.status_code == 200
        assert cross_client.status_code == 404
        snapshot_grant = detail.json()["input_snapshot"]["grants"][0]
        assert payload_before_mutation["grants"] == []
        assert snapshot_grant["nominal_amount"] == "1000.00"
        assert snapshot_grant["asserted_indexed_amount"] is None
        assert snapshot_grant["system_calculated_amount"] == "1234.57"
        assert snapshot_grant["selected_calculation_amount"] == "1234.57"
        assert snapshot_grant["cbs_response_evidence"]["raw_to_value"] == "1234.5678"
        assert snapshot_grant["base_date_source"] == "grant_date"
        assert snapshot_grant["cpi_code"] == "120010"

        monkeypatch.setattr(
            "app.services.fixation_admission_service.calculate_cbs_indexation",
            lambda **_kwargs: _failure(),
        )
        calculated_failure = client.post(
            f"/api/clients/{owner}/fixation/calculate",
            json=owner_payload("cbs_system_calculation_required"),
        )
        assert calculated_failure.status_code == 200
        assert calculated_failure.json()["status"] == "calculation_failed"
        failed = client.post(
            "/api/fixation/save",
            json={
                "client_id": owner,
                "input_data": owner_payload(
                    "cbs_system_calculation_required"
                ),
            },
        )
        assert failed.status_code == 200 and failed.json()["status"] == "calculation_failed"
        failed_detail = client.get(
            f"/api/clients/{owner}/fixation/runs/{failed.json()['run_id']}"
        ).json()
        assert failed_detail["result"] is None
        assert failed_detail["audit_rows"] == []
        assert failed_detail["input_snapshot"]["grants"][0]["indexation_failure_evidence"][
            "failure_category"
        ] == "timeout"
        assert client.get(f"/api/clients/{other}/fixation/runs/{failed.json()['run_id']}").status_code == 404
        assert client.get(f"/api/clients/{other}").status_code == 200
        assert client.get(f"/api/clients/{other}/fixation/history").json() == []
        assert client.get(f"/api/clients/{other}/fixation/latest").json() == {"result": None}
        owner_history = client.get(f"/api/clients/{owner}/fixation/history").json()
        assert any(run["status"] == "calculation_failed" for run in owner_history)

        for non_finite_value in ("NaN", "Infinity", "-Infinity"):
            calls = 0

            def handler(_request: httpx.Request, *, value=non_finite_value) -> httpx.Response:
                nonlocal calls
                calls += 1
                return httpx.Response(200, json={"answer": {"to_value": value}})

            with httpx.Client(transport=httpx.MockTransport(handler)) as cbs_client:
                monkeypatch.setattr(
                    "app.services.fixation_admission_service.calculate_cbs_indexation",
                    lambda *, _client=cbs_client, **kwargs: calculate_cbs_indexation(
                        client=_client,
                        **kwargs,
                    ),
                )
                non_finite = client.post(
                    "/api/fixation/save",
                    json={
                        "client_id": owner,
                            "input_data": owner_payload(
                                "cbs_system_calculation_required"
                            ),
                    },
                )

            assert non_finite.status_code == 200
            assert non_finite.json()["status"] == "calculation_failed"
            assert calls == 1
            non_finite_detail = client.get(
                f"/api/clients/{owner}/fixation/runs/{non_finite.json()['run_id']}"
            ).json()
            assert non_finite_detail["result"] is None
            assert non_finite_detail["audit_rows"] == []
            persisted_failure = non_finite_detail["input_snapshot"]["grants"][0]
            assert persisted_failure["cbs_response_evidence"] is None
            assert persisted_failure["indexation_failure_evidence"]["failure_category"] == "malformed_response"
            assert persisted_failure["indexation_failure_evidence"]["malformed_response"] is True

        monkeypatch.setattr(
            "app.services.fixation_admission_service.calculate_cbs_indexation",
            lambda **_kwargs: _failure(unsupported=True),
        )
        unsupported = client.post(
            "/api/fixation/save",
            json={
                "client_id": owner,
                "input_data": owner_payload(
                    "cbs_system_calculation_required"
                ),
            },
        )
        assert unsupported.status_code == 200
        assert unsupported.json()["status"] == "unsupported_calculation"
    finally:
        app.dependency_overrides.clear()
