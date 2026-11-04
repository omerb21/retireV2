#!/usr/bin/env python3
"""Read-only, authenticated staging API smoke checks for RetireV2.

Usage:
  python scripts/staging_smoke.py --client-id 1

Set RT_SMOKE_USERNAME and RT_SMOKE_PASSWORD in the process environment, or
enter them interactively when prompted. No customer or test data is written.
No secrets, cookies or response bodies are printed.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


CHECKS = [
    ("session", "/api/auth/session", "object"),
    ("clients", "/api/clients", "array"),
    ("client-detail", "/api/clients/{id}", "object"),
    ("client-profile", "/api/clients/{id}/profile", "object"),
    ("pension-products", "/api/clients/{id}/pension-products", "array"),
    ("employment-records", "/api/clients/{id}/employment-records", "array"),
    ("grants", "/api/clients/{id}/grants", "array"),
    ("actual-capitalizations", "/api/clients/{id}/actual-capitalizations", "array"),
    ("documents", "/api/clients/{id}/documents", "array"),
    ("clearinghouse", "/api/clients/{id}/clearinghouse-snapshots", "array"),
    ("missing-items", "/api/clients/{id}/missing-items", "array"),
    ("capital-assets", "/api/clients/{id}/capital-assets?lifecycle_status=current", "array"),
    ("recurring-incomes", "/api/clients/{id}/recurring-incomes?lifecycle_status=current", "array"),
    ("recurring-expenses", "/api/clients/{id}/recurring-expenses?lifecycle_status=current", "array"),
    ("professional-source", "/api/clients/{id}/professional-source-snapshot", "object"),
    ("income-readiness-context", "/api/clients/{id}/retirement-income-readiness/context", "object"),
]


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://retirev2.onrender.com")
    parser.add_argument("--client-id", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    url = args.base_url.rstrip("/")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        parser.error("--base-url must be an HTTPS URL")
    if args.client_id <= 0:
        parser.error("--client-id must be positive")

    username = os.getenv("RT_SMOKE_USERNAME") or input("Username: ")
    password = os.getenv("RT_SMOKE_PASSWORD") or getpass.getpass("Password: ")
    if not username or not password:
        print("FAIL: missing credentials")
        return 2

    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(path: str, data: dict | None = None):
        headers = {"Accept": "application/json", "Origin": url}
        method = "GET"
        body = None
        if data is not None:
            method = "POST"
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(url + path, data=body, method=method, headers=headers)
        begin = time.monotonic()
        try:
            with opener.open(req, timeout=args.timeout) as response:
                status = response.status
                raw = response.read(2_000_000)
            parsed = json.loads(raw) if raw else None
            return status, parsed, int((time.monotonic() - begin) * 1000)
        except HTTPError as e:
            # Do not echo server bodies, cookies, or credentials.
            return e.code, None, int((time.monotonic() - begin) * 1000)
        except (URLError, TimeoutError, ValueError) as e:
            return "NETWORK_ERROR:" + type(e).__name__, None, int((time.monotonic() - begin) * 1000)

    status, health, ms = request("/healthz/ready")
    if status != 200 or not isinstance(health, dict) or health.get("status") != "ready":
        print(f"FAIL readiness: HTTP {status} ({ms}ms)")
        return 1
    print(f"PASS readiness: HTTP 200 ({ms}ms)")

    status, session, ms = request("/api/auth/login", {"username": username, "password": password})
    password = ""  # Avoid retaining the password in this function's local variable.
    if status != 200 or not isinstance(session, dict) or session.get("authenticated") is not True:
        print(f"FAIL authentication: HTTP {status} ({ms}ms)")
        return 1
    print(f"PASS authentication: HTTP 200 ({ms}ms)")

    failures = 0
    for name, path, expected_type in CHECKS:
        status, payload, ms = request(path.replace("{id}", str(args.client_id)))
        shape_ok = isinstance(payload, list if expected_type == "array" else dict)
        if status == 200 and shape_ok:
            print(f"PASS {name}: HTTP 200, {expected_type} ({ms}ms)")
        else:
            failures += 1
            print(f"FAIL {name}: HTTP {status}, expected {expected_type} ({ms}ms)")

    print(f"RESULT: {len(CHECKS) - failures}/{len(CHECKS)} authenticated read checks passed")
    print("SCOPE: read-only smoke; calculations, writes and browser rendering NOT verified")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
