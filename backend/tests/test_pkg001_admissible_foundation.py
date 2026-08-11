from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.engines.fixation_engine as fixation_engine
import app.services.fixation_service as fixation_service
from app.db.base import Base, load_all_models
from app.db.session import get_db
from app.main import app
from app.models.client import Client
from app.models.fixation_audit_row import FixationAuditRow
from app.models.fixation_input_snapshot import FixationInputSnapshot
from app.schemas.fixation_contracts import FixationInput
from app.services.fixation_admission_service import parse_and_admit_fixation_payload
from app.services.fixation_service import calculate_fixation_payload
from tests.pkg004d_test_support import resolver_payload, seed_eligibility_revision


load_all_models()
_UNIT_ENGINE = create_engine("sqlite:///:memory:")
Base.metadata.create_all(_UNIT_ENGINE)
_UNIT_SESSION = sessionmaker(bind=_UNIT_ENGINE)()
_UNIT_SESSION.add_all(
    [
        Client(client_id=1, display_name="Client 1", id_number="pkg001-client-1"),
        Client(client_id=2, display_name="Client 2", id_number="pkg001-client-2"),
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


def _legacy_payload(*, client_id: int = 1) -> dict:
    return {
        "calculation_id": "pkg-001",
        "calculation_version": "pkg-001-v1",
        "eligibility_date": "2026-01-01",
        "eligibility_year": 2026,
        "upstream_context": {
            "profile_id": "m07-1",
            "client_id": client_id,
            "state": "qualified",
        },
        "parameter_set": {
            "parameter_set_id": "params-2026-accepted",
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
            "source_basis": "accepted test evidence",
            "status": "accepted",
            "accepted_for_use": True,
            "accepted_by": "planner-1",
            "decision_timestamp": "2026-01-01T08:00:00Z",
        },
        "grants_collection_state": "items_recorded",
        "grants": [
            {
                "grant_id": "grant-1",
                "client_id": client_id,
                "item_type": "severance_grant",
                "indexation_mode": "asserted_indexed_amount",
                "indexed_amount": 10000.0,
                "grant_date": "2020-01-01",
                "work_start_date": "2010-01-01",
                "work_end_date": "2020-01-01",
                "source_basis": "grant source",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "planner-1",
                "decision_timestamp": "2026-01-01T08:01:00Z",
            }
        ],
        "future_grant_reservation": {
            "amount": 500.0,
            "source_basis": "reserve basis",
            "status": "reviewed",
            "accepted_for_use": True,
            "actor": "planner-1",
            "decision_timestamp": "2026-01-01T08:02:00Z",
        },
        "actual_capitalizations_collection_state": "items_recorded",
        "actual_capitalizations": [
            {
                "capitalization_id": "cap-1",
                "item_type": "actual_capitalization",
                "amount": 250.0,
                "capitalization_date": "2025-01-01",
                "recorded_meaning": "historical actual capitalization",
                "source_basis": "capitalization source",
                "status": "reviewed",
                "accepted_for_use": True,
                "inclusion_decision": "include",
                "support_status": "supported",
                "conflict_indicator": False,
                "actor": "planner-1",
                "decision_timestamp": "2026-01-01T08:03:00Z",
            }
        ],
        "idf": None,
        "metadata": {"source_data_version_label": "source-v1"},
    }


def _payload(*, client_id: int = 1) -> dict:
    return resolver_payload(
        _legacy_payload(client_id=client_id),
        revision_id=_UNIT_REVISIONS[client_id],
    )


def _error_paths(payload: dict, *, client_id: int | None = None) -> set[str]:
    _, _, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=client_id
        or int(payload.get("parameter_set", {}).get("client_id", 1)),
        db_session=_UNIT_SESSION,
    )
    return {error.path for error in errors}


def test_parameter_set_is_mandatory_accepted_complete_and_applicable() -> None:
    missing_set = _payload()
    del missing_set["parameter_set"]
    assert "parameter_set" in _error_paths(missing_set)

    unaccepted = _payload()
    unaccepted["parameter_set"]["status"] = "rejected"
    unaccepted["parameter_set"]["accepted_for_use"] = False
    assert "parameter_set.accepted_for_use" in _error_paths(unaccepted)

    missing_required_value = _payload()
    del missing_required_value["parameter_set"]["values"]["grant_impact_multiplier"]
    assert "parameter_set.values.grant_impact_multiplier" in _error_paths(missing_required_value)

    wrong_year = _payload()
    wrong_year["parameter_set"]["tax_year"] = 2025
    assert "parameter_set.tax_year" in _error_paths(wrong_year)

    stale = _payload()
    stale["parameter_set"]["effective_from"] = "2025-01-01"
    stale["parameter_set"]["effective_to"] = "2025-12-31"
    assert "parameter_set.effective_to" in _error_paths(stale)


def test_parameter_status_vocabulary_and_effective_period_consistency() -> None:
    accepted = _payload()
    assert _error_paths(accepted) == set()

    no_period = _payload()
    no_period["parameter_set"]["effective_from"] = None
    no_period["parameter_set"]["effective_to"] = None
    assert _error_paths(no_period) == set()

    rejected_as_accepted = _payload()
    rejected_as_accepted["parameter_set"]["status"] = "rejected"
    assert "parameter_set" in _error_paths(rejected_as_accepted)

    accepted_as_rejected = _payload()
    accepted_as_rejected["parameter_set"]["accepted_for_use"] = False
    assert "parameter_set" in _error_paths(accepted_as_rejected)

    uncontrolled_status = _payload()
    uncontrolled_status["parameter_set"]["status"] = "reviewed"
    assert "parameter_set.status" in _error_paths(uncontrolled_status)

    future = _payload()
    future["parameter_set"]["effective_from"] = "2026-01-02"
    assert "parameter_set.effective_from" in _error_paths(future)


def test_only_admitted_values_reach_engine_and_result_is_deterministic() -> None:
    payload = _payload()
    before = copy.deepcopy(payload)

    first = calculate_fixation_payload(
        payload, client_id=1, db_session=_UNIT_SESSION
    )
    second = calculate_fixation_payload(
        payload, client_id=1, db_session=_UNIT_SESSION
    )

    assert first.status == "success"
    assert first.model_dump() == second.model_dump()
    assert payload == before
    assert first.monthly_cap == payload["parameter_set"]["values"]["monthly_cap"]
    assert first.future_grant_impact == 675.0


def _plain_formula_input(*, with_idf: bool = False) -> FixationInput:
    idf = None
    if with_idf:
        idf = {
            "idf_id": "idf-direct",
            "reduction_amount": 1000.0,
            "original_commutation_percent": 25.0,
            "current_commutation_percent": 20.0,
            "commutation_date": "2025-01-01",
            "promoter_age_date": "2027-01-01",
        }
    return FixationInput(
        calculation_id="direct",
        calculation_version="test",
        eligibility_date="2026-01-01",
        eligibility_year=2026,
        monthly_cap=1000.0,
        exemption_percentage=0.5,
        capital_multiplier=180.0,
        grant_impact_multiplier=1.35,
        grants=[],
        future_grant_reserved=0.0,
        actual_capitalizations=[],
        idf=idf,
    )


def test_public_engine_rejects_plain_and_idf_inputs_and_has_no_payload_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formula_called = False

    def fail_if_called(_input_data):
        nonlocal formula_called
        formula_called = True
        raise AssertionError("formula must not run")

    monkeypatch.setattr(fixation_engine, "_calculate_formula_non_authoritative", fail_if_called)

    with pytest.raises(TypeError, match="AdmittedFixationInput"):
        fixation_engine.calculate_fixation(_plain_formula_input())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="AdmittedFixationInput"):
        fixation_engine.calculate_fixation(_plain_formula_input(with_idf=True))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="cannot be admitted"):
        fixation_engine._admit_fixation_input(_plain_formula_input(with_idf=True))

    assert not hasattr(fixation_engine, "calculate_fixation_from_payload")
    assert formula_called is False


