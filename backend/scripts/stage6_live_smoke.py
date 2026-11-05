"""Read-only HTTP smoke test for the isolated Render Stage 6 review service.

Run from backend:
  .venv-py311\\Scripts\\python.exe scripts\\stage6_live_smoke.py

Prompts for the staging-only login password without echoing it.
Does not create, modify, export, or delete any customer records.
"""
from __future__ import annotations

import getpass
import sys

import httpx

ORIGIN = "https://retirev2-stage6-review-20261105.onrender.com"
USERNAME = "stage6-review"
EXPECTED_CLIENTS = (1, 2)
CAPABILITY_PATH = "/api/clients/{client_id}/scenario-drafts/capabilities/gross-scenario-results"


def expect(response: httpx.Response, status: int, label: str) -> dict | list | None:
    if response.status_code != status:
        try:
            code = response.json().get("code", "unknown")
        except (ValueError, AttributeError):
            code = "non_json"
        raise AssertionError(f"{label}: expected HTTP {status}; got {response.status_code} ({code})")
    if status == 204:
        print(label + ": PASS")
        return None
    try:
        result = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: expected JSON") from exc
    print(label + ": PASS")
    return result


def main() -> int:
    password = getpass.getpass("Staging password (hidden): ")
    if not password:
        print("STOP: staging password is required")
        return 2
    try:
        with httpx.Client(
            base_url=ORIGIN, timeout=75, follow_redirects=False,
            headers={"user-agent": "retire-v2-stage6-readonly-smoke/1"},
        ) as client:
            ready = expect(client.get("/healthz/ready"), 200, "READY")
            assert isinstance(ready, dict) and ready.get("status") == "ready"

            unauth = expect(client.get(CAPABILITY_PATH.format(client_id=1)),
                            401, "UNAUTHENTICATED_STAGE6_BLOCKED")
            assert isinstance(unauth, dict)

            login = expect(client.post(
                "/api/auth/login", json={"username": USERNAME, "password": password},
                headers={"origin": ORIGIN},
            ), 200, "LOGIN")
            assert isinstance(login, dict) and login.get("authenticated") is True

            session = expect(client.get("/api/auth/session"), 200, "SESSION")
            assert isinstance(session, dict) and session.get("authenticated") is True

            clients = expect(client.get("/api/clients"), 200, "CLIENT_LIST")
            assert isinstance(clients, list)
            actual_ids = {item.get("client_id") for item in clients if isinstance(item, dict)}
            if not set(EXPECTED_CLIENTS).issubset(actual_ids):
                raise AssertionError(f"Missing synthetic client A/B; IDs present: {sorted(actual_ids)}")
            print("SYNTHETIC_CLIENTS_A_B: PASS")

            for client_id in EXPECTED_CLIENTS:
                client_data = expect(
                    client.get(f"/api/clients/{client_id}"), 200,
                    f"CLIENT_{client_id}",
                )
                assert isinstance(client_data, dict) and client_data.get("client_id") == client_id
                response = expect(
                    client.get(CAPABILITY_PATH.format(client_id=client_id)), 200,
                    f"STAGE6_CAPABILITY_CLIENT_{client_id}",
                )
                if response != {"stage6_gross_scenario_results": True}:
                    raise AssertionError(f"Client {client_id}: Stage 6 capability not granted")

            missing = expect(client.get("/api/clients/999999999"), 404, "MISSING_CLIENT_BLOCKED")
            assert isinstance(missing, dict)

            csrf = session.get("csrf_token")
            if not isinstance(csrf, str) or not csrf:
                raise AssertionError("Authenticated session did not include CSRF token")
            expect(client.post(
                "/api/auth/logout",
                headers={"origin": ORIGIN, "x-rtdir-csrf": csrf},
            ), 204, "LOGOUT")
            expect(client.get("/api/auth/session"), 401, "SESSION_AFTER_LOGOUT_BLOCKED")

        print("STAGE6_LIVE_SMOKE_PASS")
        return 0
    except (httpx.HTTPError, AssertionError) as exc:
        print("STAGE6_LIVE_SMOKE_FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
