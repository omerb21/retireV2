"""Authenticated, non-mutating Scenario Permission Preview probe for Staging.

The probe uses the application's canonical login, session cookie and CSRF flow.
It never prints or persists credentials, cookies or the CSRF token.  The only
business request is the read-only permission-preview POST.

Example, from ``backend``::

    RETIRE_V2_STAGING_ORIGIN=https://staging.example \
    RETIRE_V2_STAGING_USERNAME=staging-user \
    RETIRE_V2_STAGING_PASSWORD=... \
    python scripts/staging_permission_preview_probe.py --confirm-staging \
      --evidence-json permission-preview-evidence.json
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx


DEFAULT_CLIENT_ID = 7
DEFAULT_PRODUCT_ID = "96edb78aaa734d0c845ae8f6ee36da50"
DEFAULT_ACTION = "pension"
DEFAULT_EFFECTIVE_DATE = "2026-12-15"


class ProbeError(RuntimeError):
    """A technical or authentication failure, with no secret-bearing detail."""


def _json_object(response: httpx.Response, label: str) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise ProbeError(f"{label}: NON_JSON_RESPONSE (HTTP {response.status_code})") from exc
    if not isinstance(body, dict):
        raise ProbeError(f"{label}: INVALID_JSON_SHAPE (HTTP {response.status_code})")
    return body


def _response_code(body: Mapping[str, Any]) -> str | None:
    code = body.get("code")
    return code if isinstance(code, str) and code else None


def _validate_origin(origin: str) -> str:
    value = origin.rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ProbeError("STAGING_ORIGIN_INVALID")
    return value


def _permission_rows(body: Mapping[str, Any]) -> list[dict[str, str]]:
    raw = body.get("components")
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rows.append({
            "component_code": str(item.get("component_code", "")),
            "permission_status": str(item.get("permission_status", "")),
            "reason_code": str(item.get("reason_code", "")),
            "reason_he": str(item.get("reason_he", "")),
        })
    return rows


def run_probe(
    client: Any,
    *,
    origin: str,
    username: str,
    password: str,
    client_id: int = DEFAULT_CLIENT_ID,
    product_id: str = DEFAULT_PRODUCT_ID,
    action: str = DEFAULT_ACTION,
    effective_date: str = DEFAULT_EFFECTIVE_DATE,
) -> dict[str, Any]:
    """Run the probe in one cookie-owning client and return sanitized evidence."""
    origin = _validate_origin(origin)
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"origin": origin},
    )
    login_body = _json_object(login, "LOGIN")
    if login.status_code != 200 or login_body.get("authenticated") is not True:
        raise ProbeError(
            f"LOGIN_REJECTED (HTTP {login.status_code}, code={_response_code(login_body) or 'unknown'})"
        )

    csrf: str | None = None
    logout_status: int | None = None
    try:
        session = client.get("/api/auth/session")
        session_body = _json_object(session, "SESSION")
        csrf_value = session_body.get("csrf_token")
        if (
            session.status_code != 200
            or session_body.get("authenticated") is not True
            or not isinstance(csrf_value, str)
            or not csrf_value
        ):
            raise ProbeError(
                f"SESSION_UNAVAILABLE (HTTP {session.status_code}, "
                f"code={_response_code(session_body) or 'unknown'})"
            )
        csrf = csrf_value
        response = client.post(
            f"/api/clients/{client_id}/scenario-conversions/permission-preview",
            json={
                "product_id": product_id,
                "action": action,
                "effective_date": effective_date,
            },
            headers={"origin": origin, "x-rtdir-csrf": csrf},
        )
        body = _json_object(response, "PERMISSION_PREVIEW")
        if response.status_code in {401, 403} or response.status_code >= 500:
            raise ProbeError(
                f"PERMISSION_PREVIEW_TECHNICAL_FAILURE (HTTP {response.status_code}, "
                f"code={_response_code(body) or 'unknown'})"
            )
        if response.status_code == 200:
            expected = {
                "schema_version": "SCENARIO_PERMISSION_PREVIEW_V1",
                "client_id": client_id,
                "product_id": product_id,
                "action": action,
                "effective_date": effective_date,
            }
            mismatched = [key for key, value in expected.items() if body.get(key) != value]
            if mismatched:
                raise ProbeError("PERMISSION_RESPONSE_IDENTITY_MISMATCH: " + ",".join(mismatched))

        return {
            "schema_version": "STAGING_PERMISSION_PREVIEW_PROBE_EVIDENCE_V1",
            "target": {
                "client_id": client_id,
                "product_id": product_id,
                "action": action,
                "effective_date": effective_date,
            },
            "authenticated_session": True,
            "http_status": response.status_code,
            "response_code": _response_code(body),
            "overall_status": body.get("overall_status") if response.status_code == 200 else None,
            "permissions": _permission_rows(body),
            "field_paths": body.get("field_paths") if isinstance(body.get("field_paths"), list) else [],
        }
    finally:
        if csrf:
            logout = client.post(
                "/api/auth/logout",
                headers={"origin": origin, "x-rtdir-csrf": csrf},
            )
            logout_status = logout.status_code
        if logout_status not in {None, 204, 401}:
            raise ProbeError(f"LOGOUT_UNCONFIRMED (HTTP {logout_status})")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--origin", default=os.getenv("RETIRE_V2_STAGING_ORIGIN", ""))
    parser.add_argument("--username", default=os.getenv("RETIRE_V2_STAGING_USERNAME", ""))
    parser.add_argument("--client-id", type=int, default=DEFAULT_CLIENT_ID)
    parser.add_argument("--product-id", default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--action", choices=("pension", "capital_asset"), default=DEFAULT_ACTION)
    parser.add_argument("--effective-date", default=DEFAULT_EFFECTIVE_DATE)
    parser.add_argument("--evidence-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if not args.confirm_staging:
        print("BLOCKED: --confirm-staging is required")
        return 2
    password = os.getenv("RETIRE_V2_STAGING_PASSWORD") or getpass.getpass(
        "Staging password (hidden): "
    )
    if not args.username or not password:
        print("BLOCKED: staging username and password are required")
        return 2
    try:
        origin = _validate_origin(args.origin)
        with httpx.Client(
            base_url=origin,
            timeout=75,
            follow_redirects=False,
            headers={"user-agent": "retire-v2-permission-probe/1"},
        ) as client:
            evidence = run_probe(
                client,
                origin=origin,
                username=args.username,
                password=password,
                client_id=args.client_id,
                product_id=args.product_id,
                action=args.action,
                effective_date=args.effective_date,
            )
        serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
        if args.evidence_json:
            args.evidence_json.write_text(serialized + "\n", encoding="utf-8")
        print(serialized)
        return 0
    except (httpx.HTTPError, ProbeError) as exc:
        print("PERMISSION_PREVIEW_PROBE_FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
