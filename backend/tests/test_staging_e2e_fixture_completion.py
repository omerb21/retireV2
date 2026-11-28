from __future__ import annotations

import base64
from pathlib import Path
import sys
from typing import Any

import httpx
import pytest

from app.services.scenario_stage6_single_pension_estimate_service import _seal


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import staging_e2e_fixture_completion as subject  # noqa: E402


CSRF = base64.urlsafe_b64encode(b"F" * 32).decode().rstrip("=")
PASSWORD = "never-print-fixture-password"


def _response(status: int, body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        json=body if body is not None else {},
        request=httpx.Request("GET", subject.STAGING_ORIGIN),
    )


def _decision() -> dict[str, Any]:
    return {
        "decision_id": subject.DECISION_ID,
        "source_product_id": subject.PRODUCT_ID,
        "source_component_id": subject.COMPONENT_ID,
        "component_code": subject.COMPONENT_CODE,
        "amount": subject.AMOUNT,
        "action": "pension",
        "effective_date": subject.EFFECTIVE_DATE,
        "validation_state": "unverified",
        "product_version_at_review": 1,
        "source_fingerprint_at_review": "a" * 64,
    }


def _scenario(version: int) -> dict[str, Any]:
    return {
        "client_id": subject.CLIENT_ID,
        "scenario_id": subject.SCENARIO_ID,
        "name": subject.SCENARIO_NAME,
        "status": "draft",
        "version": version,
        "decisions": [_decision()],
    }


def _ready_result(version: int, *, salt: str = "") -> dict[str, Any]:
    hashes = {
        "professional_admission_fingerprint": "1" * 64,
        "planning_calculation_input_fingerprint": "2" * 64,
        "monthly_basis_semantic_fingerprint": "3" * 64,
        "monthly_basis_source_fingerprint": "4" * 64,
        "temporal_semantic_fingerprint": "5" * 64,
        "temporal_source_fingerprint": "6" * 64,
        "pte_source_execution_fingerprint": "7" * 64,
        "pte_source_result_fingerprint": "8" * 64,
    }
    return _seal({
        "schema_version": "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1",
        "client_id": subject.CLIENT_ID,
        "scenario_id": subject.SCENARIO_ID,
        "scenario_version": version,
        "decision_id": subject.DECISION_ID,
        "source_id": f"scenario-decision:{subject.SCENARIO_ID}:{subject.DECISION_ID}",
        "result_state": "RESULT_READY",
        "execution_allowed": True,
        "blockers": [],
        "coefficient_provenance": {
            "source_level": "MANUAL_PROFESSIONAL_OVERRIDE",
            "factor_value": subject.FACTOR_VALUE,
            "factor_evidence_type": subject.FACTOR_EVIDENCE_TYPE,
            "factor_evidence_reference": subject.FACTOR_EVIDENCE_REFERENCE,
            "payout_option_name": subject.SYNTHETIC_OPTION_NAME,
            "admission_revision": 1,
        },
        **hashes,
        "monthly_estimate_gross_ils": "350.00",
        "retirement_target_date": subject.RETIREMENT_TARGET_DATE,
        "statement_date": subject.PLANNING_BASE_DATE,
    })


