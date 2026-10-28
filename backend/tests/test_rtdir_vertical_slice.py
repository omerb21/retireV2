from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest
from starlette.responses import Response

from app import main as app_main
from app.api import retirement_income_readiness_routes as routes
from app.api import auth_routes
from app.db.session import get_db
from app.main import app
from app.main import create_app
from app.security.config import AuthConfig, valid_actor
from app.security import middleware as security_middleware
from app.security import session as session_security
from app.security.rate_limit import bucket, login_buckets
from app.security.session import SESSION_SECONDS, issue, public_dto, verify
from app.security.session import COOKIE_NAME
from app.services import retirement_monthly_income_target_service as target_service
from app.services import retirement_target_date_income_comparison_basis_service as comparison_service


class PristineDB:
    def __init__(self):
        self.operations: list[str] = []

    def rollback(self):
        self.operations.append("rollback")

    def in_transaction(self):
        return False


def _db_override(db):
    def dependency():
        yield db
    return dependency


def _context_result(client_id=7):
    return {
        "client_id": client_id,
        "planning_calculation_input_fingerprint": "a" * 64,
        "planning_input_ready": False,
        "retirement_target": {"retirement_target_date": "2035-04-01", "retirement_target_ready": True},
        "blocking_facts": [{"source_id": "income:1", "code": "identity_resolution_required"}],
    }


def _target_result(client_id=7):
    result = {
        "schema_version": "CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY_RESULT_V1",
        "client_id": client_id,
        "planning_calculation_input_fingerprint": "a" * 64,
        "retirement_target_date": "2035-04-01",
        "target": None,
        "authority": None,
        "authority_state": "MISSING",
        "target_readiness_state": "NOT_READY",
        "target_ready": False,
        "blockers": ["RIT_TARGET_MISSING"],
        "target_semantic_fingerprint": None,
    }
    result["target_result_fingerprint"] = target_service._fingerprint({"contract": target_service.RESULT_CONTRACT, **result})
    return result


def test_context_is_a_value_preserving_single_call_adapter(monkeypatch):
    db = PristineDB(); calls = []
    monkeypatch.setattr(routes.planning_input_service, "read", lambda actual, client: calls.append((actual, client)) or _context_result(client))
    app.dependency_overrides[get_db] = _db_override(db)
    try:
        response = TestClient(app).get("/api/clients/7/retirement-income-readiness/context")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "RTDIR_PLANNING_CONTEXT_V1", "client_id": 7,
        "planning_calculation_input_fingerprint": "a" * 64,
        "planning_input_ready": False, "retirement_target_date": "2035-04-01",
        "retirement_target_ready": True,
        "blocking_facts": [{"source_id": "income:1", "code": "identity_resolution_required"}],
    }
    assert calls == [(db, 7)]
    assert db.operations == ["rollback"]


def test_target_assessment_passes_the_pristine_request_session_once(monkeypatch):
    db = PristineDB(); calls = []
    monkeypatch.setattr(routes.target_service, "assess", lambda actual, client: calls.append((actual, client, list(actual.operations))) or _target_result(client))
    app.dependency_overrides[get_db] = _db_override(db)
    try:
        response = TestClient(app).get("/api/clients/7/retirement-income-readiness/target")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert calls == [(db, 7, [])]


def test_target_confirmation_injects_path_client_and_server_actor(monkeypatch):
    db = PristineDB(); observed = []
    monkeypatch.setattr(routes.target_service, "confirm", lambda actual, command, actor: observed.append((actual, command, actor)) or _target_result(7))
    app.dependency_overrides[get_db] = _db_override(db)
    body = {
        "expected_record_version": 0,
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "2035-04-01",
        "monthly_amount": "12000.5", "income_basis": "GROSS",
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
        "source_kind": "PLANNER_SUPPLIED",
    }
    try:
        response = TestClient(app).put("/api/clients/7/retirement-income-readiness/target", json=body)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert observed[0][0] is db
    assert observed[0][1] == {"client_id": 7, **body}
    assert observed[0][2] == "development-professional"


def test_comparison_forbids_client_override_and_calls_public_owner_once(monkeypatch):
    db = PristineDB(); calls = []
    result = comparison_service._failure({
        "client_id": 7,
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "2035-04-01",
    }, "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY")
    monkeypatch.setattr(routes.comparison_service, "assess", lambda actual, request: calls.append((actual, request, list(actual.operations))) or result)
    app.dependency_overrides[get_db] = _db_override(db)
    client = TestClient(app)
    try:
        rejected = client.post("/api/clients/7/retirement-income-readiness/comparison", json={
            "client_id": 8, "expected_planning_calculation_input_fingerprint": "a" * 64,
            "expected_retirement_target_date": "2035-04-01",
        })
        accepted = client.post("/api/clients/7/retirement-income-readiness/comparison", json={
            "expected_planning_calculation_input_fingerprint": "a" * 64,
            "expected_retirement_target_date": "2035-04-01",
        })
    finally:
        app.dependency_overrides.clear()
    assert rejected.status_code == 422
    assert accepted.status_code == 200 and accepted.json() == result
    assert calls == [(db, {"client_id": 7, "expected_planning_calculation_input_fingerprint": "a" * 64, "expected_retirement_target_date": "2035-04-01"}, [])]


