"""RTDIR's exact RTICB V2 consumer and transport boundary."""
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import OperationalError

from app.api import retirement_income_readiness_routes as routes
from app.db.session import get_db
from app.main import create_app
from app.security.session import COOKIE_NAME, issue
from app.services.retirement_target_date_income_source_admission_service import (
    RetirementTargetIncomeSourceAdmissionTechnicalError,
)
from test_rtdir_vertical_slice import _edge_headers, _production_config
from test_retirement_target_date_income_comparison_basis import (
    PLANNING, TARGET_DATE, _blocked, _collection, _entry, _request, _target,
)


class UntouchedDB:
    pass


def _client(db=None):
    config = _production_config()
    application = create_app(config)
    supplied = db or UntouchedDB()
    def dependency(): yield supplied
    application.dependency_overrides[get_db] = dependency
    token, payload = issue(config)
    client = TestClient(application)
    client.cookies.set(COOKIE_NAME, token)
    headers = _edge_headers(origin="https://retire.example", **{"x-rtdir-csrf": payload["csrf"]})
    return application, client, headers, supplied


def _post(client, headers):
    return client.post(
        "/api/clients/1/retirement-income-readiness/comparison",
        json={
            "expected_planning_calculation_input_fingerprint": PLANNING,
            "expected_retirement_target_date": TARGET_DATE,
        },
        headers=headers,
    )


def _success():
    return routes.comparison_service._result(_request(), _target(), _collection([_entry()]))


def _professional_failure():
    return routes.comparison_service._failure(
        _request(), "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY", target=_target(),
    )


@pytest.mark.parametrize("result", [_success(), _professional_failure()])
def test_success_and_professional_failure_are_forwarded_verbatim_once(monkeypatch, result):
    calls = []
    monkeypatch.setattr(routes.comparison_service, "assess", lambda db, command: calls.append((db, command)) or deepcopy(result))
    application, client, headers, db = _client()
    try: response = _post(client, headers)
    finally: application.dependency_overrides.clear()
    assert response.status_code == 200 and response.json() == result
    assert calls == [(db, _request())]
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"


def test_wrong_client_precedes_shape_and_mixed_v1_v2_fail_closed(monkeypatch):
    application, client, headers, _ = _client()
    try:
        monkeypatch.setattr(routes.comparison_service, "assess", lambda *_: {"client_id": 2})
        foreign = _post(client, headers)
        monkeypatch.setattr(routes.comparison_service, "assess", lambda *_: {
            "schema_version": "RTICB_RESULT_V1", "client_id": 1,
        })
        v1 = _post(client, headers)
        mixed = _success(); mixed["rtisa_admission_result_fingerprint"] = "a" * 64
        monkeypatch.setattr(routes.comparison_service, "assess", lambda *_: mixed)
        hybrid = _post(client, headers)
    finally: application.dependency_overrides.clear()
    assert (foreign.status_code, foreign.json()["code"]) == (500, "RESPONSE_CLIENT_MISMATCH")
    assert (v1.status_code, v1.json()["code"]) == (500, "PRODUCER_RESPONSE_INVALID")
    assert (hybrid.status_code, hybrid.json()["code"]) == (500, "PRODUCER_RESPONSE_INVALID")


@pytest.mark.parametrize("code,status,expected_status,expected_code,fields", [
    ("CRTISBA_UPSTREAM_TECHNICAL_FAILURE", 503, 503, "RTICB_UPSTREAM_TECHNICAL_FAILURE", []),
    ("PRODUCER_RESPONSE_INVALID", 500, 500, "PRODUCER_RESPONSE_INVALID", []),
    ("RESPONSE_CLIENT_MISMATCH", 500, 500, "RESPONSE_CLIENT_MISMATCH", []),
    ("CLIENT_NOT_FOUND", 404, 404, "CLIENT_NOT_FOUND", ["/path/client_id"]),
    ("CRTISBA_DATABASE_FAILURE", 503, 500, "INTERNAL_ERROR", []),
    ("CRTISBA_SOURCE_NOT_FOUND", 404, 500, "INTERNAL_ERROR", []),
])
def test_exhaustive_crtisba_exception_whitelist(monkeypatch, code, status, expected_status, expected_code, fields):
    calls = []
    def fail(*_):
        calls.append(code)
        raise routes.source_basis_service.CRTISBAError(code, status)
    monkeypatch.setattr(routes.comparison_service, "assess", fail)
    application, client, headers, _ = _client()
    try: response = _post(client, headers)
    finally: application.dependency_overrides.clear()
    assert calls == [code]
    assert (response.status_code, response.json()["code"], response.json()["field_paths"]) == (
        expected_status, expected_code, fields,
    )
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"