class FakeClient:
    def __init__(self, *, price_target_ready: bool = False) -> None:
        self.case_written = False
        self.base_written = False
        self.target_written = False
        self.election_written = False
        self.factor_written = False
        self.price_written = False
        self.scenario_version = subject.INITIAL_SCENARIO_VERSION
        self.planning_version = 0
        self.calls: list[tuple[str, str, dict | None]] = []
        self.failure: tuple[str, str, int, str] | None = None
        self.network_failure: tuple[str, str] | None = None
        self.logout_status = 204
        self.price_target_ready = price_target_ready
        self.gross_salt = ""

    def _record(self, method: str, path: str, body: dict | None = None) -> None:
        self.calls.append((method, path, body))
        if self.network_failure == (method, path):
            raise httpx.ConnectError("secret transport detail")

    def post(self, path: str, **kwargs) -> httpx.Response:
        self._record("POST", path, kwargs.get("json"))
        if path == "/api/auth/login":
            return _response(200, {"authenticated": True, "csrf_token": CSRF})
        if path == "/api/auth/logout":
            return _response(self.logout_status)
        return self.request("POST", path, **kwargs)

    def get(self, path: str, **_kwargs) -> httpx.Response:
        self._record("GET", path)
        if path == "/api/auth/session":
            return _response(200, {"authenticated": True, "csrf_token": CSRF})
        if path == subject.SCENARIO_PATH:
            return _response(200, _scenario(self.scenario_version))
        if path == subject.PRODUCT_PATH:
            return _response(200, {
                "client_id": subject.CLIENT_ID,
                "product_id": subject.PRODUCT_ID,
                "version": 1,
                "statement_date": subject.PLANNING_BASE_DATE,
                "conversion_components": [{
                    "component_id": subject.COMPONENT_ID,
                    "component_code": subject.COMPONENT_CODE,
                    "balance": subject.SOURCE_BALANCE,
                }],
            })
        if path == subject.CLIENT_PATH:
            return _response(200, {
                "client_id": subject.CLIENT_ID,
                "m01_case": {
                    "client_id": subject.CLIENT_ID,
                    "display_name": "SYNTHETIC CASE 7",
                    "id_number": "SYNTHETIC-7",
                    "birth_date": subject.BIRTH_DATE if self.case_written else None,
                    "gender": subject.GENDER if self.case_written else None,
                    "employment_status": None,
                    "planned_retirement_date": (
                        subject.RETIREMENT_TARGET_DATE if self.case_written else None
                    ),
                    "planned_retirement_age": None,
                },
            })
        if path == subject.PLANNING_PATH:
            return _response(200, self._planning())
        if path == subject.ELECTIONS_PATH:
            return _response(200, {
                "elections": [subject._election()] if self.election_written else [],
            })
        if path == subject.FACTOR_CURSOR_PATH:
            return _response(200, {
                "scenario_version": self.scenario_version,
                "latest_admission_revision": 0,
                "authority_state": "NOT_EVALUATED",
            })
        if path == subject.GROSS_PATH:
            if not self.factor_written:
                raise AssertionError("gross read before factor admission")
            return _response(200, _ready_result(self.scenario_version, salt=self.gross_salt))
        if path == subject.TARGET_PATH:
            return _response(200, {
                "client_id": subject.CLIENT_ID,
                "target_ready": self.price_target_ready,
                "retirement_target_date": (
                    subject.RETIREMENT_TARGET_DATE if self.price_target_ready else None
                ),
                "target_result_fingerprint": "b" * 64,
            })
        if path == subject.CASHFLOW_PATH:
            return _response(200, {
                "sources": [{
                    "source_id": (
                        f"scenario-decision:{subject.SCENARIO_ID}:{subject.DECISION_ID}"
                    ),
                    "source_kind": "CALCULATED_PENSION",
                    "source_state": "READY",
                    "authority_fingerprint": "c" * 64,
                }],
            })
        raise AssertionError(f"unexpected GET {path}")

    def _planning(self) -> dict[str, Any]:
        return {
            "client_id": subject.CLIENT_ID,
            "decision_version": self.planning_version,
            "planning_base_date": (
                subject.PLANNING_BASE_DATE if self.base_written else None
            ),
            "retirement_target": {
                "retirement_target_date": (
                    subject.RETIREMENT_TARGET_DATE if self.target_written else None
                ),
                "retirement_target_ready": self.base_written and self.target_written,
                "current_reference_fingerprint": "d" * 64,
            },
        }

    def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        body = kwargs.get("json")
        self._record(method, path, body)
        if self.failure and self.failure[:2] == (method, path):
            _, _, status, code = self.failure
            return _response(status, {"code": code})
        if (method, path) == ("PUT", subject.CASE_PATH):
            self.case_written = True
            return _response(200, {
                "client_id": subject.CLIENT_ID,
                "birth_date": subject.BIRTH_DATE,
                "gender": subject.GENDER,
                "planned_retirement_date": subject.RETIREMENT_TARGET_DATE,
                "planned_retirement_age": None,
            })
        if (method, path) == ("PUT", subject.PLANNING_PATH + "/base-date"):
            assert body["expected_version"] == self.planning_version
            self.base_written = True
            self.planning_version += 1
            return _response(200, {"version": self.planning_version})
        if (method, path) == ("PUT", subject.PLANNING_PATH + "/target-date"):
            assert body["expected_version"] == self.planning_version
            assert body["expected_target_reference_fingerprint"] == "d" * 64
            self.target_written = True
            self.planning_version += 1
            return _response(200, {"decision_version": self.planning_version})
        if (method, path) == ("PUT", subject.ELECTIONS_PATH):
            assert body == {
                "expected_scenario_version": subject.INITIAL_SCENARIO_VERSION,
                "elections": [subject._election()],
            }
            self.election_written = True
            self.scenario_version += 1
            return _response(200, _scenario(self.scenario_version))
        if (method, path) == ("POST", subject.FACTOR_PATH):
            assert body["expected_scenario_version"] == self.scenario_version
            assert body["expected_admission_revision"] == 0
            self.factor_written = True
            return _response(200, {
                "admission_revision": 1,
                "professional_admission_fingerprint": "1" * 64,
                "execution_allowed": False,
            })
        if (method, path) == ("POST", subject.PRICE_BASIS_PATH):
            assert body["expected_revision"] == 0
            self.price_written = True
            return _response(200, {
                "scenario_id": subject.SCENARIO_ID,
                "decision_id": subject.DECISION_ID,
                "scenario_version": self.scenario_version,
                "revision": 1,
                "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE",
                "record_fingerprint": "e" * 64,
            })
        raise AssertionError(f"unexpected write {method} {path}")