def test_legacy_payload_cannot_reach_application_formula(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    formula_called = False

    def fail_if_called(_input_data):
        nonlocal formula_called
        formula_called = True
        raise AssertionError("formula must not run")

    monkeypatch.setattr(fixation_engine, "_calculate_formula_non_authoritative", fail_if_called)
    legacy_payload = _plain_formula_input().model_dump(mode="json")

    result = calculate_fixation_payload(
        legacy_payload,
        client_id=1,
        db_session=_UNIT_SESSION,
    )

    assert result.status == "validation_failed"
    assert formula_called is False


@pytest.mark.parametrize(
    "mutate_payload",
    [
        lambda payload: payload.pop("parameter_set"),
        lambda payload: payload.update(
            upstream_context={"state": "blocked"}
        ),
        lambda payload: payload["grants"][0].update(accepted_for_use=False),
        lambda payload: payload["actual_capitalizations"][0].update(accepted_for_use=False),
        lambda payload: payload["future_grant_reservation"].update(accepted_for_use=False),
    ],
    ids=[
        "parameter-set",
        "legacy-m07-context",
        "grant",
        "capitalization",
        "future-reserve",
    ],
)
def test_missing_admissibility_evidence_cannot_reach_formula(
    monkeypatch: pytest.MonkeyPatch,
    mutate_payload,
) -> None:
    payload = _payload()
    mutate_payload(payload)

    def fail_if_called(_input_data):
        raise AssertionError("formula must not run")

    monkeypatch.setattr(fixation_service, "calculate_fixation_engine", fail_if_called)

    result = calculate_fixation_payload(
        payload, client_id=1, db_session=_UNIT_SESSION
    )

    assert result.status == "validation_failed"


def test_reviewed_zero_and_preserved_exclusion_decisions() -> None:
    payload = _payload()
    payload["grants"][0]["inclusion_decision"] = "exclude"
    payload["actual_capitalizations"][0]["inclusion_decision"] = "exclude"
    payload["future_grant_reservation"] = None

    context, engine_input, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
    )
    result = calculate_fixation_payload(
        payload, client_id=1, db_session=_UNIT_SESSION
    )

    assert errors == []
    assert context is not None and context.grants[0].inclusion_decision == "exclude"
    assert engine_input is not None
    engine_result = fixation_engine.calculate_fixation(engine_input)
    assert engine_result.grant_results == []
    assert engine_result.actual_capitalization_results == []
    assert result.status == "success"
    assert result.total_impact == 0.0


