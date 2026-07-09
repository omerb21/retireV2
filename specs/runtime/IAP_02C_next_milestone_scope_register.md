# V2-IAP-02C Next Milestone Scope Register

Package: `V2-IAP-02C`

Scope: Product Decision for next V2 milestone only.

## Milestone Selection

| Field | Decision |
|---|---|
| Next milestone selected | `NO` |
| Milestone name | `NOT_SELECTED` |
| Version label | `NOT_SELECTED` |
| Implementation planning authorized | `NO` |
| First possible implementation package name | `NOT_ASSIGNED_BLOCKED_UNTIL_PRODUCT_DIRECTION_SELECTED` |
| Product decision status | `BLOCKED_BY_UNANSWERED_DIRECTION_SELECTION` |

## Intended User And Audience

| Audience field | Decision |
|---|---|
| Intended user | `NOT_SELECTED` |
| Audience | `NOT_SELECTED` |
| Current preserved audience boundary | Existing V2.1 Milestone 1 remains internal planner-facing only. |
| Client-facing audience authorized | `NO` |

## Included Capability Direction

No next implementation capability direction is selected.

Candidate directions remain unselected:

- V2.1 Package F continuation.
- V2.2 / Milestone 2 broader retirement planning foundation.
- Pension portfolio / pension holdings review expansion.
- Pension analysis record expansion.
- Clearinghouse/import/OCR/document evidence repository.
- Pension/tax/cashflow/scenario engines or scenario comparison.
- Client-facing reports, portal, export, PDF, print, email, or 161D output.
- Fixation Rights enhancement or reopening.
- Source/evidence/capability coverage consolidation.

## Explicit In Scope

Only the following are in scope for V2-IAP-02C:

- answer the IAP-02B Product Decision questions from existing repository evidence;
- record that no next implementation milestone is selected;
- preserve V2.1 Milestone 1 and V2.0/Fixation Rights closure boundaries;
- identify blocking unanswered Product Decision questions;
- recommend a next product-direction selection package.

No business implementation scope is in scope.

## Explicit Out Of Scope

The following remain out of scope:

- V1 changes or copying;
- source code changes;
- test changes;
- backend app code changes;
- frontend code changes;
- migrations, models, schemas, services, UI, business logic, package files, or dependencies;
- implementation IAP creation;
- business routes;
- UI;
- database tables;
- calculations;
- imports, OCR, parsing, document storage, clearinghouse integration, external integrations, or evidence repositories;
- client-facing output;
- recommendations, readiness, eligibility, approvals, suitability, execution workflow, or follow-up;
- Fixation Rights reopening or changes to FixationInput, review conversion, calculations, save-run behavior, stale/mismatch behavior, audit, snapshots, results, or engine behavior.

## Source-Of-Truth Rules

| Area | Rule |
|---|---|
| Product authority | Only approved V2 planning/product-decision artifacts can authorize implementation. |
| V1 evidence | V1 is read-only reference only and cannot authorize V2 behavior. |
| Implementation evidence | Documentation alone is not positive implementation evidence under `specs/acceptance/package_acceptance_standard.md`. |
| Existing V2.1 facts | Facts, planner assumptions, source/verification statuses, advisory missing information, and analysis records remain separate unless a future Product Decision authorizes relationships. |
| Existing Fixation Rights | Completed V2.0/Fixation Rights behavior remains closed and protected. |

## Authorization Flags

| Question | Decision |
|---|---|
| Are calculations authorized? | `NO` |
| Are imports/OCR/clearinghouse authorized? | `NO` |
| Is client-facing output authorized? | `NO` |
| May Fixation Rights be reopened? | `NO` |
| Is implementation planning authorized? | `NO` |

## Blocking Unanswered Scope Items

Implementation planning is blocked until a later Product Decision selects and answers:

- next milestone name and version label;
- continuation vs new milestone vs governance-only direction;
- included capability IDs;
- selected candidate domain;
- intended user/audience;
- package sequence;
- package-specific acceptance evidence;
- whether a consolidated capability coverage matrix is required;
- first execution package file boundaries and stop conditions.

## Proposed Next Package

```text
V2-IAP-02D_PRODUCT_DIRECTION_SELECTION
```

Package nature: product decision only.

Purpose: select exactly one next product direction or explicitly select governance-only coverage consolidation before implementation planning.