def test_session_is_absolute_non_sliding_and_actor_bound():
    config = AuthConfig(production=True, actor_id="planner:one", session_secret=b"s" * 32, rate_limit_secret=b"r" * 32)
    token, payload = issue(config, now=1_800_000_000)
    assert payload["exp"] - payload["iat"] == SESSION_SECONDS
    assert set(payload) == {"contract", "actor_id", "iat", "exp", "nonce", "csrf"}
    checked, code = verify(config, token, now=1_800_000_100)
    assert code is None and checked == payload
    assert public_dto(payload)["csrf_token"] == payload["csrf"]
    wrong_actor = AuthConfig(production=True, actor_id="planner:two", session_secret=b"s" * 32, rate_limit_secret=b"r" * 32)
    assert verify(wrong_actor, token, now=1_800_000_100)[1] == "SESSION_INVALID"
    assert verify(config, token, now=payload["exp"])[1] == "SESSION_EXPIRED"


def test_rate_limit_keys_are_hmac_only_and_domain_separated():
    config = AuthConfig(production=True, actor_id="planner", session_secret=b"s" * 32, rate_limit_secret=b"r" * 32)
    buckets = login_buckets(config, "omer", "127.0.0.1")
    assert [item.key for item in buckets] == sorted(item.key for item in buckets)
    assert {item.kind for item in buckets} == {"GLOBAL", "USER", "IP"}
    assert all(len(item.key) == 64 and "omer" not in item.key and "127" not in item.key for item in buckets)
    assert bucket(config, "USER", "omer").key != bucket(config, "IP", "omer").key


def test_actor_contract_matches_rit_boundary():
    assert valid_actor("planner:retirement")
    assert not valid_actor("")
    assert not valid_actor(" planner")
    assert not valid_actor("planner\n")


def _production_config() -> AuthConfig:
    return AuthConfig(
        production=True,
        public_origin="https://retire.example",
        public_authority="retire.example",
        username="planner",
        password_hash="unused-by-these-tests",
        dummy_password_hash="also-unused",
        actor_id="trusted:planner",
        session_secret=b"s" * 32,
        rate_limit_secret=b"r" * 32,
    )


def _edge_headers(**extra: str) -> dict[str, str]:
    headers = {
        "host": "retire.example",
        "x-real-ip": "2001:db8::1",
        "x-forwarded-proto": "https",
        "x-forwarded-host": "retire.example",
    }
    headers.update(extra)
    return headers


def _authenticated_client():
    config = _production_config()
    production_app = create_app(config)
    token, payload = issue(config)
    client = TestClient(production_app)
    client.cookies.set(COOKIE_NAME, token)
    return client, payload


def test_production_protects_known_and_unknown_api_before_route_disclosure():
    client = TestClient(create_app(_production_config()))
    known = client.get("/api/auth/session", headers=_edge_headers())
    unknown = client.get("/api/not-a-real-route", headers=_edge_headers())
    assert (known.status_code, known.json()["code"]) == (401, "SESSION_MISSING")
    assert (unknown.status_code, unknown.json()["code"]) == (401, "SESSION_MISSING")
    assert known.headers["cache-control"] == "no-store, private"
    assert unknown.headers["pragma"] == "no-cache"


def test_session_actor_is_server_bound_and_forged_headers_are_ignored():
    client, payload = _authenticated_client()
    response = client.get(
        "/api/auth/session",
        headers=_edge_headers(**{"x-professional-actor": "forged", "x-forwarded-for": "127.0.0.1"}),
    )
    assert response.status_code == 200
    assert response.json()["actor_id"] == "trusted:planner"
    assert response.json()["csrf_token"] == payload["csrf"]


def test_unsafe_request_requires_exact_origin_and_session_bound_csrf():
    client, payload = _authenticated_client()
    missing_origin = client.post("/api/auth/logout", headers=_edge_headers())
    wrong_csrf = client.post(
        "/api/auth/logout",
        headers=_edge_headers(origin="https://retire.example", **{"x-rtdir-csrf": "B" * 43}),
    )
    accepted = client.post(
        "/api/auth/logout",
        headers=_edge_headers(origin="https://retire.example", **{"x-rtdir-csrf": payload["csrf"]}),
    )
    assert (missing_origin.status_code, missing_origin.json()["code"]) == (403, "ORIGIN_FORBIDDEN")
    assert (wrong_csrf.status_code, wrong_csrf.json()["code"]) == (403, "CSRF_INVALID")
    assert accepted.status_code == 204
    assert COOKIE_NAME + "=" in accepted.headers["set-cookie"]
    assert "Max-Age=0" in accepted.headers["set-cookie"]


