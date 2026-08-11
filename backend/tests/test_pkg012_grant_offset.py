from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.engines.fixation_engine import _calculate_formula_non_authoritative
from app.main import app
from app.schemas.fixation_contracts import FixationInput
from app.schemas.cbs_indexation import (
    CbsIndexationRequestEvidence,
    CbsIndexationResponseEvidence,
    CbsIndexationSuccess,
)
from app.services import fixation_admission_service
from tests.pkg004d_test_support import resolver_payload, seed_eligibility_revision
from tests.test_phase9_api import _build_client, _create_client


def _payload(*, eligibility: date = date(2025, 1, 1), grants: list[dict] | None = None) -> dict:
    return {
        "calculation_id": "pkg012",
        "calculation_version": "pkg-012-v1",
        "eligibility_date": eligibility,
        "eligibility_year": eligibility.year,
        "monthly_cap": 1000,
        "exemption_percentage": 0.5,
        "capital_multiplier": 180,
        "grant_impact_multiplier": 1.35,
        "grants": grants or [],
        "future_grant_reserved": 0,
        "actual_capitalizations": [],
        "idf": None,
    }


def _grant(
    *,
    eligibility: date = date(2025, 1, 1),
    receipt: date = date(2020, 1, 1),
    start: date | None = None,
    end: date | None = None,
    indexed: float = 100000,
    grant_id: str = "G-1",
) -> dict:
    return {
        "grant_id": grant_id,
        "indexed_amount": indexed,
        "grant_date": receipt,
        "work_start_date": start or eligibility - timedelta(days=11_688),
        "work_end_date": end or eligibility,
    }


def _calculate(grants: list[dict], eligibility: date = date(2025, 1, 1)):
    return _calculate_formula_non_authoritative(FixationInput(**_payload(eligibility=eligibility, grants=grants)))


def test_zero_grants_produces_zero_handoff() -> None:
    result = _calculate([])
    assert result.grant_impact_total == 0
    assert result.grant_offset_handoff["aggregate_grant_offset"] == 0
    assert result.grant_offset_handoff["per_grant_breakdown"] == []


def test_exact_fifteen_year_boundary_is_included() -> None:
    eligibility = date(2026, 1, 1)
    result = _calculate([_grant(eligibility=eligibility, receipt=date(2011, 1, 1))], eligibility)
    grant = result.grant_results[0]
    assert grant.years_difference == 15
    assert grant.relevant is True
    assert grant.impact_amount == 135000


def test_more_than_fifteen_years_is_excluded() -> None:
    eligibility = date(2026, 1, 2)
    result = _calculate([_grant(eligibility=eligibility, receipt=date(2011, 1, 1))], eligibility)
    assert result.grant_results[0].relevant is False
    assert result.grant_results[0].impact_amount == 0


def test_golden_ratio_and_rounding_sequence() -> None:
    eligibility = date(2025, 1, 1)
    result = _calculate([
        _grant(
            eligibility=eligibility,
            start=eligibility - timedelta(days=23_376),
            end=eligibility,
        )
    ])
    grant = result.grant_results[0]
    assert grant.ratio == 0.5
    assert grant.indexed_amount == 100000
    assert grant.limited_indexed_amount == 50000
    assert grant.impact_amount == 67500


@pytest.mark.parametrize(
    ("start_delta", "end_delta", "expected_ratio"),
    [
        (1000, 0, 1.0),
        (11_688, 0, 1.0),
        (23_376, 0, 0.5),
        (23_376, 5_844, 1 / 3),
        (23_376, 11_688, 0.0),
        (11_688, -100, 11_688 / 11_788),
    ],
)
def test_32_year_overlap_uses_full_employment_denominator(
    start_delta: int, end_delta: int, expected_ratio: float
) -> None:
    eligibility = date(2025, 1, 1)
    result = _calculate([
        _grant(
            eligibility=eligibility,
            start=eligibility - timedelta(days=start_delta),
            end=eligibility - timedelta(days=end_delta),
        )
    ])
    assert result.grant_results[0].ratio == pytest.approx(expected_ratio)


def test_multiple_grants_round_before_aggregation_and_zero_is_valid() -> None:
    first = _grant(indexed=100000.005, grant_id="G-1")
    second = _grant(indexed=0, grant_id="G-2")
    result = _calculate([first, second])
    assert [grant.grant_id for grant in result.grant_results] == ["G-1", "G-2"]
    assert result.grant_results[1].impact_amount == 0
    assert result.grant_impact_total == sum(grant.impact_amount for grant in result.grant_results)


@pytest.mark.parametrize("amount", [-1, "NaN", "Infinity", "bad"])
def test_invalid_grant_amount_is_rejected(amount) -> None:
    with pytest.raises(ValueError):
        FixationInput(**_payload(grants=[_grant(indexed=amount)]))