def test_conflict_decision_is_used_without_system_source_ranking() -> None:
    payload = _payload()
    grant = payload["grants"][0]
    grant["conflict_indicator"] = True
    grant["accepted_value"] = 1234.0

    context, engine_input, errors, _ = parse_and_admit_fixation_payload(
        payload,
        client_id=1,
        db_session=_UNIT_SESSION,
    )

    assert errors == []
    assert context is not None and context.grants[0].conflict_indicator is True
    assert engine_input is not None
    engine_result = fixation_engine.calculate_fixation(engine_input)
    assert engine_result.grant_results[0].indexed_amount == 1234.0


def _warning_reviewed_payload() -> dict:
    payload = _payload()
    payload["upstream_context"] = {
        "profile_id": "m07-warning-1",
        "client_id": 1,
        "state": "warning_reviewed",
        "warnings": [{"code": "M07-W-1", "message": "review required"}],
        "review_reason": "planner reviewed the recorded warning",
        "reviewed_by": "planner-1",
        "review_timestamp": "2026-01-01T07:59:00Z",
        "qualification_trace_id": "trace-m07-1",
    }
    return payload


@pytest.mark.parametrize("missing_field", ["warnings", "review_reason", "reviewed_by", "review_timestamp"])
def test_warning_reviewed_requires_complete_review_evidence(missing_field: str) -> None:
    payload = _warning_reviewed_payload()
    del payload["upstream_context"][missing_field]

    assert "upstream_context" in _error_paths(payload)


def test_qualified_context_does_not_require_warning_review_evidence() -> None:
    assert _error_paths(_payload()) == set()


def test_acceptance_evidence_unsupported_inputs_idf_and_m07_gate_block_engine() -> None:
    unaccepted_grant = _payload()
    unaccepted_grant["grants"][0]["accepted_for_use"] = False
    assert "grants[0].accepted_for_use" in _error_paths(unaccepted_grant)

    unsupported_grant = _payload()
    unsupported_grant["grants"][0]["support_status"] = "unsupported"
    assert "grants[0].support_status" in _error_paths(unsupported_grant)

    missing_support_decision = _payload()
    del missing_support_decision["grants"][0]["support_status"]
    assert "grants[0].support_status" in _error_paths(missing_support_decision)

    unaccepted_reserve = _payload()
    unaccepted_reserve["future_grant_reservation"]["accepted_for_use"] = False
    assert "future_grant_reservation.accepted_for_use" in _error_paths(unaccepted_reserve)

    unaccepted_cap = _payload()
    unaccepted_cap["actual_capitalizations"][0]["accepted_for_use"] = False
    assert "actual_capitalizations[0].accepted_for_use" in _error_paths(unaccepted_cap)

    blocked_m07 = _payload()
    blocked_m07["upstream_context"] = {"state": "blocked"}
    assert "upstream_context" in _error_paths(blocked_m07)

    idf = _payload()
    idf["idf"] = {
        "idf_id": "idf-1",
        "reduction_amount": 1000.0,
        "original_commutation_percent": 25.0,
        "current_commutation_percent": 20.0,
        "commutation_date": "2025-01-01",
        "promoter_age_date": "2027-01-01",
    }
    result = calculate_fixation_payload(
        idf, client_id=1, db_session=_UNIT_SESSION
    )
    assert result.status == "requires_special_handling"
    assert result.validation_errors[0].path == "idf"


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


