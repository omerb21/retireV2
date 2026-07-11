# V2 Contract: Admin Settings Evidence Investigation

Package: V2-IAP-02I_CONTRACT_PACKAGE_FOR_SELECTED_MILESTONE
Status: CONTRACT_GOVERNANCE_ONLY
Repository HEAD reviewed: 5df006e9c2650ed733e27e6a9125eeab128d04bf

## Current State

- HEAD: `5df006e docs: select V2 admin settings evidence milestone`
- 02H selected: `OPT-I Administration/settings evidence investigation`
- Selected milestone: `V2 Administration and Settings Evidence Investigation`
- Implementation authorization: NO
- Contract package preparation authorization: YES

## Contract Purpose

This contract defines the later evidence investigation package for the selected milestone. It does not perform the investigation itself, does not inspect source beyond the listed planning artifacts used by this contract package, and does not authorize implementation.

The later evidence package may perform read-only evidence investigation only within the sources and boundaries defined here.

## Selected Scope

### In Scope

- Define evidence questions for admin/settings investigation.
- Define permitted evidence sources for the later evidence package.
- Define classification rules for findings.
- Define reproducibility, audit, and permission questions.
- Define stop conditions.
- Define the required result artifact for the later evidence package.

### Out Of Scope

- Code.
- Tests.
- Backend.
- Frontend.
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
- Calculation behavior.
- V1/V2 remapping.
- Product Decision changes.
- Implementation authorization.

## Evidence Questions For 02J

The later evidence package must answer these exact questions:

| ID | Evidence question |
|---|---|
| Q-A | Does V1 evidence show a real admin/settings/table-editing capability, or only configurable constants/data files? |
| Q-B | If V1 evidence exists, what exact files, routes, UI, or tests prove it? |
| Q-C | Does V2 already contain any admin/settings capability evidence? |
| Q-D | Does V2 contain configurable constants, caps, year data, or settings-like structures? |
| Q-E | Are any such structures mutable at runtime, static code constants, database records, seed data, or external-source values? |
| Q-F | Would changing such settings affect calculation reproducibility? |
| Q-G | Is there evidence of permissions, audit trail, or role-based access for settings/admin behavior? |
| Q-H | Is admin/settings needed for current accepted V2 scope, or only for excluded future calculation domains? |
| Q-I | Should the result be `NOT_APPLICABLE`, `EVIDENCE_ABSENT`, `EVIDENCE_PRESENT_NOT_AUTHORIZED`, `REQUIRES_FUTURE_PRODUCT_DECISION`, `EXCLUDED_FROM_CURRENT_SCOPE`, or `UNKNOWN_NEEDS_MORE_EVIDENCE`? |

## Permitted Evidence Sources For 02J

02J may use only read-only inspection. It must not modify any file.

### Required Planning Sources

02J may read:

- `specs/reference/v1_discovery_full.md`
- `specs/reference/v1_usage_rules.md`
- `specs/runtime/V1_TO_V2_FULL_CAPABILITY_COVERAGE_MATRIX.md`
- `specs/runtime/V2_FULL_DEVELOPMENT_PLAN_FROM_V1_GAPS.md`
- `specs/runtime/V2_PRODUCT_DECISION_FOR_NEXT_MILESTONE.md`
- `CURRENT_PROJECT_STATE.md`

### Permitted Repository Searches

02J may run read-only repository searches for these exact terms:

- `admin`
- `settings`
- `config`
- `configuration`
- `constants`
- `caps`
- `cap`
- `year`
- `table`
- `lookup`
- `index`
- `CPI`
- `CBS`
- `permissions`
- `role`
- `audit`

Search commands must be read-only and must be reported in the 02J result file.

### Matching File Reads

02J may read matching source, test, or spec files only when a permitted search result identifies them as evidence candidates for the named evidence questions.

Permitted matching reads are evidence extraction only. They must not be used to perform broad V1/V2 remapping and must not be used to modify files.

## Forbidden 02J Actions

02J must not:

- Modify files.
- Run tests.
- Implement behavior.
- Change source code.
- Change tests.
- Change backend.
- Change frontend.
- Change migrations.
- Change models.
- Change schemas.
- Change services.
- Change UI.
- Change package files.
- Change dependencies.
- Create or modify admin UI.
- Create or modify settings persistence.
- Create or modify mutable calculation tables.
- Implement permissions.
- Implement audit behavior.
- Authorize implementation.
- Perform broad V1/V2 remapping.
- Change Product Decision artifacts.