def test_six_field_crud_and_foreign_id_non_leakage(tmp_path) -> None:
    client, _, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client)["client_id"]
        other_id = _create_client(client, id_number="1002")["client_id"]
        payload = {
            "employer_name": "Employer",
            "employer_withholding_file_number": "12345",
            "employment_start_date": "2010-01-01",
            "employment_end_date": "2020-01-01",
            "grant_receipt_date": "2020-02-01",
            "exempt_grant_amount": "0",
        }
        created = client.post(f"/api/clients/{client_id}/grants", json=payload)
        assert created.status_code == 200
        body = created.json()
        assert set(body) == {"grant_id", "client_id", *payload.keys()}
        assert body["employer_withholding_file_number"] == "12345"
        grant_id = body["grant_id"]

        foreign = client.put(f"/api/clients/{other_id}/grants/{grant_id}", json=payload)
        missing = client.put(f"/api/clients/{other_id}/grants/missing", json=payload)
        assert (foreign.status_code, foreign.json()) == (missing.status_code, missing.json())

        assert client.delete(f"/api/clients/{client_id}/grants/{grant_id}").status_code == 200
        assert client.get(f"/api/clients/{client_id}/grants").json() == []
    finally:
        app.dependency_overrides.clear()


def test_six_field_request_rejects_indexed_amount_and_missing_required_fields(tmp_path) -> None:
    client, _, _ = _build_client(tmp_path)
    try:
        client_id = _create_client(client)["client_id"]
        response = client.post(
            f"/api/clients/{client_id}/grants",
            json={"employer_name": "Employer", "indexed_amount": 100},
        )
        assert response.status_code == 422
        paths = {tuple(item["loc"]) for item in response.json()["detail"]}
        assert ("body", "indexed_amount") in paths
        assert ("body", "employer_withholding_file_number") in paths
        assert ("body", "exempt_grant_amount") in paths
    finally:
        app.dependency_overrides.clear()


def test_direct_calculation_uses_persisted_grants_and_freezes_saved_evidence(
    tmp_path, monkeypatch
) -> None:
    client, session_local, _ = _build_client(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def fake_cbs(*, amount, grant_date, work_end_date, eligibility_date):
        assert amount == Decimal("100000.00")
        assert grant_date == date(2020, 1, 1)
        request = CbsIndexationRequestEvidence(
            amount=amount,
            resolved_base_date=grant_date,
            base_date_source="grant_date",
            target_date=eligibility_date,
            calculation_timestamp=now,
        )
        return CbsIndexationSuccess(
            request=request,
            response=CbsIndexationResponseEvidence(
                raw_to_value=Decimal("100000"),
                missing_optional_fields=[],
                calculation_timestamp=now,
                response_status=200,
            ),
        )

    monkeypatch.setattr(fixation_admission_service, "calculate_cbs_indexation", fake_cbs)
    try:
        client_id = _create_client(client)["client_id"]
        with session_local() as db:
            revision_id, _ = seed_eligibility_revision(
                db, client_id=client_id, eligibility_dates=("2025-01-01",)
            )
            db.commit()
        grant_payload = {
            "employer_name": "Employer",
            "employer_withholding_file_number": "WF-1",
            "employment_start_date": (date(2025, 1, 1) - timedelta(days=23_376)).isoformat(),
            "employment_end_date": "2025-01-01",
            "grant_receipt_date": "2020-01-01",
            "exempt_grant_amount": "100000",
        }
        created = client.post(f"/api/clients/{client_id}/grants", json=grant_payload)
        grant_id = created.json()["grant_id"]
        payload = resolver_payload(
            {
                "calculation_version": "pkg-012-v1",
                "eligibility_date": "2025-01-01",
                "eligibility_year": 2025,
                "parameter_set": {
                    "parameter_set_id": "params-2025",
                    "client_id": client_id,
                    "tax_year": 2025,
                    "values": {
                        "monthly_cap": 1000,
                        "exemption_percentage": 0.5,
                        "capital_multiplier": 180,
                        "grant_impact_multiplier": 1.35,
                    },
                    "source_basis": "accepted test context",
                    "status": "accepted",
                    "accepted_for_use": True,
                    "accepted_by": "planner",
                    "decision_timestamp": now.isoformat(),
                },
                "grants_collection_state": "confirmed_none",
                "grants": [],
                "future_grant_reservation": None,
                "actual_capitalizations_collection_state": "confirmed_none",
                "actual_capitalizations": [],
                "idf": None,
                "metadata": {"grant_contract": "pkg-012-direct-v1"},
            },
            revision_id=revision_id,
        )
        saved = client.post(
            "/api/fixation/save", json={"client_id": client_id, "input_data": payload}
        )
        assert saved.status_code == 200
        run_id = saved.json()["run_id"]
        detail_before = client.get(
            f"/api/clients/{client_id}/fixation/runs/{run_id}"
        ).json()
        result = detail_before["result"]
        assert result["grant_results"][0]["grant_id"] == grant_id
        assert result["grant_results"][0]["ratio"] == pytest.approx(0.5)
        assert result["grant_results"][0]["impact_amount"] == 67500
        assert result["grant_results"][0]["cbs_response_evidence"]["raw_to_value"] == "100000"

        changed = dict(grant_payload, exempt_grant_amount="1")
        assert client.put(f"/api/clients/{client_id}/grants/{grant_id}", json=changed).status_code == 200
        assert client.delete(f"/api/clients/{client_id}/grants/{grant_id}").status_code == 200
        assert client.get(f"/api/clients/{client_id}/fixation/runs/{run_id}").json() == detail_before
    finally:
        app.dependency_overrides.clear()