def test_logout_session_failures_are_normalized_to_authentication_required_and_delete_cookie():
    config = _production_config()
    client = TestClient(create_app(config))
    valid_headers = _edge_headers(origin="https://retire.example")
    missing = client.post("/api/auth/logout", headers=valid_headers)
    client.cookies.set(COOKIE_NAME, "not-a-session")
    malformed = client.post("/api/auth/logout", headers=valid_headers)
    expired_token, _ = issue(config, now=1)
    client.cookies.set(COOKIE_NAME, expired_token)
    expired = client.post("/api/auth/logout", headers=valid_headers)
    wrong_config = AuthConfig(**{**config.__dict__, "session_secret": b"w" * 32})
    wrong_token, _ = issue(wrong_config)
    client.cookies.set(COOKIE_NAME, wrong_token)
    wrong_signature = client.post("/api/auth/logout", headers=valid_headers)
    for response in (missing, malformed, expired, wrong_signature):
        assert (response.status_code, response.json()["code"]) == (401, "AUTHENTICATION_REQUIRED")
        assert response.json()["schema_version"] == "RTDIR_TRANSPORT_ERROR_V1"
        assert response.json()["field_paths"] == []
        assert COOKIE_NAME + "=" in response.headers["set-cookie"]
        assert "Max-Age=0" in response.headers["set-cookie"]


def test_logout_wrong_origin_precedes_missing_and_invalid_session():
    config = _production_config()
    client = TestClient(create_app(config))
    wrong_origin = _edge_headers(origin="https://evil.example")
    missing = client.post("/api/auth/logout", headers=wrong_origin)
    client.cookies.set(COOKIE_NAME, "not-a-session")
    invalid = client.post("/api/auth/logout", headers=wrong_origin)
    for response in (missing, invalid):
        assert (response.status_code, response.json()["code"]) == (403, "ORIGIN_FORBIDDEN")
        assert response.json()["schema_version"] == "RTDIR_TRANSPORT_ERROR_V1"
        assert response.json()["field_paths"] == []


def test_csrf_requires_canonical_decoded_32_bytes_and_session_binding():
    client, payload = _authenticated_client()
    headers = _edge_headers(origin="https://retire.example")
    malformed = ["A" * 42, "A" * 43 + "=", "!" * 43, "_" * 43]
    for token in malformed:
        response = client.post("/api/auth/logout", headers={**headers, "x-rtdir-csrf": token})
        assert (response.status_code, response.json()["code"]) == (403, "CSRF_INVALID")
    other_config = _production_config()
    _, other = issue(other_config)
    assert other["csrf"] != payload["csrf"]
    cross = client.post("/api/auth/logout", headers={**headers, "x-rtdir-csrf": other["csrf"]})
    assert (cross.status_code, cross.json()["code"]) == (403, "CSRF_INVALID")


def test_deployment_environment_mode_is_explicit_and_fail_closed(monkeypatch):
    for name in ("APP_ENV", "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID"):
        monkeypatch.delenv(name, raising=False)
    assert AuthConfig.from_env() == AuthConfig(production=False)
    for invalid in ("", "prod", "Production", " production"):
        monkeypatch.setenv("APP_ENV", invalid)
        with pytest.raises(RuntimeError, match="APP_ENV"):
            AuthConfig.from_env()
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="APP_ENV"):
        AuthConfig.from_env()


def test_strict_producer_contracts_reject_malformed_results(monkeypatch):
    db = PristineDB()
    app.dependency_overrides[get_db] = _db_override(db)
    client = TestClient(app)
    try:
        monkeypatch.setattr(routes.target_service, "assess", lambda *_: {**_target_result(), "authority_state": "SURPRISE"})
        target_response = client.get("/api/clients/7/retirement-income-readiness/target")
        monkeypatch.setattr(routes.comparison_service, "assess", lambda *_: {"client_id": 7, "result_state": "block_no_result"})
        comparison_response = client.post("/api/clients/7/retirement-income-readiness/comparison", json={
            "expected_planning_calculation_input_fingerprint": "a" * 64,
            "expected_retirement_target_date": "2035-04-01",
        })
        monkeypatch.setattr(routes.planning_input_service, "read", lambda *_: {**_context_result(), "planning_input_ready": "yes"})
        context_response = client.get("/api/clients/7/retirement-income-readiness/context")
    finally:
        app.dependency_overrides.clear()
    for response in (target_response, comparison_response, context_response):
        assert (response.status_code, response.json()["code"]) == (500, "PRODUCER_RESPONSE_INVALID")


def test_production_unexpected_exception_is_sanitized(monkeypatch):
    production_app = create_app(_production_config())
    client, payload = _authenticated_client()
    production_app.dependency_overrides[get_db] = _db_override(PristineDB())
    monkeypatch.setattr(routes.target_service, "assess", lambda *_: (_ for _ in ()).throw(RuntimeError("secret client material")))
    client = TestClient(production_app, raise_server_exceptions=False)
    token, _ = issue(_production_config())
    client.cookies.set(COOKIE_NAME, token)
    response = client.get("/api/clients/7/retirement-income-readiness/target", headers=_edge_headers())
    assert (response.status_code, response.json()["code"]) == (500, "INTERNAL_ERROR")
    assert "secret" not in response.text
    assert response.headers["cache-control"] == "no-store, private"


