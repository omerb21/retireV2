"""Stage 6 staging-only synthetic workflow: canonical sources, drafts and isolation.

Run from backend:
  .venv-py311\\Scripts\\python.exe scripts\\stage6_live_workflow.py

Uses the same isolated Render review service as stage6_live_smoke.py.
It creates or reuses *named synthetic* products and drafts for fixture clients
1 and 2. It NEVER computes, stores or asserts a fictional approved pension.
The expected Stage 6 result is BLOCKED until professional evidence exists.
Re-running uses the named records and does not duplicate them.
"""
from __future__ import annotations

import getpass
import os
from typing import Any

import httpx

from stage6_live_smoke import ORIGIN, USERNAME

COMPONENT_CODES = (
    "פיצויים_מעסיק_נוכחי",
    "פיצויים_לאחר_התחשבנות",
    "פיצויים_שלא_עברו_התחשבנות",
    "פיצויים_ממעסיקים_קודמים_רצף_זכויות",
    "פיצויים_ממעסיקים_קודמים_רצף_קצבה",
    "תגמולי_עובד_עד_2000",
    "תגמולי_עובד_אחרי_2000",
    "תגמולי_עובד_אחרי_2008_לא_משלמת",
    "תגמולי_מעביד_עד_2000",
    "תגמולי_מעביד_אחרי_2000",
    "תגמולי_מעביד_אחרי_2008_לא_משלמת",
)
SELECTED_COMPONENT = "תגמולי_עובד_אחרי_2000"
FIXTURE_NAMES = {
    1: ("STAGE6 SYNTH PRODUCT A", "STAGE6 SYNTH ALT A1", "STAGE6 SYNTH ALT A2"),
    2: ("STAGE6 SYNTH PRODUCT B", "STAGE6 SYNTH ALT B1"),
}


def request(
    client: httpx.Client, method: str, path: str, *,
    body: dict[str, Any] | None = None, csrf: str | None = None,
    statuses: tuple[int, ...] = (200,),
) -> Any:
    headers: dict[str, str] = {}
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not csrf:
            raise AssertionError(f"{method} requires signed CSRF session")
        headers.update({"origin": ORIGIN, "x-rtdir-csrf": csrf})
    response = client.request(method, path, json=body, headers=headers)
    if response.status_code not in statuses:
        try:
            error = response.json()
            code = error.get("code", error.get("detail", {}).get("code", "unknown"))
        except (ValueError, AttributeError):
            code = "non_json"
        raise AssertionError(
            f"{method} {path}: HTTP {response.status_code}; code={code}"
        )
    if response.status_code == 204:
        return None
    return response.json()


def synthetic_product(
    client: httpx.Client, client_id: int, csrf: str,
) -> dict[str, Any]:
    name = FIXTURE_NAMES[client_id][0]
    path = f"/api/clients/{client_id}/pension-products"
    products = request(client, "GET", path)
    matching = [row for row in products if row["product_name"] == name]
    if len(matching) > 1:
        raise AssertionError(f"Duplicate synthetic product name for client {client_id}")
    meta = {
        "product_name": name,
        "product_type": "קרן פנסיה",
        "provider_name": "STAGE6 SYNTH ONLY",
        "provider_identifier": None,
        "account_reference": f"STAGE6-SYNTH-{client_id}",
        "start_date": "2010-01-01",
        "statement_date": "2026-10-31",
        "historical_employers": [],
        "reported_product_total": "200000.00",
        "reported_rewards_total": "200000.00",
        "reported_severance_total": "0.00",
    }
    product = matching[0] if matching else request(
        client, "POST", path, body=meta, csrf=csrf, statuses=(201,),
    )
    if product.get("client_id") != client_id or product.get("source_kind") != "manual":
        raise AssertionError("Synthetic product client/source binding mismatch")
    desired = {key: ("200000.00" if key == SELECTED_COMPONENT else "0.00")
               for key in COMPONENT_CODES}
    if product.get("components") != desired:
        product = request(
            client, "PUT", f"{path}/{product['product_id']}",
            csrf=csrf, body={**meta, "expected_version": product["version"],
                             "components": desired},
        )
    components = [
        row for row in product["conversion_components"]
        if row["component_code"] == SELECTED_COMPONENT
    ]
    if len(components) != 1 or str(components[0]["balance"]) != "200000.00":
        raise AssertionError("Canonical source component mismatch")
    print(f"CLIENT_{client_id}_SYNTHETIC_PENSION_SOURCE: PASS")
    return {
        "product_id": product["product_id"],
        "component_id": components[0]["component_id"],
    }