def _run(client: FakeClient) -> dict[str, Any]:
    return subject.run_completion(
        client,
        origin=subject.STAGING_ORIGIN,
        username="approved-user",
        password=PASSWORD,
    )


def test_complete_fixture_uses_canonical_cas_sequence_and_skips_unready_price_basis():
    client = FakeClient()
    evidence = _run(client)
    assert evidence["run_status"] == "completed"
    assert evidence["scenario_version_after_election"] == 6
    assert evidence["factor_admission_revision"] == 1
    assert evidence["gross_result"]["result_state"] == "RESULT_READY"
    assert evidence["gross_result"]["monthly_estimate_gross_ils"] == "350.00"
    assert evidence["gross_result_reloaded"] is True
    assert evidence["price_basis"] == {
        "status": "skipped",
        "reason": "RETIREMENT_MONTHLY_INCOME_TARGET_NOT_READY",
    }
    writes = [(method, path) for method, path, _ in client.calls
              if method in {"PUT", "POST"} and path not in {
                  "/api/auth/login", "/api/auth/logout"}]
    assert writes == [
        ("PUT", subject.CASE_PATH),
        ("PUT", subject.PLANNING_PATH + "/base-date"),
        ("PUT", subject.PLANNING_PATH + "/target-date"),
        ("PUT", subject.ELECTIONS_PATH),
        ("POST", subject.FACTOR_PATH),
    ]


def test_price_basis_is_written_only_after_ready_target_and_ready_cashflow_source():
    client = FakeClient(price_target_ready=True)
    evidence = _run(client)
    assert client.price_written is True
    assert evidence["price_basis"]["status"] == "confirmed"


@pytest.mark.parametrize(
    ("method", "path", "code"),
    [
        ("PUT", subject.ELECTIONS_PATH, "SCENARIO_VERSION_CONFLICT"),
        ("POST", subject.FACTOR_PATH, "PROFESSIONAL_REVIEW_INPUT_FACTS_MISSING"),
        ("PUT", subject.PLANNING_PATH + "/target-date", "PLANNING_DECISION_STALE"),
    ],
)
def test_cas_and_professional_blocks_stop_without_later_writes(method, path, code):
    client = FakeClient()
    client.failure = (method, path, 409, code)
    with pytest.raises(subject.FixtureCompletionError, match=code):
        _run(client)
    assert not client.price_written
    if path != subject.FACTOR_PATH:
        assert not client.factor_written