def test_edge_and_preflight_contracts_are_closed_and_exact():
    client = TestClient(create_app(_production_config()))
    missing_edge = client.get("/healthz/live", headers={"host": "retire.example"})
    forged_host = client.get("/healthz/live", headers=_edge_headers(**{"x-forwarded-host": "evil.example"}))
    preflight = client.options(
        "/api/auth/session",
        headers=_edge_headers(
            origin="https://retire.example",
            **{
                "access-control-request-method": "GET",
                "access-control-request-headers": "Content-Type, X-RTDIR-CSRF",
            },
        ),
    )
    rejected = client.options(
        "/api/auth/session",
        headers=_edge_headers(
            origin="https://evil.example",
            **{"access-control-request-method": "GET"},
        ),
    )
    assert (missing_edge.status_code, missing_edge.json()["code"]) == (400, "EDGE_REQUEST_INVALID")
    assert (forged_host.status_code, forged_host.json()["code"]) == (400, "EDGE_REQUEST_INVALID")
    assert preflight.status_code == 204
    assert preflight.headers["access-control-allow-origin"] == "https://retire.example"
    assert preflight.headers["access-control-allow-credentials"] == "true"
    assert (rejected.status_code, rejected.json()["code"]) == (403, "ORIGIN_FORBIDDEN")


def test_internal_railway_readiness_exception_is_exact():
    production_app = create_app(_production_config())
    production_app.state.rate_limiter_ready = True
    client = TestClient(production_app)
    accepted = client.get("/healthz/ready", headers={"host": "healthcheck.railway.app"})
    wrong_path = client.get("/healthz/live", headers={"host": "healthcheck.railway.app"})
    wrong_method = client.head("/healthz/ready", headers={"host": "healthcheck.railway.app"})
    assert accepted.status_code == 200 and accepted.json() == {"status": "ready"}
    assert wrong_path.status_code == 400 and wrong_path.json()["code"] == "EDGE_REQUEST_INVALID"
    assert wrong_method.status_code == 400


def test_every_registered_api_route_is_login_or_protected_by_global_middleware():
    production_app = create_app(_production_config())
    client = TestClient(production_app)
    for route in production_app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if not path.startswith("/api/"):
            continue
        for method in methods - {"OPTIONS"}:
            if (method, path) == ("POST", "/api/auth/login"):
                continue
            concrete = path
            for parameter in ("client_id", "conversion_id", "run_id", "revision_id"):
                concrete = concrete.replace("{" + parameter + "}", "1")
            headers = _edge_headers(origin="https://retire.example") if (method, path) == ("POST", "/api/auth/logout") else _edge_headers()
            response = client.request(method, concrete, headers=headers)
            assert response.status_code == 401, (method, path, response.status_code, response.text)
            expected_code = "AUTHENTICATION_REQUIRED" if path == "/api/auth/logout" else "SESSION_MISSING"
            assert response.json()["code"] == expected_code


def test_login_uses_real_and_dummy_argon_and_issues_exact_cookie(monkeypatch):
    from argon2 import PasswordHasher

    hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
    config = _production_config()
    config = AuthConfig(
        **{
            **config.__dict__,
            "password_hash": hasher.hash("correct-password"),
            "dummy_password_hash": hasher.hash("different-dummy-password"),
        }
    )
    production_app = create_app(config)
    production_app.state.rate_limiter_ready = True

    class Store:
        def close(self):
            pass

    finalized: list[bool] = []
    monkeypatch.setattr(auth_routes, "_store", lambda request: Store())
    monkeypatch.setattr(auth_routes, "cleanup_batch", lambda db: 0)
    monkeypatch.setattr(auth_routes, "precheck", lambda db, buckets: 0)
    monkeypatch.setattr(auth_routes, "finalize", lambda db, buckets, success: finalized.append(success) or 0)
    client = TestClient(production_app)
    headers = _edge_headers(origin="https://retire.example")
    unknown = client.post("/api/auth/login", headers=headers, json={"username": "unknown", "password": "correct-password"})
    success = client.post("/api/auth/login", headers=headers, json={"username": "planner", "password": "correct-password"})
    assert (unknown.status_code, unknown.json()["code"]) == (401, "AUTHENTICATION_FAILED")
    assert success.status_code == 200
    assert finalized == [False, True]
    cookie = success.headers["set-cookie"]
    assert cookie.startswith(COOKIE_NAME + "=")
    assert all(item in cookie for item in ("HttpOnly", "Max-Age=28800", "Path=/", "SameSite=lax", "Secure"))
    assert "Domain=" not in cookie


