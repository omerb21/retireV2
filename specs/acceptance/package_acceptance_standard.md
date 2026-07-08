# Package Acceptance Standard

This standard is binding acceptance-gate infrastructure for future Retirement Planning V2 packages.

It defines when a V2 capability may be marked as covered. It does not mark any business capability as implemented. It does not authorize application code, business logic, UI, database, migration, or test changes.

## Evidence Statuses

| Status | Meaning | Positive implementation evidence? |
|---|---|---|
| `SOURCE_MAPPED` | Source exists and is linked to a capability. | Partial only. Source evidence must not be treated as runtime or test evidence. |
| `RUNTIME_REGISTERED` | A backend route or runtime entry point was observed from app startup or equivalent runtime inspection. | Yes, for runtime registration only. |
| `UI_MAPPED` | A visible UI route, screen, or action is linked to a capability. | Partial only. UI mapping does not prove backend behavior or test coverage. |
| `TEST_COLLECTED` | Pytest, Vitest, or an equivalent test runner sees the test during collection. | No. Collection proves inventory only. |
| `TEST_CONFIRMED` | The relevant collected test passed. | Yes, for the behavior asserted by that test only. |
| `TEST_EXCEPTION` | The test exists but failed, skipped, is flaky, is not applicable, or otherwise cannot be used as positive evidence. | No. Exceptions must be recorded and must not be counted as coverage. |
| `UNMAPPED` | The item exists but is not assigned to a capability. | No. Unmapped business or runtime items block package completion unless explicitly approved as non-business exceptions. |
| `EXCLUDED_WITH_REASON` | The item is intentionally excluded and the reason is recorded. | No, unless the reviewer accepts the exclusion for scope accounting only. |

## Capability Coverage Rule

A package may claim capability coverage only when every relevant source, runtime, UI, entity, service or engine, and test item is accounted for by one of the evidence statuses above.

Coverage requires all applicable evidence layers to be recorded separately:

- source evidence for changed or added source files;
- runtime evidence for backend routes or runtime entry points;
- UI evidence for visible pages, screens, actions, and flows;
- entity evidence for models and their producers and consumers;
- service or engine evidence for business services, engines, and their consumers;
- test evidence for collected and confirmed tests;
- exception evidence for failed, skipped, flaky, not-run, or not-applicable tests;
- unmapped evidence for any item not yet assigned to a capability.

## Future Package Acceptance Rules

| Check | Requirement |
|---|---|
| Source coverage | Every source file changed or added is linked to a capability, or excluded with reason. |
| Runtime coverage | Every backend route or runtime entry point is linked to a capability. |
| UI coverage | Every visible page/action is linked to a capability. |
| Entity coverage | Every model/entity has producer and consumer notes. |
| Service/engine coverage | Every business service or engine is linked to a capability and consumer. |
| Test coverage | Tests are collected and either pass or are recorded as exceptions. |
| Unmapped accounting | `UNMAPPED` is empty or contains explicit approved non-business exceptions. |
| Evidence boundary | Documentation alone cannot be used as positive implementation evidence. |

## Required Completion Decision

Every package completion report must answer:

```text
Decision: may the next package start?
```

Allowed answers:

```text
YES
NO
YES_WITH_EXPLICIT_EXCEPTIONS
```

`YES_WITH_EXPLICIT_EXCEPTIONS` is allowed only when every exception is recorded with a reason, owner decision, and acceptance boundary.
