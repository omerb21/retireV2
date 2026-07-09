# V2-IAP-02C Decision Question Answers

Package: `V2-IAP-02C`

Scope: Product Decision for next V2 milestone only.

This document answers the Product Decision questions carried forward from V2-IAP-02B. It does not authorize implementation.

## Decision Answers

| Question ID | Product Decision question | Answer | Status |
|---|---|---|---|
| `IAP02C-Q001` | What is the exact next milestone name and version label, if any, after V2.1 Milestone 1? | No exact next implementation milestone name or version label is approved in the artifacts read. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q002` | Is the next work a continuation of V2.1, a new V2.2/Milestone 2, or a governance-only evidence consolidation package? | Not decided by repository authority. IAP-02B identified multiple candidates, but no artifact selects one. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q003` | Which capability IDs are included, and are new capability IDs required? | No next milestone is selected, so no included capability IDs or new capability IDs are authorized. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q004` | Which candidate domain is selected? | None selected. Candidate domains remain pension portfolio/review, pension analysis records, imports/documents/OCR/clearinghouse, pension/tax/cashflow/scenario engines, client-facing output, Fixation Rights remediation, or governance coverage consolidation. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q005` | What is explicitly in scope at the product level? | For implementation: nothing. For this Product Decision package: documenting that no next milestone direction is selected and that implementation planning remains blocked. | `ANSWERED_FOR_02C_ONLY` |
| `IAP02C-Q006` | What is explicitly out of scope? | All implementation is out of scope: source code, tests, backend/frontend, migrations, models, schemas, services, UI, business logic, routes, database tables, calculations, imports, OCR, clearinghouse integration, client-facing output, and Fixation Rights changes. | `ANSWERED` |
| `IAP02C-Q007` | What user role and audience is the milestone for? | No next milestone is selected, so no milestone audience is approved. Existing V2.1 Milestone 1 audience was internal planner-facing only. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q008` | What is the source-of-truth rule for every new datum, status, output, and decision? | No new datum, status, output, or decision is authorized. Existing rules remain: build from approved V2 specs, V1 reference is not authority, documentation alone is not implementation evidence, and completed Fixation Rights outputs retain their existing authority boundaries. | `ANSWERED_FOR_CURRENT_BOUNDARY` |
| `IAP02C-Q009` | Are source status, verification state, planner assumptions, advisory missing information, and analysis records still separate, and what relationships are allowed? | For existing V2.1 scope, they remain separate. No new relationships are authorized for a future milestone until a selected direction defines them. | `ANSWERED_FOR_CURRENT_BOUNDARY` |
| `IAP02C-Q010` | Are any calculations authorized? | No. No pension, tax, cashflow, retirement income, withdrawal, scenario, readiness, eligibility, recommendation, or other new calculation is authorized. | `ANSWERED` |
| `IAP02C-Q011` | Are imports, OCR, parsing, document storage, clearinghouse integration, or external integrations authorized? | No. These remain explicitly excluded unless a later Product Decision authorizes them. | `ANSWERED` |
| `IAP02C-Q012` | Are client-facing outputs authorized? | No. Client-facing reports, portal, export, PDF, print, email, 161D output, or document generation are not authorized. | `ANSWERED` |
| `IAP02C-Q013` | Are completed V2.0/Fixation Rights flows allowed to change? | No. Completed V2.0/Fixation Rights flows remain closed and protected unless separate concrete contradiction/regression evidence is approved. | `ANSWERED` |
| `IAP02C-Q014` | What package sequence is approved for the selected milestone? | None. No selected milestone means no package sequence is approved. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q015` | What acceptance evidence is required for each package? | The acceptance standard applies to any future package, but no package-specific evidence plan can be set until a milestone and package sequence are selected. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q016` | Must a consolidated V1-to-V2 capability coverage matrix be created before implementation? | Not decided. IAP-02A found no single current matrix; IAP-02B classified coverage consolidation as a possible governance-only package. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q017` | What files or directories are allowed and forbidden for the first execution package? | No first implementation package is authorized, so no implementation file scope is approved. Any next package before implementation must remain governance/product-decision only unless a milestone is selected. | `BLOCKING_UNANSWERED` |
| `IAP02C-Q018` | What stop conditions require escalation rather than implementation? | Stop if any next step requires source code, tests, backend/frontend, migrations, models, schemas, services, UI, business logic, routes, database tables, calculations, imports, OCR, clearinghouse integration, client-facing output, Fixation Rights changes, V1 copying, or V1-derived authorization before a milestone decision exists. | `ANSWERED` |

## Blocking Unanswered Questions

The following decision questions block implementation planning:

- `IAP02C-Q001`
- `IAP02C-Q002`
- `IAP02C-Q003`
- `IAP02C-Q004`
- `IAP02C-Q007`
- `IAP02C-Q014`
- `IAP02C-Q015`
- `IAP02C-Q016`
- `IAP02C-Q017`

## Decision Summary

```text
NO_NEXT_IMPLEMENTATION_MILESTONE_SELECTED
```

No implementation planning is authorized.