def test_invalid_login_framing_never_reaches_argon(monkeypatch):
    production_app = create_app(_production_config())
    production_app.state.rate_limiter_ready = True

    class Store:
        def close(self):
            pass

    mutations: list[bool] = []
    monkeypatch.setattr(auth_routes, "_store", lambda request: Store())
    monkeypatch.setattr(auth_routes, "finalize", lambda db, buckets, success: mutations.append(success) or 0)
    client = TestClient(production_app)
    headers = _edge_headers(origin="https://retire.example")
    bad_json = client.post("/api/auth/login", headers={**headers, "content-type": "application/json"}, content=b"{")
    bad_shape = client.post("/api/auth/login", headers=headers, json={"username": "planner", "password": "ok", "actor": "forged"})
    wrong_media = client.post("/api/auth/login", headers={**headers, "content-type": "text/plain"}, content=b"{}")
    too_large = client.post("/api/auth/login", headers={**headers, "content-type": "application/json"}, content=b" " * 8193)
    assert (bad_json.status_code, bad_json.json()["code"]) == (400, "REQUEST_JSON_INVALID")
    assert (bad_shape.status_code, bad_shape.json()["code"]) == (422, "LOGIN_REQUEST_INVALID")
    assert bad_shape.json()["field_paths"] == ["/actor"]
    assert (wrong_media.status_code, wrong_media.json()["code"]) == (415, "LOGIN_CONTENT_TYPE_UNSUPPORTED")
    assert (too_large.status_code, too_large.json()["code"]) == (413, "LOGIN_BODY_TOO_LARGE")
    assert mutations == [False, False]


def _assert_mutation_cycle(ordinary, mutate, restore):
    ordinary()
    mutate()
    killed = False
    try:
        ordinary()
    except Exception:
        killed = True
    finally:
        restore()
    assert killed, "the unchanged ordinary oracle survived the production-branch mutation"
    ordinary()


def test_mutation_dummy_argon_branch_is_detected_and_restored(monkeypatch):
    from argon2 import PasswordHasher

    config = _production_config()
    production_app = create_app(config)
    production_app.state.rate_limiter_ready = True

    class Store:
        def close(self):
            pass

    monkeypatch.setattr(auth_routes, "_store", lambda request: Store())
    monkeypatch.setattr(auth_routes, "cleanup_batch", lambda db: 0)
    monkeypatch.setattr(auth_routes, "precheck", lambda db, buckets: 0)
    monkeypatch.setattr(auth_routes, "finalize", lambda db, buckets, success: 0)
    selected: list[str] = []
    monkeypatch.setattr(
        PasswordHasher,
        "verify",
        lambda self, encoded, password: selected.append(encoded) or False,
    )
    client = TestClient(production_app)

    def ordinary():
        selected.clear()
        response = client.post(
            "/api/auth/login",
            headers=_edge_headers(origin="https://retire.example"),
            json={"username": "unknown", "password": "secret"},
        )
        assert (response.status_code, response.json()["code"]) == (401, "AUTHENTICATION_FAILED")
        assert selected == [config.dummy_password_hash]

    original = auth_routes.hmac.compare_digest
    _assert_mutation_cycle(
        ordinary,
        lambda: monkeypatch.setattr(auth_routes.hmac, "compare_digest", lambda *_: True),
        lambda: monkeypatch.setattr(auth_routes.hmac, "compare_digest", original),
    )


def test_mutation_session_signing_expiry_and_actor_contract_is_detected_and_restored(monkeypatch):
    old = AuthConfig(production=True, actor_id="planner:one", session_secret=b"o" * 32, rate_limit_secret=b"r" * 32)
    current = AuthConfig(production=True, actor_id="planner:one", session_secret=b"n" * 32, rate_limit_secret=b"r" * 32)
    token, payload = session_security.issue(old, now=1_800_000_000)

    def signing_oracle():
        assert session_security.verify(current, token, now=1_800_000_100)[1] == "SESSION_INVALID"

    original_serializer = session_security._serializer
    _assert_mutation_cycle(
        signing_oracle,
        lambda: monkeypatch.setattr(session_security, "_serializer", lambda config: original_serializer(old)),
        lambda: monkeypatch.setattr(session_security, "_serializer", original_serializer),
    )

    def lifetime_oracle():
        assert session_security.verify(old, token, now=1_800_000_100) == (payload, None)
        wrong_actor = AuthConfig(production=True, actor_id="planner:two", session_secret=b"o" * 32, rate_limit_secret=b"r" * 32)
        assert session_security.verify(wrong_actor, token, now=1_800_000_100)[1] == "SESSION_INVALID"
        assert session_security.verify(old, token, now=payload["exp"])[1] == "SESSION_EXPIRED"

    _assert_mutation_cycle(
        lifetime_oracle,
        lambda: monkeypatch.setattr(session_security, "SESSION_SECONDS", SESSION_SECONDS * 2),
        lambda: monkeypatch.setattr(session_security, "SESSION_SECONDS", SESSION_SECONDS),
    )


