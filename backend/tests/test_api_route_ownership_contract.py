"""Protect the single-planner API against overlapping operation registrations.

This catches exact duplicate routes and equivalent path-parameter aliases
before the API is used as a future agent/MCP action catalogue. It does not
equate distinct domain operations merely because they share a verb.
"""
import re
from collections import defaultdict

from fastapi.routing import APIRoute
from app.main import create_app


def _shape(path: str) -> str:
    # {client_id} and {id} still address the same HTTP resource.
    return re.sub(r"\\{[^{}]+\\}", "{}", path)


def test_no_duplicate_canonical_api_operation_registration():
    app = create_app()
    registered = defaultdict(list)
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
            continue
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            registered[(method, _shape(route.path))].append(route.endpoint.__qualname__)
    duplicates = {str(key): handlers for key, handlers in registered.items()
                  if len(handlers) != 1}
    assert not duplicates, duplicates


def test_scenario_draft_routes_are_distinct_from_real_balance_mutations():
    app = create_app()
    scenario_paths = [
        route.path for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/clients/{client_id}/scenario-drafts")
    ]
    assert scenario_paths
    assert all("canonical-conversions" not in path for path in scenario_paths)


def test_fixation_calculation_has_single_discoverable_agent_operation():
    """Keep the legacy URL callable without exposing duplicate tool actions."""
    app = create_app()
    discovered = app.openapi()["paths"]
    canonical = "/api/clients/{client_id}/fixation/calculate"
    legacy = "/api/clients/{client_id}/fixation/validate"
    assert "post" in discovered[canonical]
    assert legacy not in discovered or "post" not in discovered[legacy]
    registered = [
        route for route in app.routes
        if isinstance(route, APIRoute) and route.path == legacy and "POST" in route.methods
    ]
    assert len(registered) == 1
    assert registered[0].include_in_schema is False


def test_health_probes_remain_callable_but_are_not_mcp_operations():
    app = create_app()
    schema = app.openapi()
    for path in ("/health", "/healthz/live", "/healthz/ready"):
        assert path not in schema["paths"]
        routes = [route for route in app.routes
                  if isinstance(route, APIRoute) and route.path == path]
        assert len(routes) == 1
        assert {"GET", "HEAD"} <= routes[0].methods
        assert routes[0].include_in_schema is False