def synthetic_draft(
    client: httpx.Client, client_id: int, name: str, amount: str,
    source: dict[str, str], csrf: str,
) -> dict[str, Any]:
    prefix = f"/api/clients/{client_id}/scenario-drafts"
    rows = request(client, "GET", prefix)
    matching = [row for row in rows if row["name"] == name]
    if len(matching) > 1:
        raise AssertionError(f"Duplicate synthetic scenario name for client {client_id}")
    draft = matching[0] if matching else request(
        client, "POST", prefix, body={"name": name}, csrf=csrf,
    )
    if draft["client_id"] != client_id or draft["status"] != "draft":
        raise AssertionError("Synthetic draft client/status mismatch")
    desired = {
        "source_product_id": source["product_id"],
        "source_component_id": source["component_id"],
        "component_code": SELECTED_COMPONENT,
        "amount": amount,
        "action": "pension",
        "effective_date": "2027-07-01",
    }
    decisions = draft["decisions"]
    if not decisions:
        draft = request(
            client, "PUT", f"{prefix}/{draft['scenario_id']}",
            body={"expected_version": draft["version"], "name": name,
                  "decisions": [desired]},
            csrf=csrf,
        )
    elif len(decisions) != 1 or any(
        decisions[0].get(key) != value for key, value in desired.items()
    ):
        raise AssertionError("Existing named draft was modified unexpectedly")
    decision = draft["decisions"][0]
    if (draft["client_id"] != client_id
            or decision["source_fingerprint_at_review"] is None
            or decision["validation_state"] != "unverified"):
        raise AssertionError("Scenario source/staleness identity not recorded")
    print(f"CLIENT_{client_id}_{name.replace(' ', '_')}: PASS")
    return draft


def blocked_result(
    client: httpx.Client, client_id: int, draft: dict[str, Any],
) -> None:
    scenario_id = draft["scenario_id"]
    decision_id = draft["decisions"][0]["decision_id"]
    prefix = f"/api/clients/{client_id}/scenario-drafts"
    row = request(
        client, "GET",
        f"{prefix}/{scenario_id}/pension-decisions/{decision_id}/gross-estimate",
    )
    if (row.get("schema_version") != "STAGE6_SINGLE_PENSION_DECISION_ESTIMATE_V1"
            or row.get("client_id") != client_id
            or row.get("scenario_id") != scenario_id
            or row.get("decision_id") != decision_id
            or row.get("result_state") != "BLOCKED"
            or row.get("execution_allowed") is not False
            or row.get("monthly_estimate_gross_ils") is not None
            or not row.get("blockers")):
        raise AssertionError("Stage 6 gross estimate failed closed-result contract")
    aggregate = request(client, "GET", f"{prefix}/{scenario_id}/pension-gross-summary")
    if (aggregate.get("schema_version") != "STAGE6_PENSION_DECISION_AGGREGATE_V1"
            or aggregate.get("client_id") != client_id
            or aggregate.get("scenario_id") != scenario_id
            or aggregate.get("aggregation_state") != "BLOCKED"
            or aggregate.get("monthly_pension_gross_total_ils") is not None
            or aggregate.get("execution_allowed") is not False):
        raise AssertionError("Stage 6 aggregation invented a gross pension result")
    print(f"CLIENT_{client_id}_STAGE6_BLOCKED_UNTIL_PROFESSIONAL_REVIEW: PASS")


def main() -> int:
    password = os.environ.get("STAGE6_SMOKE_PASSWORD") or getpass.getpass(
        "Staging password (hidden): "
    )
    if not password:
        print("STOP: Staging password is required")
        return 2
    try:
        with httpx.Client(base_url=ORIGIN, timeout=90, follow_redirects=False) as client:
            response = client.post(
                "/api/auth/login",
                json={"username": USERNAME, "password": password},
                headers={"origin": ORIGIN},
            )
            if response.status_code != 200:
                raise AssertionError(f"Staging login rejected: HTTP {response.status_code}")
            session = request(client, "GET", "/api/auth/session")
            csrf = session.get("csrf_token")
            if session.get("authenticated") is not True or not csrf:
                raise AssertionError("Staging session/CSRF unavailable")
            print("AUTHENTICATED_STAGING: PASS")

            fixtures = {}
            for client_id in (1, 2):
                meta = request(client, "GET", f"/api/clients/{client_id}")
                if (meta.get("client_id") != client_id
                        or meta.get("id_number") != f"STAGE6_SYNTH_{'A' if client_id == 1 else 'B'}_20261105"):
                    raise AssertionError("Refusing to modify non-synthetic client")
                source = synthetic_product(client, client_id, csrf)
                names = FIXTURE_NAMES[client_id][1:]
                amounts = ("100000.00", "140000.00") if client_id == 1 else ("90000.00",)
                fixtures[client_id] = [
                    synthetic_draft(client, client_id, name, amount, source, csrf)
                    for name, amount in zip(names, amounts)
                ]

            for client_id in (1, 2):
                for draft in fixtures[client_id]:
                    blocked_result(client, client_id, draft)

            # A scenario belonging to B must never be read via A, and vice versa.
            a = fixtures[1][0]["scenario_id"]
            b = fixtures[2][0]["scenario_id"]
            request(client, "GET", f"/api/clients/2/scenario-drafts/{a}",
                    statuses=(404,))
            request(client, "GET", f"/api/clients/1/scenario-drafts/{b}",
                    statuses=(404,))
            print("CROSS_CLIENT_SCENARIO_ISOLATION: PASS")
            request(client, "POST", "/api/auth/logout", csrf=csrf, statuses=(204,))
            print("STAGE6_SYNTHETIC_WORKFLOW_PASS")
        return 0
    except (httpx.HTTPError, AssertionError, ValueError, KeyError, TypeError) as exc:
        print("STAGE6_SYNTHETIC_WORKFLOW_FAILED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