def test_mutation_origin_and_csrf_guards_are_detected_and_restored(monkeypatch):
    def origin_oracle():
        client, _ = _authenticated_client()
        response = client.post("/api/auth/logout", headers=_edge_headers())
        assert (response.status_code, response.json()["code"]) == (403, "ORIGIN_FORBIDDEN")

    original_origin = security_middleware.validate_origin
    _assert_mutation_cycle(
        origin_oracle,
        lambda: monkeypatch.setattr(security_middleware, "validate_origin", lambda *_: None),
        lambda: monkeypatch.setattr(security_middleware, "validate_origin", original_origin),
    )

    def csrf_oracle():
        client, _ = _authenticated_client()
        response = client.post(
            "/api/auth/logout",
            headers=_edge_headers(origin="https://retire.example", **{"x-rtdir-csrf": "B" * 43}),
        )
        assert (response.status_code, response.json()["code"]) == (403, "CSRF_INVALID")

    original_csrf = security_middleware.validate_csrf
    _assert_mutation_cycle(
        csrf_oracle,
        lambda: monkeypatch.setattr(security_middleware, "validate_csrf", lambda *_: None),
        lambda: monkeypatch.setattr(security_middleware, "validate_csrf", original_csrf),
    )


def test_mutation_login_framing_and_cookie_rules_are_detected_and_restored(monkeypatch):
    from argon2 import PasswordHasher

    config = _production_config()
    production_app = create_app(config)
    production_app.state.rate_limiter_ready = True

    class Store:
        def close(self):
            pass

    monkeypatch.setattr(auth_routes, "_store", lambda request: Store())
    monkeypatch.setattr(auth_routes, "cleanup_batch", lambda db: 0)
    monkeypatch.setattr(auth_routes, "precheck", lambda db, buckets: 0)
    monkeypatch.setattr(auth_routes, "finalize", lambda db, buckets, success: 0)
    verify_calls: list[str] = []
    monkeypatch.setattr(PasswordHasher, "verify", lambda self, encoded, password: verify_calls.append(password) or True)
    client = TestClient(production_app)
    headers = _edge_headers(origin="https://retire.example")

    def framing_oracle():
        verify_calls.clear()
        response = client.post("/api/auth/login", headers=headers, json={"username": "planner", "password": "bad\n"})
        assert (response.status_code, response.json()["code"]) == (422, "LOGIN_REQUEST_INVALID")
        assert verify_calls == []

    original_valid_password = auth_routes._valid_password
    _assert_mutation_cycle(
        framing_oracle,
        lambda: monkeypatch.setattr(auth_routes, "_valid_password", lambda value: True),
        lambda: monkeypatch.setattr(auth_routes, "_valid_password", original_valid_password),
    )

    def cookie_oracle():
        response = client.post("/api/auth/login", headers=headers, json={"username": "planner", "password": "secret"})
        cookie = response.headers["set-cookie"]
        assert response.status_code == 200
        assert all(value in cookie for value in ("HttpOnly", "Max-Age=28800", "Path=/", "SameSite=lax", "Secure"))
        assert "Domain=" not in cookie

    original_set_cookie = auth_routes.Response.set_cookie

    def insecure_cookie(self, key, value="", **kwargs):
        kwargs["secure"] = False
        return original_set_cookie(self, key, value, **kwargs)

    _assert_mutation_cycle(
        cookie_oracle,
        lambda: monkeypatch.setattr(auth_routes.Response, "set_cookie", insecure_cookie),
        lambda: monkeypatch.setattr(auth_routes.Response, "set_cookie", original_set_cookie),
    )


def test_mutation_public_route_health_and_edge_boundaries_are_detected_and_restored(monkeypatch):
    production_app = create_app(_production_config())
    production_app.state.rate_limiter_ready = True
    client = TestClient(production_app, raise_server_exceptions=False)

    def route_oracle():
        response = client.get("/api/not-a-real-route", headers=_edge_headers())
        assert (response.status_code, response.json()["code"]) == (401, "SESSION_MISSING")

    original_public = security_middleware.is_public_path
    _assert_mutation_cycle(
        route_oracle,
        lambda: monkeypatch.setattr(security_middleware, "is_public_path", lambda method, path: path == "/api/not-a-real-route" or original_public(method, path)),
        lambda: monkeypatch.setattr(security_middleware, "is_public_path", original_public),
    )

    def health_oracle():
        response = client.get("/healthz/live", headers={"host": "healthcheck.railway.app"})
        assert (response.status_code, response.json()["code"]) == (400, "EDGE_REQUEST_INVALID")

    original_health = security_middleware.is_internal_health
    _assert_mutation_cycle(
        health_oracle,
        lambda: monkeypatch.setattr(security_middleware, "is_internal_health", lambda request: request.url.path in {"/healthz/ready", "/healthz/live"}),
        lambda: monkeypatch.setattr(security_middleware, "is_internal_health", original_health),
    )

    def edge_oracle():
        response = client.get("/healthz/live", headers={**_edge_headers(), "x-real-ip": "forged"})
        assert (response.status_code, response.json()["code"]) == (400, "EDGE_REQUEST_INVALID")

    original_edge = security_middleware.validate_edge
    _assert_mutation_cycle(
        edge_oracle,
        lambda: monkeypatch.setattr(security_middleware, "validate_edge", lambda *_: ("127.0.0.1", None)),
        lambda: monkeypatch.setattr(security_middleware, "validate_edge", original_edge),
    )