def test_network_failure_after_factor_post_is_unknown_and_never_retried():
    client = FakeClient()
    client.network_failure = ("POST", subject.FACTOR_PATH)
    with pytest.raises(
        subject.FixtureCompletionError,
        match="FACTOR_ADMISSION_WRITE_COMMIT_OUTCOME_UNKNOWN",
    ):
        _run(client)
    assert sum(1 for method, path, _ in client.calls
               if (method, path) == ("POST", subject.FACTOR_PATH)) == 1


def test_logout_failure_preserves_confirmed_result_and_reports_cleanup_separately():
    client = FakeClient()
    client.logout_status = 401
    with pytest.raises(subject.FixtureCompletionError) as caught:
        _run(client)
    error = caught.value
    assert str(error) == "FIXTURE_COMPLETION_CLEANUP_FAILED"
    assert error.cleanup_error == "LOGOUT_UNCONFIRMED (HTTP 401)"
    assert error.evidence["run_status"] == "completed"


def test_source_identity_mismatch_stops_before_any_business_write():
    client = FakeClient()
    original = client.get

    def bad_get(path: str, **kwargs):
        response = original(path, **kwargs)
        if path == subject.SCENARIO_PATH:
            body = response.json()
            body["decisions"][0]["source_component_id"] = "wrong"
            return _response(200, body)
        return response

    client.get = bad_get  # type: ignore[method-assign]
    with pytest.raises(subject.FixtureCompletionError, match="DECISION_IDENTITY_MISMATCH"):
        _run(client)
    assert not any(method in {"PUT", "POST"} and path not in {
        "/api/auth/login", "/api/auth/logout"} for method, path, _ in client.calls)


def test_invalid_origin_is_rejected_before_login():
    client = FakeClient()
    with pytest.raises(subject.ProbeError, match="STAGING_ORIGIN_NOT_ALLOWED"):
        subject.run_completion(
            client,
            origin="https://retire-v2-production.example",
            username="approved-user",
            password=PASSWORD,
        )
    assert client.calls == []


def test_factor_cursor_conflict_blocks_duplicate_or_unverified_admission():
    client = FakeClient()
    original = client.get

    def stale_cursor(path: str, **kwargs):
        if path == subject.FACTOR_CURSOR_PATH:
            client._record("GET", path)
            return _response(200, {
                "scenario_version": client.scenario_version,
                "latest_admission_revision": 1,
                "authority_state": "NOT_EVALUATED",
            })
        return original(path, **kwargs)

    client.get = stale_cursor  # type: ignore[method-assign]
    with pytest.raises(subject.FixtureCompletionError, match="FACTOR_ADMISSION_CURSOR_CONFLICT"):
        _run(client)
    assert not client.factor_written


def test_failure_evidence_never_contains_credentials_cookie_or_csrf():
    client = FakeClient()
    client.failure = ("POST", subject.FACTOR_PATH, 409, "FACTOR_ADMISSION_SCENARIO_STALE")
    with pytest.raises(subject.FixtureCompletionError) as caught:
        _run(client)
    rendered = repr(caught.value.evidence) + str(caught.value)
    assert PASSWORD not in rendered
    assert CSRF not in rendered
    assert "cookie" not in rendered.lower()


def test_approved_remaining_values_are_canonical_and_explicitly_synthetic():
    election = subject._election()
    assert subject.GENDER == "male"
    assert election["survivors_option"] == "תקנוני"
    assert election["coefficient_selection"] == "manual_review_required"
    assert election["company_name"].startswith("SYNTHETIC-")
    assert election["option_name"].startswith("SYNTHETIC-")
    assert subject.FACTOR_EVIDENCE_TYPE == "PLANNER_ASSUMPTION"
    assert subject.FACTOR_EVIDENCE_REFERENCE.startswith("SYNTHETIC-E2E-STAGING-")