@pytest.mark.parametrize("exception,status,code", [
    (routes.source_basis_service.CRTISBAFingerprintConstructionError(), 500, "INTERNAL_ERROR"),
    (routes.comparison_service.RTICBFingerprintConstructionError(), 500, "INTERNAL_ERROR"),
    (OperationalError("SELECT", {}, Exception("database")), 503, "RTICB_DATABASE_FAILURE"),
    (RetirementTargetIncomeSourceAdmissionTechnicalError("stage", "blocker", "detail"), 503, "RTICB_UPSTREAM_TECHNICAL_FAILURE"),
    (RuntimeError("unexpected"), 500, "INTERNAL_ERROR"),
])
def test_other_technical_families_have_deterministic_transport(monkeypatch, exception, status, code):
    def fail(*_): raise exception
    monkeypatch.setattr(routes.comparison_service, "assess", fail)
    application, client, headers, _ = _client()
    try: response = _post(client, headers)
    finally: application.dependency_overrides.clear()
    assert (response.status_code, response.json()["code"], response.json()["field_paths"]) == (status, code, [])


def test_consumer_validator_kills_coherently_rehashed_professional_tampering():
    ordinary = _success()
    assert routes.comparison_service.public_result_valid(ordinary, 1, PLANNING, TARGET_DATE)
    mutant = deepcopy(ordinary)
    mutant["source_comparisons"][0]["comparison_state"] = "NOT_ADMITTED"
    entry = mutant["source_comparisons"][0]
    bare = {key: value for key, value in entry.items() if key != "source_comparison_fingerprint"}
    entry["source_comparison_fingerprint"] = routes.comparison_service._fingerprint({
        "contract": routes.comparison_service.ENTRY_FINGERPRINT_CONTRACT,
        "comparison_input_fingerprint": mutant["comparison_input_fingerprint"], "entry": bare,
    })
    payload = {key: value for key, value in mutant.items() if key != "comparison_result_fingerprint"}
    mutant["comparison_result_fingerprint"] = routes.comparison_service._fingerprint({
        "contract": routes.comparison_service.RESULT_FINGERPRINT_CONTRACT, "result": payload,
    })
    assert not routes.comparison_service.public_result_valid(mutant, 1, PLANNING, TARGET_DATE)
    assert routes.comparison_service.public_result_valid(ordinary, 1, PLANNING, TARGET_DATE)


def test_blocked_failure_identity_is_not_accepted_as_a_bare_rticb_result():
    assert not routes.comparison_service.public_result_valid(_blocked("planning_context"), 1, PLANNING, TARGET_DATE)


def test_route_response_validator_mutation_is_killed_and_restored(monkeypatch):
    malformed = {"schema_version": "RTICB_RESULT_V1", "client_id": 1}
    monkeypatch.setattr(routes.comparison_service, "assess", lambda *_: deepcopy(malformed))
    application, client, headers, _ = _client()
    def ordinary_oracle():
        response = _post(client, headers)
        assert (response.status_code, response.json()["code"]) == (
            500, "PRODUCER_RESPONSE_INVALID",
        )
    try:
        ordinary_oracle()
        original = routes.comparison_service.public_result_valid
        reached = []
        def bypass(*args, **kwargs):
            reached.append((args, kwargs)); return True
        monkeypatch.setattr(routes.comparison_service, "public_result_valid", bypass)
        with pytest.raises((AssertionError, KeyError)):
            ordinary_oracle()
        assert reached
        monkeypatch.setattr(routes.comparison_service, "public_result_valid", original)
        ordinary_oracle()
    finally:
        application.dependency_overrides.clear()
