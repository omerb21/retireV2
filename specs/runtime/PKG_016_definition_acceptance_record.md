# PKG-016 Definition Acceptance Record

## 1. Record Identity

| Field | Value |
|---|---|
| Package | `PKG-016` |
| Title | `M10 Stateless Comparator Frontend Presentation and Invocation Foundation` |
| Acceptance type | `Definition Acceptance` |
| Final decision | `ACCEPT_PKG_016_DEFINITION` |
| Professional decision | `NO_OMER_PROFESSIONAL_DECISION_REQUIRED` |
| Findings | `NO_FINDING` |
| Definition status | `ACCEPTED` |
| Implementation | `NOT_AUTHORIZED` |
| Classification | `FRONTEND_PRESENTATION_AND_INVOCATION_ONLY` |
| Business authority | `NO_NEW_M10_BUSINESS_AUTHORITY` |
| Definition base | `91e0d3f01c4c01c1e5d81f06bc678dfa9f79635d` |
| Accepted definition HEAD | `717a0e56d70cfb93b3d99492cdb0d30512513676` |
| Current Alembic head | `e6b4c8d2f507` |

## 2. Immutable Accepted Definition Boundary

The immutable accepted PKG-016 definition HEAD is exactly:

`717a0e56d70cfb93b3d99492cdb0d30512513676`

Its exact parent is
`91e0d3f01c4c01c1e5d81f06bc678dfa9f79635d`, and it is exactly one commit
above that base.

The commit containing this acceptance record is the **definition
acceptance-record evidence HEAD only**. It is not the accepted definition HEAD,
does not replace or extend that immutable boundary, and must never be described
as the accepted definition HEAD. This record neither edits nor recreates the
accepted definition.

## 3. Accepted Audit Decision

Independent WORK audit recorded:

- Decision: `ACCEPT_PKG_016_DEFINITION`.
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`.
- Findings: `NO_FINDING`.

The definition is accepted. Implementation remains `NOT_AUTHORIZED`.

## 4. Accepted Definition Integrity Anchors

The following Git blobs are immutable integrity anchors at accepted definition
HEAD `717a0e56d70cfb93b3d99492cdb0d30512513676`:

| Artifact | Blob SHA |
|---|---|
| `specs/runtime/PKG_016_FINAL_PACKAGE_DEFINITION.md` | `567976e3093ccacb55e277acb78fe8fe4a2d705d` |
| `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md` | `e9c2bdd74cf80b28d62dcf1e8b2b1276dd1103b8` |

Future integrity checks must resolve these paths at the accepted definition
HEAD, not at the acceptance-record evidence HEAD.

## 5. Accepted Scope

The accepted definition establishes definition-level scope only for a bounded,
client-scoped frontend presentation and invocation slice over accepted PKG-015
authority. It defines future behavior for:

- server-evidenced M09 subject and run discovery;
- exactly one transient baseline-reference/adjusted-compared pair;
- exact invocation of
  `POST /api/clients/{client_id}/m10/compare`;
- exact presentation of accepted comparator success evidence;
- exact one-to-one presentation of accepted structured blocker evidence;
- client-bound asynchronous generation and request ownership; and
- deterministic rejection of stale discovery and comparison completions.

This accepted scope is a definition boundary only. It creates no implementation
authority.

## 6. Consumed Accepted Contracts

PKG-016 consumes exactly:

1. `declared_retirement_cashflow_adjustments/v1`
2. `m09-subject-currentness-v1`
3. `m09-to-m10-eligibility-v2`
4. `m10-scenario-comparison-v2`
5. `m10-pair-admission-v2`
6. `m10-comparison-result-v2`
7. `m10-comparison-fingerprint-v2`

No successor contract, compatibility alias, or v3 authority is created.

## 7. No-New-Authority Boundary

PKG-016 does not add:

- M10 business calculations;
- metrics, percentages, percentage changes, materiality, or significance;
- assumption-delta semantics;
- multi-scenario or adjusted-versus-adjusted comparison;
- comparison persistence, history, or saved comparison;
- planner review, approval, preferred-selection, or other professional-selection
  authority;
- recommendation, ranking, optimization, or suitability; or
- M11 or M12 eligibility or authority.

PKG-015 remains the sole comparator arithmetic and pair-admission owner. Broad
M10 remains unresolved and blocked outside the accepted bounded subset.

## 8. Browser and Server Authority Boundary

The browser owns presentation and invocation only.

Server authority remains sole and unchanged for:

- M09 currentness evidence;
- M10 eligibility evidence;
- pair admission;
- comparison arithmetic and deltas;
- numeric relations;
- blocker selection and precedence; and
- comparison fingerprinting.

No browser-side monetary arithmetic, authority reconstruction, or semantic
reinterpretation is accepted or authorized.

## 9. Discovery Authority

The accepted admissible discovery evidence is existing server-provided:

- `subject_type`;
- `is_current`; and
- `eligible_for_m10`.

The frontend may filter and render using those exact server facts. It may not
reconstruct currentness, eligibility, semantic identity, factual-baseline
compatibility, horizon compatibility, family/version compatibility, or pair
admission from other metadata or raw business facts. The atomic comparator POST
remains the final pair-admission authority.

## 10. Baseline and Adjusted Semantics

The baseline is server-owned. Exactly one eligible/current baseline is required.
Zero or multiple apparent baseline candidates fail closed, without a browser
tie-break or browser-created baseline.

Selectable adjusted candidates are limited to server-evidenced adjusted
subjects with exactly one eligible/current run per subject. Their ordering is
neutral and deterministic, based only on accepted non-business metadata, and
conveys no preference, quality, ranking, or recommendation.

Choosing one baseline reference and one adjusted compared run constructs one
transient request only. It creates no preferred, approved, recommended,
reviewed, persisted, M11-eligible, or M12-eligible selection.

## 11. Decimal and Display Boundary

Authoritative monetary representation remains server evidence. The accepted
definition prohibits:

- `Number` coercion;
- `parseFloat`;
- floating-point arithmetic;
- browser delta calculation;
- browser relation calculation;
- authoritative browser rounding; and
- missing-value synthesis, zero-fill, fallback, or default values.

The exact server monetary string remains semantically recoverable and
unchanged. Relation presentation comes only from the server-returned relation
enum.

## 12. Accepted Blocker Contract

The definition accepts one-to-one browser presentation of the exact closed
PKG-015 blocker set:

1. `comparison_run_unavailable`
2. `comparison_same_subject`
3. `comparison_pair_role_invalid`
4. `comparison_scenario_contract_mismatch`
5. `comparison_horizon_mismatch`
6. `comparison_factual_baseline_material_mismatch`
7. `comparison_component_domain_contract_mismatch`
8. `comparison_engine_version_mismatch`
9. `comparison_result_schema_version_mismatch`
10. `comparison_factual_upstream_version_mismatch`
11. `comparison_run_not_current`
12. `comparison_run_not_eligible`
13. `comparison_fingerprint_invalid`
14. `comparison_semantically_identical_manifest`
15. `comparison_month_alignment_mismatch`
16. `comparison_numeric_domain_invalid`

No suppression, combination, severity invention, warning invention, or
precedence change is accepted. The browser renders the one server-selected
code. Transport, generic server, schema, and malformed-error failures remain
distinct from accepted business blockers.

## 13. Async and Client-Generation Boundary

Every discovery and comparison request must capture:

- `clientId`;
- a monotonic client-context generation; and
- request/channel ownership.

Every state mutation from success, error, and `finally` requires matching
client generation and request ownership. A route/client generation change
immediately clears prior candidates, selection, actionable run IDs, result,
blocker, error, and loading ownership.

Accepted future implementation evidence must deterministically cover A -> B and
A -> B -> A, stale success, stale rejection, and stale `finally` for both
discovery and comparison. An A-old completion cannot mutate a later A-new visit.

## 14. Q-019 Preservation

The following unresolved Q-019 branches remain excluded for broader M10:

- additional metrics and percentages;
- materiality or significance;
- assumption-delta semantics;
- missing or partial presentation; and
- broader compatibility.

PKG-016 definition acceptance does not resolve or authorize any of them.

## 15. Q-020 Preservation

The following unresolved Q-020 branches remain excluded:

- multi-scenario and adjusted-versus-adjusted comparison;
- review;
- persisted or preferred selection;
- supersession and archive; and
- M11 or M12 handoff/eligibility.

PKG-016 definition acceptance does not resolve or authorize any of them.

## 16. Acceptance-Criteria Evidence

- Count: `45`.
- Exact range: `AC-016-001` through `AC-016-045`.
- Result: `45 PASS / 0 FAIL / 0 AMBIGUOUS`.
- Missing criteria: `NONE`.
- Duplicate criteria: `NONE`.
- Contradictions: `NONE`.

## 17. Non-Acceptance-Criteria Evidence

- Count: `32`.
- Exact range: `NAC-016-001` through `NAC-016-032`.
- Result: `32 PASS / 0 FAIL / 0 AMBIGUOUS`.
- Missing criteria: `NONE`.
- Duplicate criteria: `NONE`.

## 18. Accepted Stop Conditions

The accepted 20 stop conditions are exactly:

1. `PKG_016_BACKEND_SEMANTIC_EXPANSION_REQUIRED`
2. `PKG_016_NEW_METRIC_REQUIRED`
3. `PKG_016_MATERIALITY_OR_SIGNIFICANCE_REQUIRED`
4. `PKG_016_ASSUMPTION_DELTA_SEMANTICS_REQUIRED`
5. `PKG_016_MULTI_SCENARIO_REQUIRED`
6. `PKG_016_ADJUSTED_VS_ADJUSTED_REQUIRED`
7. `PKG_016_COMPARISON_PERSISTENCE_REQUIRED`
8. `PKG_016_REVIEW_OR_SELECTION_AUTHORITY_REQUIRED`
9. `PKG_016_M11_OR_M12_AUTHORITY_REQUIRED`
10. `PKG_016_BROWSER_CALCULATION_REQUIRED`
11. `PKG_016_MISSING_VALUE_SYNTHESIS_REQUIRED`
12. `PKG_016_UPSTREAM_ELIGIBILITY_RECONSTRUCTION_REQUIRED`
13. `PKG_016_NEW_PROFESSIONAL_DECISION_REQUIRED`
14. `PKG_016_SCOPE_EXPANSION_REQUIRED`
15. `PKG_016_DISCOVERY_AUTHORITY_INSUFFICIENT`
16. `PKG_016_BASELINE_AUTHORITY_AMBIGUOUS`
17. `PKG_016_PAIR_PREADMISSION_ROUTE_REQUIRED`
18. `PKG_016_BLOCKER_CONTRACT_DIVERGENCE_REQUIRED`
19. `PKG_016_CLIENT_GENERATION_ISOLATION_UNAVAILABLE`
20. `PKG_016_NONDETERMINISTIC_DISCOVERY_REQUIRED`

None fired during definition acceptance. Each remains a fail-closed future
implementation boundary and grants no authority to perform the named expansion.

## 19. Independently Verified Repository and API Evidence

WORK independently verified existing repository support for:

- `AppRoutes.tsx` and client-scoped navigation architecture;
- `useClientContextGeneration`;
- `listM09Subjects`;
- `listM09SubjectRuns`;
- server-returned currentness and M10 eligibility evidence;
- subject and run summary identity/display metadata;
- `POST /api/clients/{client_id}/m10/compare`;
- its exact two-field `reference_run_id` / `compared_run_id` request;
- its closed success-response schema; and
- `ApiTransportError`-based transport/error distinction.

Therefore `NO_BACKEND_BUSINESS_CHANGE` remains a viable future implementation
expectation. This finding does not authorize that implementation.

## 20. Accepted Definition File and Scope Preservation

This acceptance-record evidence commit changes only:

`specs/runtime/PKG_016_definition_acceptance_record.md`

It does not change the accepted PKG-016 definition, Build Plan, any accepted
PKG-015 artifact, frontend, backend, tests, migrations, or persistence. Alembic
remains exactly one head at `e6b4c8d2f507`.

## 21. Governance State After Record Creation

- PKG-016 definition: `ACCEPTED_PENDING_RECORD_AUDIT`.
- Accepted definition HEAD:
  `717a0e56d70cfb93b3d99492cdb0d30512513676`.
- Definition acceptance-record evidence HEAD: the commit containing this record;
  evidence only, not the accepted definition HEAD.
- PKG-016 implementation: `NOT_AUTHORIZED`.
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`.
- M11-M14: `NOT_AUTHORIZED`.
- M08E: `EXCLUDED`.
- `02M`: `FROZEN`.
- Next package: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

This record creates no implementation, frontend, backend, test, migration,
persistence, API-semantic, broad-M10, downstream, production, or next-package
authorization.

PKG_016_DEFINITION_ACCEPTED
