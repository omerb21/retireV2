# PKG-004B2 Acceptance Record

## Package Identity

| Field | Value |
|---|---|
| Package | `PKG-004B2 — M07 Calculation Input Resolution` |
| Status | `ACCEPTED` |
| Accepted classification | `CALCULATION_INPUT_RESOLVER_FRAMEWORK` |
| Base | `2bbd4e42025ffbfae76cb131893e5f355d2dd127` |
| Accepted implementation HEAD | `f384ecbc72e649d3b6512127740cdfcf35417627` |
| Alembic head | `a9c4e7f2b615` |
| Definition | `specs/runtime/PKG_004B2_FINAL_PACKAGE_DEFINITION.md` |

## Accepted Technical Scope

PKG-004B2 provides:

- a server-owned manifest-registry boundary;
- fail-closed handling of an unknown calculation scope or manifest version;
- strict resolver input schemas;
- `resolve_calculation_inputs(...)`;
- client-scoped loading of one finalized PKG-004B1 evidence revision;
- deterministic candidate normalization;
- coalescing of identical normalized values with all traceability references;
- detection of conflicting normalized values;
- narrow explicit user selections between available candidates;
- rejection or invalidation of stale selections;
- exactly three resolution outcomes:
  - `resolved`;
  - `missing_inputs`;
  - `ambiguous_inputs`;
- a deterministic canonical result and SHA-256 fingerprint;
- a calculation-ready payload only for `resolved`;
- indistinguishable safe behavior for missing and foreign B1 references;
- no mutation of PKG-004B1 evidence.

## Accepted Framework Boundary

`FRAMEWORK_ACCEPTED_WITHOUT_PRODUCTION_CALCULATION_MANIFEST`

No concrete production calculation scope or manifest is registered. This is
an accepted PKG-004B2 framework boundary, not a defect in the package.
Unknown production scope or manifest version fails closed and emits no
calculation-ready payload.

Future calculation-consuming packages may register manifests only after their
scope, fields, technical types, normalization rules, derivations, and
conditional requirements are authorized. The resolver must not invent any
business field, normalization rule, derivation, or conditional rule.

## Explicitly Absent

PKG-004B2 does not introduce:

- qualification;
- warning review;
- `accepted_for_use`;
- professional approval or authority;
- source ranking;
- latest-wins conflict selection;
- a direct PKG-004B2 manual-entry channel;
- resolution persistence or resolution history;
- a current-record selector;
- successor or supersession lifecycle;
- database models or migrations;
- an HTTP API;
- UI;
- fixation integration.

## Acceptance Evidence

Focused audit result:

`FOCUSED_AUDIT_PASSED_ACCEPT_PKG_004B2_FRAMEWORK`

| Audit area | Result |
|---|---|
| Repository safety | `PASS` |
| Expected four changed files only | `PASS` |
| Manifest registry | `PASS` |
| Input boundary | `PASS` |
| B1 and client isolation | `PASS` |
| Resolution rules | `PASS` |
| Normalization and fingerprint | `PASS` |
| Calculation-payload boundary | `PASS` |
| Forbidden architecture | `PASS` |
| Defects | `none` |

Test and verification evidence:

| Verification | Result |
|---|---|
| Focused PKG-004B2 | `24 passed` |
| PKG-004B1 + PKG-004B2 | `71 passed` |
| API/client-isolation baseline | `70 passed` |
| Python compile | `PASS` |
| Alembic | single head `PASS` |
| Git diff check | `PASS` |
| Prior full backend implementation evidence | `501 passed` |

Frontend tests and production build were not rerun because PKG-004B2 changed
no frontend files.

## Accepted Package Limitations

The following are accepted package boundaries:

- no production calculation manifest;
- no direct calculation-engine integration;
- no persistent selections unless a later authorized package introduces them;
- no HTTP or API exposure;
- no UI;
- no historical backfill;
- no production-readiness claim;
- no V1/V2 parity claim;
- no full M07-completion claim.

## Relationship to PKG-004B1

- PKG-004B1 remains accepted and unchanged.
- PKG-004B2 reads finalized B1 evidence only.
- PKG-004B2 does not alter B1 evidence.
- A manually entered value must first be represented in B1 as evidence or a
  planner assertion.
- PKG-004B2 remains a calculation-input resolver, not an authority layer.

## Follow-up Boundary

- Future calculation-consuming packages must define their own authorized
  manifest scope and field rules.
- PKG-004B2 acceptance does not automatically authorize a production
  calculation manifest.
- No next package is authorized by this acceptance record.
