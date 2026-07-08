# Evidence Templates

These templates are reusable for future V2 package evidence.

## Route Evidence Template

| Route | Methods | Handler | Source router | Capability ID | Runtime observed | Notes |
|---|---|---|---|---|---|---|
| `/example` | `GET` | `handler_name` | `path/to/router.py` | `V1-CAP-000` | `YES`, `NO`, or `RUNTIME_ROUTE_EVIDENCE_NOT_AVAILABLE` | Runtime command, observation, or limitation |

Rules:

- `Runtime observed` may be `YES` only when the route or entry point was observed from app startup, generated route listing, or equivalent runtime inspection.
- Static source presence alone must not be recorded as runtime observation.
- If no route listing command exists, record `RUNTIME_ROUTE_EVIDENCE_NOT_AVAILABLE`.

## UI Evidence Template

| UI path/screen | Component/source path | User action | Capability ID | Backend dependency | Evidence status | Notes |
|---|---|---|---|---|---|---|
| `/example` or `ScreenName` | `path/to/component.tsx` | User-visible action | `V1-CAP-000` | API route/service or `None` | `UI_MAPPED`, `UNMAPPED`, or `EXCLUDED_WITH_REASON` | Browser/runtime observation, static mapping, or limitation |

Rules:

- UI evidence proves visible mapping only.
- UI evidence must not be used as proof that backend behavior, persistence, calculations, or tests are complete.
- Backend dependencies must be named when the UI action depends on backend behavior.

## Test Evidence Template

Allowed test result values:

```text
PASSED
FAILED
SKIPPED
XFAILED
XPASSED
NOT_RUN
NOT_COLLECTED
```

| Test path | Test name / module | Capability ID | Collected | Result | Evidence status | Failure/skip note |
|---|---|---|---|---|---|---|
| `path/to/test_file.py` | `test_name` or module name | `V1-CAP-000` | `YES` or `NO` | `PASSED`, `FAILED`, `SKIPPED`, `XFAILED`, `XPASSED`, `NOT_RUN`, or `NOT_COLLECTED` | `TEST_COLLECTED`, `TEST_CONFIRMED`, or `TEST_EXCEPTION` | Required for any non-passing or non-collected result |

Rules:

- `TEST_CONFIRMED` is allowed only for `PASSED`.
- `TEST_COLLECTED` is inventory evidence, not behavior confirmation.
- `TEST_EXCEPTION` is required for `FAILED`, `SKIPPED`, `XFAILED`, `XPASSED`, `NOT_RUN`, and `NOT_COLLECTED` unless the item is separately `EXCLUDED_WITH_REASON`.

## UNMAPPED Register Template

| Source item | Type | Why unmapped | Owner decision needed | Proposed handling | Status |
|---|---|---|---|---|---|
| `path/to/item` or runtime/UI/test item | Source, route, UI, entity, service, engine, test, document, or other | Explanation | Decision owner or approving authority needed | Map to capability, exclude with reason, defer, or investigate | `UNMAPPED`, `EXCLUDED_WITH_REASON`, or decision status |

Rules:

- No future package may claim completion while this register contains unexplained business or runtime items.
- Approved non-business exceptions must include the reason and acceptance boundary.
- Documentation-only items must not be converted into implementation evidence.
