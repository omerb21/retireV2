# V2 Product Decision For Next Milestone

Package: V2-IAP-02H_PRODUCT_DECISION_FOR_NEXT_MILESTONE
Status: PRODUCT_SCOPE_DECISION_ONLY
Repository HEAD reviewed: a138cd98eef6737a09c42a76600d28477f6cb4ff

## Current State

- HEAD: `a138cd9 docs: add V2 product discovery options`
- 02D status: closed.
- GOV-01 status: closed.
- 02F status: closed.
- 02G status: closed.
- Implementation authorization before this decision: NO.
- This package does not implement, does not create contracts, does not reopen V1/V2 mapping, and does not authorize code changes.

## Decision Criteria Applied

The accepted 02G discovery options were evaluated using the required criteria:

1. Lowest risk first.
2. Internal-only before client-facing.
3. No calculations unless unavoidable.
4. No tax, cashflow, scenario, projection, OCR, import, clearinghouse integration, report/PDF/161D, LLM, recommendation, or client-facing output unless explicitly required and explicitly authorized.
5. Prefer options that can lead to a narrow contract package.
6. Prefer options that improve V2 planning/product structure without reopening V1/V2 mapping.
7. Reject options that require unresolved legal/tax/formula/source/output authority.
8. Choose NO-GO if no option can be selected safely.

## Options Reviewed

| Option ID | Option name | Risk | Classification from 02G | Calculations involved | Client-facing output involved | Imports/OCR/clearinghouse involved | Reports/PDF/161D involved | LLM/recommendations involved | Decision result | Basis |
|---|---|---|---|---|---|---|---|---|---|---|
| OPT-A | Route-level fixation utility parity | MEDIUM | NEEDS_PRODUCT_DECISION | YES | NO | NO | NO | NO | Rejected | Requires calculation-related route contract authority and could create V1 route parity without clear V2 need. |
| OPT-B | Source / verification / document metadata foundation | MEDIUM | NEEDS_PRODUCT_DECISION | NO | NO | YES | NO | NO | Rejected | Touches source/document/clearinghouse boundary and requires source-of-truth and integration-adjacent decisions. |
| OPT-C | Pension analysis expansion | MEDIUM | NEEDS_PRODUCT_DECISION | NO by default; possible YES if formulas are authorized later | NO by default; possible YES if output is authorized later | NO | NO | NO | Deferred | Internal possibility, but still requires audience and analysis-scope decisions and may drift toward portfolio/recommendation work. |
| OPT-D | Full pension portfolio review/projection | HIGH | NEEDS_PRODUCT_DECISION | YES | Possibly YES | Possibly YES | Possibly YES | NO unless explicitly authorized | Rejected | Requires unresolved projection, calculation, source, and output authority. |
| OPT-E | Tax/cashflow/scenario calculation domains | HIGH | EXCLUDED_UNTIL_AUTHORIZED | YES | Possibly YES | Possibly YES | Possibly YES | NO unless explicitly authorized | Rejected | Explicitly high-risk and excluded until legal/tax/formula/source authority exists. |
| OPT-F | Imports/OCR/clearinghouse integration | HIGH | EXCLUDED_UNTIL_AUTHORIZED | NO by default; possible YES later | Possibly YES | YES | Possibly YES | NO | Rejected | Requires external integration, source trust, privacy, and side-effect decisions. |
| OPT-G | Reports/PDF/161D/client-facing output | HIGH | EXCLUDED_UNTIL_AUTHORIZED | Possibly YES | YES | NO unless document-dependent | YES | Possibly YES only if authorized | Rejected | Requires unresolved output, legal/form, rendering, and client-facing authority. |
| OPT-H | LLM/tool/recommendation workflow | HIGH | EXCLUDED_UNTIL_AUTHORIZED | Possibly YES | Possibly YES | Possibly YES | Possibly YES | YES | Rejected | Requires unresolved LLM/tool, recommendation, safety, audit, and output authority. |
| OPT-I | Administration/settings evidence investigation | LOW for evidence investigation; HIGH for implementation | UNKNOWN_NEEDS_EVIDENCE | Possibly YES if settings affect calculations, but not authorized here | NO | NO | NO | NO | Selected | Lowest-risk option when limited to evidence investigation and contract definition only; can improve planning structure without code, tests, calculations, client output, imports, reports, LLM, or remapping. |

## Selected Outcome

SELECTED_OPTION: OPT-I

## Selected Milestone

Milestone name:

V2 Administration and Settings Evidence Investigation

Selected option:

OPT-I Administration/settings evidence investigation

Audience:

Internal product/governance reviewers and future implementation planners.

Purpose:

Determine whether V2 needs an administration/settings capability area, what exact evidence is missing, and what contract boundaries would be required before any future implementation can be considered.

This milestone is evidence and contract preparation only. It does not authorize implementation.

## Scope

### Explicitly In Scope

- Define the evidence contract for investigating administration/settings capability.
- Identify the specific evidence sources that may be read in a later evidence package.
- Define how to classify findings as:
  - not applicable;
  - evidence absent;
  - evidence present but not authorized;
  - requires future Product Decision;
  - excluded from current V2 scope.
- Define reproducibility, audit, and permission questions that must be answered if mutable settings are ever considered.
- Preserve the distinction between evidence investigation and implementation.

### Explicitly Out Of Scope

- Source code changes.
- Test changes.
- Backend changes.
- Frontend changes.
- Migrations.
- Models.
- Schemas.
- Services.
- UI.
- Package files.
- Dependencies.
- Runtime behavior.
- Admin UI.
- Settings persistence.
- Mutable calculation tables.
- Permission implementation.
- V1/V2 remapping.
- New discovery options.
- Calculation implementation.
- Tax, cashflow, scenario, projection, OCR, import, clearinghouse integration, report/PDF/161D, LLM, recommendation, or client-facing output.

## Explicit Authorization Answers

| Question | Decision |
|---|---|
| Calculations authorized | NO |
| Imports/OCR/clearinghouse authorized | NO |
| Reports/PDF/161D/client-facing output authorized | NO |
| LLM/recommendations authorized | NO |
| Code changes authorized | NO |
| Test changes authorized | NO |
| Contract package preparation authorized | YES |
| Implementation authorized directly by 02H | NO |

## First Contract Package

First contract package name:

`V2-IAP-02I_CONTRACT_PACKAGE_FOR_SELECTED_MILESTONE`

First contract package allowed file:

`specs/runtime/V2_CONTRACT_ADMIN_SETTINGS_EVIDENCE_INVESTIGATION.md`

Allowed areas for the contract package:

- The single allowed contract file only.
- Governance/planning language needed to define the evidence investigation contract.
- No reads or writes outside the contract package's explicitly listed sources and output file.

Forbidden areas for the contract package:

- Any implementation.
- Any code.
- Any tests.
- Backend.
- Frontend.
- Migrations.
- Models.
- Schemas.
- Services.
- UI.
- Package files.
- Dependencies.
- Product Discovery rewrite.
- V1/V2 remapping.
- Changes to existing planning files.
- Runtime behavior.
- Admin/settings implementation.
- Calculation behavior.
- Client-facing output.

## Required Acceptance Evidence For Contract Package

The contract package must provide:

1. HEAD reviewed.
2. Files read.
3. The single contract file created.
4. Exact evidence questions for an administration/settings investigation package.
5. Exact permitted evidence sources for the later evidence package.
6. Exact forbidden areas.
7. Classification rules for evidence findings.
8. Stop conditions.
9. Confirmation that no implementation, code, tests, or runtime behavior are authorized.
10. Final git status.

## Contract Package Stop Conditions

The contract package must stop if:

1. It requires source code, tests, backend, frontend, migrations, models, schemas, services, UI, package files, dependencies, or unrelated files.
2. It requires V1/V2 remapping.
3. It attempts to decide that administration/settings implementation is required.
4. It attempts to authorize mutable settings, admin UI, permissions, or calculation table behavior.
5. It cannot define exact evidence sources for the later evidence investigation.
6. It cannot preserve reproducibility and audit questions as unanswered evidence questions.
7. It would need to modify any existing planning document.

## Required Next Step

The next roadmap step is a Contract Package only:

`V2-IAP-02I_CONTRACT_PACKAGE_FOR_SELECTED_MILESTONE`

The 02I package may prepare only:

`specs/runtime/V2_CONTRACT_ADMIN_SETTINGS_EVIDENCE_INVESTIGATION.md`

02I must not implement.

## Anti-loop Controls

1. 02H does not implement.
2. 02H does not create contracts.
3. 02H does not reopen V1/V2 mapping.
4. 02H does not authorize code changes.
5. Because OPT-I is selected, only the next contract package is authorized to be prepared.
6. No implementation may start before the contract package is accepted.
7. No broad remapping cycle is allowed unless a named evidence gap is identified.
8. The selected milestone remains evidence/contract-first and does not determine that administration/settings implementation is needed.
9. A later evidence package may still conclude NO-GO for administration/settings implementation.

## Final Decision

SELECTED_OPTION: OPT-I

Selected milestone:

V2 Administration and Settings Evidence Investigation

Next package:

`V2-IAP-02I_CONTRACT_PACKAGE_FOR_SELECTED_MILESTONE`

Implementation authorized: NO.