def test_mutation_adapter_reclassification_client_identity_and_single_invocation_are_detected_and_restored(monkeypatch):
    db = PristineDB()
    app.dependency_overrides[get_db] = _db_override(db)
    client = TestClient(app)
    try:
        malformed_context = {**_context_result(7), "planning_input_ready": "yes"}
        monkeypatch.setattr(routes.planning_input_service, "read", lambda *_: malformed_context)

        def context_oracle():
            response = client.get("/api/clients/7/retirement-income-readiness/context")
            assert (response.status_code, response.json()["code"]) == (500, "PRODUCER_RESPONSE_INVALID")

        original_context_valid = routes._context_valid
        _assert_mutation_cycle(
            context_oracle,
            lambda: monkeypatch.setattr(routes, "_context_valid", lambda *_: True),
            lambda: monkeypatch.setattr(routes, "_context_valid", original_context_valid),
        )

        calls: list[int] = []
        monkeypatch.setattr(routes.target_service, "assess", lambda actual, client_id: calls.append(client_id) or _target_result(client_id))

        def invocation_oracle():
            calls.clear()
            response = client.get("/api/clients/7/retirement-income-readiness/target")
            assert response.status_code == 200
            assert calls == [7]

        original_target_valid = routes._target_result_valid

        def duplicate_validation(result, client_id):
            routes.target_service.assess(db, client_id)
            return original_target_valid(result, client_id)

        _assert_mutation_cycle(
            invocation_oracle,
            lambda: monkeypatch.setattr(routes, "_target_result_valid", duplicate_validation),
            lambda: monkeypatch.setattr(routes, "_target_result_valid", original_target_valid),
        )

        monkeypatch.setattr(routes.target_service, "assess", lambda *_: _target_result(8))

        def identity_oracle():
            response = client.get("/api/clients/7/retirement-income-readiness/target")
            assert (response.status_code, response.json()["code"]) == (500, "PRODUCER_RESPONSE_INVALID")

        _assert_mutation_cycle(
            identity_oracle,
            lambda: monkeypatch.setattr(routes, "_target_result_valid", lambda *_: True),
            lambda: monkeypatch.setattr(routes, "_target_result_valid", original_target_valid),
        )
    finally:
        app.dependency_overrides.clear()


def test_mutation_cors_contract_is_detected_and_restored(monkeypatch):
    def ordinary():
        client = TestClient(create_app(_production_config()))
        accepted = client.options("/api/auth/session", headers=_edge_headers(
            origin="https://retire.example",
            **{"access-control-request-method": "POST", "access-control-request-headers": "Content-Type, X-RTDIR-CSRF"},
        ))
        assert accepted.status_code == 204
        assert accepted.headers["access-control-allow-origin"] == "https://retire.example"
        assert accepted.headers["access-control-allow-credentials"] == "true"
        assert accepted.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE, OPTIONS"
        assert accepted.headers["access-control-allow-headers"] == "Content-Type, X-RTDIR-CSRF"
        for extra in (
            {"access-control-request-method": "TRACE"},
            {"access-control-request-method": "POST", "access-control-request-headers": "Authorization"},
        ):
            rejected = client.options("/api/auth/session", headers=_edge_headers(origin="https://retire.example", **extra))
            assert (rejected.status_code, rejected.json()["code"]) == (403, "ORIGIN_FORBIDDEN")

    original = security_middleware.RTDIRSecurityMiddleware.dispatch

    async def wildcard_mutant(self, request, call_next):
        response = await original(self, request, call_next)
        if request.method == "OPTIONS" and response.status_code == 204:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] += ", TRACE"
        return response

    _assert_mutation_cycle(
        ordinary,
        lambda: monkeypatch.setattr(security_middleware.RTDIRSecurityMiddleware, "dispatch", wildcard_mutant),
        lambda: monkeypatch.setattr(security_middleware.RTDIRSecurityMiddleware, "dispatch", original),
    )


def test_mutation_sensitive_response_cache_contract_is_detected_and_restored(monkeypatch):
    def ordinary():
        client, _ = _authenticated_client()
        response = client.get("/api/auth/session", headers=_edge_headers())
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store, private"
        assert response.headers["pragma"] == "no-cache"

    original = dict(security_middleware.NO_STORE)
    _assert_mutation_cycle(
        ordinary,
        security_middleware.NO_STORE.clear,
        lambda: security_middleware.NO_STORE.update(original),
    )


def test_mutation_failed_logout_cannot_be_reported_as_success(monkeypatch):
    def ordinary():
        client = TestClient(create_app(_production_config()))
        response = client.post("/api/auth/logout", headers=_edge_headers(origin="https://retire.example"))
        assert (response.status_code, response.json()["code"]) == (401, "AUTHENTICATION_REQUIRED")
        assert "Max-Age=0" in response.headers["set-cookie"]

    original = security_middleware.error

    def success_mutant(request, status, code, fields=(), headers=None):
        if code == "AUTHENTICATION_REQUIRED":
            return Response(status_code=204)
        return original(request, status, code, fields, headers)

    _assert_mutation_cycle(
        ordinary,
        lambda: monkeypatch.setattr(security_middleware, "error", success_mutant),
        lambda: monkeypatch.setattr(security_middleware, "error", original),
    )


