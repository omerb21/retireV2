# V2-IAP-01B-5 Exception Resolution Register

Package: `V2-IAP-01B-5`

Scope: planner-assumptions route contract review only.

## Resolved Exception

| Exception ID | Exception | Classification | Resolution status | Files changed | Evidence |
|---|---|---|---|---|---|
| `IAP01B5-BE-001` | `tests/test_v21_package_b_api.py::test_planner_assumption_route_absent` expected `404`, but the current route returned `422`. | `STALE_ROUTE_CONTRACT_EXPECTATION`, `ACCEPTED_LATER_PACKAGE_ROUTE` | Resolved. Test was renamed and rewritten to assert the explicit current Package D route-present validation contract. | `backend/tests/test_v21_package_b_api.py` | Replacement targeted test passed: 1 passed in 3.88s. Full `test_v21_package_b_api.py` passed: 39 passed in 107.08s. |

## Exact Current Failure

```text
tests/test_v21_package_b_api.py::test_planner_assumption_route_absent
assert 422 == 404
```

The request was:

```text
POST /api/clients/{client_id}/planner-assumptions
json={"title": "Not authorized"}
```

## Accepted Route Contract Evidence

| Evidence | Result |
|---|---|
| `6295270 v21-package-d: add assumptions and advisory missing information maintenance` | Accepted later package added planner-assumption API behavior. |
| `backend/tests/test_v21_package_d_api.py` | Tests create, list, read, update, lifecycle filter, validation, ownership, and no-delete/no-supersede behavior for `/api/clients/{client_id}/planner-assumptions`. |
| `backend/app/api/clients_routes.py` | Current routes include POST, GET list, GET one, and PUT for `/planner-assumptions`. |

## Replacement Contract

The rewritten test asserts a single explicit contract:

```text
POST /api/clients/{client_id}/planner-assumptions with only title returns 422
```

It also asserts the exact missing required body fields:

```text
assumption_category
assumption_value_text
rationale
owner
```

No generic `status_code in {404, 422}` allowance was used.

## Downstream Exceptions

| Exception ID | Downstream exception | Classification | Status | Evidence |
|---|---|---|---|---|
| `IAP01B5-DOWNSTREAM-001` | Full backend suite governance gate reports `backend/tests/test_v21_package_b_api.py` as an unapproved tracked change. | `GOVERNANCE_ALLOWLIST_FOLLOWUP` | Carried. Governance tests were forbidden for this package. | `python -m pytest -q`: `test_repository_has_only_approved_tracked_changes_for_governance_gate` failed. |

## Recommendation

```text
YES_WITH_EXPLICIT_DOWNSTREAM_EXCEPTION
```

V2-IAP-01B-5 may be accepted for the route-contract review scope because the stale absent-route assertion is replaced by one explicit accepted current contract.
