"""Conservative import-graph guard for sealed historical execution services.

Scan the local app source tree, not a hand-selected list of services.
A module-level dependency is treated as reachable even when import is inside
a function; this intentionally over-approximates actual execution.
"""
import ast
from collections import deque
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
LEGACY_EXECUTION = {
    "app.services.m09_cashflow_service",
    "app.services.m09_scenario_subject_service",
    "app.services.m10_comparison_service",
}
ARCHIVE_API = {
    "app.api.m06_conversion_routes",
    "app.api.m09_cashflow_routes",
    "app.api.m10_comparison_routes",
}


def _modules():
    return {
        "app." + ".".join(path.relative_to(APP).with_suffix("").parts): path
        for path in APP.rglob("*.py")
        if path.name != "__init__.py"
    }


def _dependencies(module, modules):
    path = modules[module]
    result = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name in modules:
                    result.add(item.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module in modules:
                result.add(node.module)
            for item in node.names:
                full_name = node.module + "." + item.name
                if full_name in modules:
                    result.add(full_name)
    return result


def test_active_api_cannot_reach_historical_execution_modules():
    modules = _modules()
    assert LEGACY_EXECUTION <= set(modules), "Guard cannot resolve historical services"
    roots = sorted(
        module for module in modules
        if module.startswith("app.api.") and module.endswith("_routes")
        and module not in ARCHIVE_API
    )
    assert roots, "No active API roots found"
    adjacency = {name: _dependencies(name, modules) for name in modules}
    for root in roots:
        queue = deque([(root,)])
        visited = set()
        while queue:
            chain = queue.popleft()
            current = chain[-1]
            if current in visited:
                continue
            visited.add(current)
            assert current not in LEGACY_EXECUTION, "Historical engine reachable: " + " -> ".join(chain)
            for dependency in sorted(adjacency[current] - visited):
                queue.append((*chain, dependency))
