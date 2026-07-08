# Capability Evidence Ledger Template

Use this ledger for every future V2 package that claims capability coverage.

Do not collapse source evidence, runtime evidence, UI evidence, and test evidence into one status. A capability may be partially mapped while still lacking runtime or test confirmation.

| Capability ID | Capability name | Source files | Runtime routes | UI paths/screens | Entities/models | Services/engines | Tests collected | Tests confirmed | Exceptions | Unmapped | Evidence status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `V1-CAP-000` | Example capability name | `path/to/source.py` | `METHOD /route` or `RUNTIME_ROUTE_EVIDENCE_NOT_AVAILABLE` | `/ui/path` or screen/action name | Model/entity names and producer/consumer notes | Service/engine names and consumer notes | Test paths or modules collected | Passing tests only | Failed/skipped/flaky/not-applicable notes | Unassigned items or `None` | `SOURCE_MAPPED`, `RUNTIME_REGISTERED`, `UI_MAPPED`, `TEST_COLLECTED`, `TEST_CONFIRMED`, `TEST_EXCEPTION`, `UNMAPPED`, `EXCLUDED_WITH_REASON` |

## Ledger Rules

- `Tests confirmed` may include only passing tests.
- Failed, skipped, flaky, not-run, not-collected, or not-applicable tests belong in `Exceptions`.
- `RUNTIME_ROUTE_EVIDENCE_NOT_AVAILABLE` must be used when no route listing or runtime inspection evidence is available.
- `Unmapped` must state `None` only after source, runtime, UI, entity, service/engine, and test accounting has been reviewed.
- `Evidence status` may contain multiple statuses only when each status is supported by the corresponding ledger columns.