def test_mutation_caller_actor_cannot_cross_target_confirmation_boundary(monkeypatch):
    config = _production_config()
    production_app = create_app(config)
    db = PristineDB()
    production_app.dependency_overrides[get_db] = _db_override(db)
    token, payload = issue(config)
    observed: list[str] = []
    monkeypatch.setattr(routes.target_service, "confirm", lambda actual, command, actor: observed.append(actor) or _target_result(7))
    body = {
        "expected_record_version": 0,
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "2035-04-01",
        "monthly_amount": "12000.00", "income_basis": "GROSS",
        "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE", "price_reference_date": None,
        "source_kind": "PLANNER_SUPPLIED",
    }

    def ordinary():
        observed.clear()
        client = TestClient(production_app)
        client.cookies.set(COOKIE_NAME, token)
        response = client.put(
            "/api/clients/7/retirement-income-readiness/target",
            headers=_edge_headers(origin="https://retire.example", **{
                "x-rtdir-csrf": payload["csrf"], "x-professional-actor": "forged:caller",
            }),
            json=body,
        )
        assert response.status_code == 200
        assert observed == ["trusted:planner"]

    original = security_middleware.validate_session

    def caller_actor_mutant(request, actual_config):
        rejected = original(request, actual_config)
        if rejected is None:
            request.state.trusted_professional_actor = request.headers.get("x-professional-actor")
        return rejected

    try:
        _assert_mutation_cycle(
            ordinary,
            lambda: monkeypatch.setattr(security_middleware, "validate_session", caller_actor_mutant),
            lambda: monkeypatch.setattr(security_middleware, "validate_session", original),
        )
    finally:
        production_app.dependency_overrides.clear()


def test_mutation_comparison_dto_extra_fields_are_detected_and_restored(monkeypatch):
    config = _production_config()
    production_app = create_app(config)
    db = PristineDB()
    production_app.dependency_overrides[get_db] = _db_override(db)
    token, payload = issue(config)
    calls: list[dict] = []
    result = comparison_service._failure({
        "client_id": 7,
        "expected_planning_calculation_input_fingerprint": "a" * 64,
        "expected_retirement_target_date": "2035-04-01",
    }, "target_authority", "RTICB_TARGET_AUTHORITY_NOT_READY")
    monkeypatch.setattr(routes.comparison_service, "assess", lambda actual, command: calls.append(command) or result)
    route = next(item for item in production_app.routes if getattr(item, "path", "") == "/api/clients/{client_id}/retirement-income-readiness/comparison")
    original_adapter = route.body_field._type_adapter

    def ordinary():
        for extra in ({"client_id": 99}, {"trusted_professional_actor": "forged:caller"}):
            calls.clear()
            client = TestClient(production_app)
            client.cookies.set(COOKIE_NAME, token)
            response = client.post(
                "/api/clients/7/retirement-income-readiness/comparison",
                headers=_edge_headers(origin="https://retire.example", **{"x-rtdir-csrf": payload["csrf"]}),
                json={
                    "expected_planning_calculation_input_fingerprint": "a" * 64,
                    "expected_retirement_target_date": "2035-04-01",
                    **extra,
                },
            )
            assert (response.status_code, response.json()["code"]) == (422, "REQUEST_SCHEMA_INVALID")
            assert calls == []

    class IgnoreExtraAdapter:
        def validate_python(self, value, *args, **kwargs):
            if isinstance(value, dict):
                value = {key: item for key, item in value.items() if key in {
                    "expected_planning_calculation_input_fingerprint", "expected_retirement_target_date",
                }}
            return original_adapter.validate_python(value, *args, **kwargs)

    try:
        _assert_mutation_cycle(
            ordinary,
            lambda: setattr(route.body_field, "_type_adapter", IgnoreExtraAdapter()),
            lambda: setattr(route.body_field, "_type_adapter", original_adapter),
        )
    finally:
        route.body_field._type_adapter = original_adapter
        production_app.dependency_overrides.clear()


def test_mutation_production_spa_allowlist_rejects_unknown_and_docs_routes(monkeypatch):
    config = _production_config()
    production_app = create_app(config)
    token, _ = issue(config)

    def ordinary():
        client = TestClient(production_app)
        client.cookies.set(COOKIE_NAME, token)
        for path in ("/unknown-client-screen", "/docs", "/openapi.json"):
            response = client.get(path, headers=_edge_headers())
            assert (response.status_code, response.json()["code"]) == (404, "ROUTE_NOT_FOUND")

    original = app_main.is_spa_path
    _assert_mutation_cycle(
        ordinary,
        lambda: monkeypatch.setattr(app_main, "is_spa_path", lambda path: True),
        lambda: monkeypatch.setattr(app_main, "is_spa_path", original),
    )


def test_production_spa_allowlist_includes_the_professional_workspace_route():
    assert app_main.is_spa_path("/clients/7/workspace") is True
