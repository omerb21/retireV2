"""Fail when a new mutating API is added without explicit ownership review.

POST may be a preview/read or a financial calculation, not necessarily a DB write.
This is a bounded inventory, NOT proof that every distinct URL has unique semantics.
"""
from fastapi.routing import APIRoute

from app.main import create_app

# Reviewed 2026-10-26. Changes require assigning an explicit business owner
# before exposing new operations to a future MCP agent.
KNOWN_MUTATING_OPERATIONS = {
    "auth": {
        "POST /login", "POST /logout",
    },
    "canonical-conversions": {
        "POST /preview", "POST /", "POST /{conversion_id}/reverse",
    },
    "clients": {
        "POST /", "PUT /{client_id}/case", "PUT /{client_id}/profile",
        "POST /{client_id}/clearinghouse-snapshots",
        "PUT /{client_id}/clearinghouse-snapshots/{clearinghouse_snapshot_id}/verification",
        "POST /{client_id}/documents", "PUT /{client_id}/documents/{document_id}/verification",
        "POST /{client_id}/capital-assets", "PUT /{client_id}/capital-assets/{capital_asset_id}",
        "POST /{client_id}/recurring-incomes", "PUT /{client_id}/recurring-incomes/{recurring_income_id}",
        "POST /{client_id}/recurring-expenses", "PUT /{client_id}/recurring-expenses/{recurring_expense_id}",
        "POST /{client_id}/retirement-timing-work-intentions",
        "PUT /{client_id}/retirement-timing-work-intentions/{retirement_timing_work_intention_id}",
        "POST /{client_id}/planner-assumptions", "PUT /{client_id}/planner-assumptions/{planner_assumption_id}",
        "POST /{client_id}/missing-items", "PUT /{client_id}/missing-items/{missing_data_item_id}",
        "POST /{client_id}/employment-records", "POST /{client_id}/historical-employment-settlements",
        "PUT /{client_id}/employment-records/{employment_record_id}",
        "DELETE /{client_id}/employment-records/{employment_record_id}",
        "POST /{client_id}/employment-records/{employment_record_id}/grants",
        "POST /{client_id}/grants", "PUT /{client_id}/grants/{grant_id}",
        "POST /{client_id}/grants/{grant_id}/employment-link",
        "DELETE /{client_id}/grants/{grant_id}",
        "POST /{client_id}/actual-capitalizations", "PUT /{client_id}/actual-capitalizations/{capitalization_id}",
        "DELETE /{client_id}/actual-capitalizations/{capitalization_id}",
    },
    "fixation-m07": {"POST /eligibility-date-revisions"},
    "fixation": {
        "POST /fixation/review/validate", "POST /fixation/review/convert",
        "POST /clients/{client_id}/fixation/validate", "POST /clients/{client_id}/fixation/calculate",
        "POST /fixation/save",
        "POST /clients/{client_id}/fixation/runs/{run_id}/internal-planner-judgment",
        "POST /clients/{client_id}/fixation/runs/{run_id}/dependency-comparison",
    },
    "pension-products": {
        "POST /", "POST /imports", "POST /save-selected", "PUT /{product_id}", "DELETE /{product_id}",
    },
    "planning-input": {
        "PUT /base-date", "PUT /income-resolutions/{income_id}", "PUT /target-date",
        "PUT /projection-basis/{capital_asset_id}", "PUT /projection-basis/{capital_asset_id}/clear",
    },
    "professional-source-snapshot": {
        "POST /canonical-pension-sources/manual", "PUT /canonical-pension-sources/manual/{source_id}",
        "DELETE /canonical-pension-sources/manual/{source_id}",
        "PUT /canonical-pension-sources/conversion/{destination_id}/temporal-authority",
    },
    "retirement-income-readiness": {
        "PUT /target", "POST /comparison", "PUT /source-bases/{source_id}",
    },
    "scenario-drafts": {
        "POST /", "POST /{scenario_id}/duplicate", "PUT /{scenario_id}",
        "POST /{scenario_id}/rename", "POST /{scenario_id}/archive",
    },
    "scenario-permission-preview": {"POST /permission-preview"},
}


def test_every_write_or_post_is_listed_for_business_owner_review():
    # Route tags and full paths are derived from FastAPI registration, not
    # static scan of source decorators (which can miss included routers).
    app = create_app()
    observed = {}
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in sorted(route.methods & {"POST", "PUT", "PATCH", "DELETE"}):
            # Keyed by tag and relative path for ease of review.
            tag = route.tags[0] if route.tags else "UNTAGGED"
            observed.setdefault(tag, set()).add((method, route.path))
    expected = {}
    for tag, values in KNOWN_MUTATING_OPERATIONS.items():
        expected[tag] = values
    # Normalize by identifying the correct prefix based on the registered
    # path rather than assuming a tag is itself the prefix.
    paths = {(method, path) for methods in observed.values() for method, path in methods}
    assert len(paths) == sum(len(v) for v in observed.values()), "One mutating operation registered under multiple tags"
    # Detect any unreviewed mutation by tag+route leaf. Exact full route
    # spellings are already guarded by test_api_route_ownership_contract.
    canonical_prefixes = {
        "auth": "/api/auth",
        "canonical-conversions": "/api/clients/{client_id}/canonical-conversions",
        "clients": "/api/clients",
        "fixation-m07": "/api/clients/{client_id}/fixation/m07",
        "fixation": "/api",
        "pension-products": "/api/clients/{client_id}/pension-products",
        "planning-input": "/api/clients/{client_id}/retirement-planning-input",
        "professional-source-snapshot": "/api/clients/{client_id}",
        "retirement-income-readiness": "/api/clients/{client_id}/retirement-income-readiness",
        "scenario-drafts": "/api/clients/{client_id}/scenario-drafts",
        "scenario-permission-preview": "/api/clients/{client_id}/scenario-conversions",
    }
    allowlist = {
        (method, prefix + (suffix if suffix != "/" else ""))
        for tag, operations in expected.items()
        for prefix in [canonical_prefixes[tag]]
        for operation in operations
        for method, suffix in [operation.split(" ", 1)]
    }
    assert paths == allowlist, {
        "unreviewed_operations": sorted(paths - allowlist),
        "no_longer_registered": sorted(allowlist - paths),
    }
