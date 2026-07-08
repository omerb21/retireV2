# Package Completion Report Template

Use this template at the end of every future V2 package.

## 1. Package Identity

| Field | Value |
|---|---|
| Package ID |  |
| Package name |  |
| Repository |  |
| Branch |  |
| Starting commit |  |
| Ending commit |  |
| Scope authority |  |

## 2. Source Baseline

| Source artifact | Version, path, or commit | Role |
|---|---|---|
|  |  |  |

## 3. Files Changed

| File | Change type | Capability ID or exclusion reason |
|---|---|---|
|  | Added, modified, deleted, or renamed |  |

## 4. Capability Coverage Table

| Capability ID | Capability name | Source files | Runtime routes | UI paths/screens | Entities/models | Services/engines | Tests collected | Tests confirmed | Exceptions | Unmapped | Evidence status |
|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |  |  |

## 5. Runtime Evidence

| Route | Methods | Handler | Source router | Capability ID | Runtime observed | Notes |
|---|---|---|---|---|---|---|
|  |  |  |  |  | `YES`, `NO`, or `RUNTIME_ROUTE_EVIDENCE_NOT_AVAILABLE` |  |

## 6. UI Evidence

| UI path/screen | Component/source path | User action | Capability ID | Backend dependency | Evidence status | Notes |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## 7. Test Evidence

| Test path | Test name / module | Capability ID | Collected | Result | Evidence status | Failure/skip note |
|---|---|---|---|---|---|---|
|  |  |  | `YES` or `NO` | `PASSED`, `FAILED`, `SKIPPED`, `XFAILED`, `XPASSED`, `NOT_RUN`, or `NOT_COLLECTED` |  |  |

## 8. UNMAPPED Register

| Source item | Type | Why unmapped | Owner decision needed | Proposed handling | Status |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 9. Exclusions

| Item | Reason | Approval or authority | Acceptance boundary |
|---|---|---|---|
|  |  |  |  |

## 10. Known Evidence Exceptions

| Item | Exception type | Reason | Required follow-up |
|---|---|---|---|
|  |  |  |  |

## 11. Decision: May The Next Package Start?

Answer one:

```text
YES
NO
YES_WITH_EXPLICIT_EXCEPTIONS
```

Decision rationale:

```text

```

## Required Command Log

Record exact commands run for this package and their results.

Minimum required command:

```powershell
git status --short
```

If package scripts exist in a Node/React package:

```powershell
npm test
npm run build
```

If pytest is configured in a Python backend:

```powershell
pytest --collect-only -q
pytest -q
```

If route evidence is available, record the project-specific route listing command. If no route listing command exists, record:

```text
RUNTIME_ROUTE_EVIDENCE_NOT_AVAILABLE
```