## Classification Rules

02J must classify each finding and final result using only these classifications:

| Classification | Rule |
|---|---|
| `NOT_APPLICABLE` | No admin/settings capability is relevant to accepted current V2 scope. |
| `EVIDENCE_ABSENT` | Expected evidence is not found in the permitted sources and searches. |
| `EVIDENCE_PRESENT_NOT_AUTHORIZED` | Evidence exists, but no Product Decision authorizes implementation. |
| `REQUIRES_FUTURE_PRODUCT_DECISION` | Implementation may be relevant, but requires a future product/scope decision before any contract or implementation work. |
| `EXCLUDED_FROM_CURRENT_SCOPE` | Evidence belongs only to excluded tax, cashflow, scenario, output, integration, LLM, recommendation, or other excluded future domains. |
| `UNKNOWN_NEEDS_MORE_EVIDENCE` | Evidence is contradictory, incomplete, outside permitted sources, or cannot be resolved safely. |

## Reproducibility, Audit, And Permission Questions

02J must preserve these as evidence questions, not implementation requirements:

1. Would any admin/settings capability alter calculation inputs, caps, constants, year data, or lookup values?
2. If yes, how would historical calculation reproducibility be preserved?
3. Is there evidence of an audit trail for changes to settings-like values?
4. Is there evidence of role-based or permission-based access to settings/admin behavior?
5. Is any settings-like evidence tied only to excluded future calculation/output/integration domains?
6. If mutable settings are found, is there any accepted V2 authority to use them in current scope?

02J must not answer these questions by implementing behavior.

## Required Output Of 02J

The next evidence package output file is:

`specs/runtime/V2_ADMIN_SETTINGS_EVIDENCE_INVESTIGATION_RESULT.md`

It must include:

- Evidence sources read.
- Search commands used.
- Findings table.
- Classification per finding.
- Final classification.
- Implementation recommendation: `NO` or `FUTURE_DECISION_REQUIRED` only.
- No implementation authorization.
- Final git status.

## Acceptance Gate For 02I

02I is accepted only if:

1. Exactly one file is created.
2. The file defines exact evidence questions.
3. The file defines exact permitted evidence sources.
4. The file defines classification rules.
5. The file defines the next evidence package output.
6. The file defines stop conditions.
7. It does not implement.
8. It does not inspect or modify code beyond allowed planning reads.
9. It does not authorize implementation.

## Stop Conditions For 02J

The next evidence package must stop if:

1. Evidence requires code changes.
2. Evidence requires test changes.
3. Evidence requires runtime behavior changes.
4. Evidence requires broad V1/V2 remapping.
5. Evidence points to excluded tax, cashflow, scenario, output, integration, or LLM domains.
6. Exact evidence cannot be named.
7. Findings imply mutable calculation tables without reproducibility or audit authority.
8. Permission or audit implications are unresolved.
9. Required evidence is outside the permitted evidence sources.
10. The result cannot be classified safely using the permitted classification rules.

## Explicit Next Step

After 02I, the next package is:

`V2-IAP-02J_ADMIN_SETTINGS_EVIDENCE_INVESTIGATION`

Allowed file for 02J:

`specs/runtime/V2_ADMIN_SETTINGS_EVIDENCE_INVESTIGATION_RESULT.md`

02J may perform read-only evidence investigation only.

02J must not implement.

## Anti-loop Controls

1. 02I does not implement.
2. 02I does not investigate evidence itself.
3. 02I only defines the contract for 02J.
4. 02J must not reopen broad V1/V2 mapping.
5. 02J must answer the named evidence questions or return `UNKNOWN_NEEDS_MORE_EVIDENCE`.
6. No implementation may start from 02I or 02J.
7. If admin/settings is not evidenced or not authorized, the path stops or returns to Product Decision with named evidence only.

## Implementation Authorization Status

Implementation authorized by 02I: NO.

Evidence investigation authorized for 02J: YES, read-only and bounded by this contract.

Code changes authorized: NO.

Test changes authorized: NO.

Runtime behavior changes authorized: NO.