def test_saved_manifest_is_immutable_and_run_access_is_client_isolated(tmp_path: Path) -> None:
    db_path = tmp_path / "pkg001.db"
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
            json={"full_name": "Owner", "id_number": "pkg-owner", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        other = client.post(
            "/api/clients",
            json={"full_name": "Other", "id_number": "pkg-other", "birth_date": "1970-01-01"},
        ).json()["client_id"]
        with session_local() as session:
            owner_revision, _ = seed_eligibility_revision(
                session, client_id=owner
            )
            other_revision, _ = seed_eligibility_revision(
                session, client_id=other
            )
            session.commit()

        payload = resolver_payload(
            _legacy_payload(client_id=owner),
            revision_id=owner_revision,
        )
        payload["grants_collection_state"] = "confirmed_none"
        payload["grants"] = []
        saved = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": payload},
        )
        assert saved.status_code == 200
        assert saved.json()["status"] == "success"
        run_id = saved.json()["run_id"]

        payload["parameter_set"]["values"]["monthly_cap"] = 999999.0
        owner_detail = client.get(f"/api/clients/{owner}/fixation/runs/{run_id}")
        other_detail = client.get(f"/api/clients/{other}/fixation/runs/{run_id}")
        assert owner_detail.status_code == 200
        assert other_detail.status_code == 404
        assert owner_detail.json()["input_snapshot"]["parameter_set"]["values"]["monthly_cap"] == 1000.0
        assert owner_detail.json()["input_snapshot"]["grants"] == []

        cross_client_calculation = client.post(
            f"/api/clients/{other}/fixation/calculate",
            json=resolver_payload(
                _legacy_payload(client_id=owner),
                revision_id=owner_revision,
            ),
        )
        assert cross_client_calculation.status_code == 200
        assert cross_client_calculation.json()["status"] == "validation_failed"
        assert {
            error["path"] for error in cross_client_calculation.json()["validation_errors"]
        } == {"parameter_set.client_id"}

        idf_payload = resolver_payload(
            _legacy_payload(client_id=owner),
            revision_id=owner_revision,
        )
        idf_payload["idf"] = {
            "idf_id": "idf-save",
            "reduction_amount": 1000.0,
            "original_commutation_percent": 25.0,
            "current_commutation_percent": 20.0,
            "commutation_date": "2025-01-01",
            "promoter_age_date": "2027-01-01",
        }
        idf_saved = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": idf_payload},
        )
        assert idf_saved.status_code == 200
        assert idf_saved.json()["status"] == "requires_special_handling"
        idf_detail = client.get(
            f"/api/clients/{owner}/fixation/runs/{idf_saved.json()['run_id']}"
        ).json()
        assert idf_detail["run"]["status"] == "requires_special_handling"
        assert idf_detail["result"] is None
        assert idf_detail["audit_rows"] == []

        idf_calculated = client.post(
            f"/api/clients/{owner}/fixation/calculate",
            json=idf_payload,
        )
        assert idf_calculated.status_code == 200
        assert idf_calculated.json()["status"] == "requires_special_handling"

        legacy_context_payload = _legacy_payload(client_id=owner)
        legacy_saved = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": legacy_context_payload},
        )
        assert legacy_saved.status_code == 200
        assert legacy_saved.json()["status"] == "validation_failed"

        with session_local() as session:
            snapshot = session.scalar(
                select(FixationInputSnapshot).where(FixationInputSnapshot.fixation_run_id == run_id)
            )
            assert snapshot is not None
            assert snapshot.input_payload["parameter_set"]["parameter_set_id"] == "params-2026-accepted"
            idf_audit_rows = session.scalars(
                select(FixationAuditRow).where(
                    FixationAuditRow.fixation_run_id == idf_saved.json()["run_id"]
                )
            ).all()
            assert idf_audit_rows == []

        mismatched = resolver_payload(
            _legacy_payload(client_id=other),
            revision_id=other_revision,
        )
        rejected = client.post(
            "/api/fixation/save",
            json={"client_id": owner, "input_data": mismatched},
        )
        assert rejected.status_code == 200
        assert rejected.json()["status"] == "validation_failed"
    finally:
        app.dependency_overrides.clear()
