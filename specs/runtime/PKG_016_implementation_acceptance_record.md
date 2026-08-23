# PKG-016 Implementation Acceptance Record

## Record Identity

- Package: `PKG-016`
- Title: `M10 Stateless Comparator Frontend Presentation and Invocation Foundation`
- Acceptance type: `Implementation Acceptance`
- Audit decision: `ACCEPT_PKG_016_IMPLEMENTATION`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`
- Classification: `FRONTEND_PRESENTATION_AND_INVOCATION_ONLY`
- Business authority: `NO_NEW_M10_BUSINESS_AUTHORITY`
- Definition status: `CLOSED_ON_MASTER`
- Implementation status: `ACCEPTED`
- Implementation base / current master: `d82c17e5fff5a111a43b0cd0cd0b4e27124af4a3`
- Accepted definition HEAD: `717a0e56d70cfb93b3d99492cdb0d30512513676`
- Definition acceptance-record evidence: `d82c17e5fff5a111a43b0cd0cd0b4e27124af4a3`
- Accepted implementation HEAD: `cc8fe1c169747e7da96e4f05ed78b996865018a1`
- Previous rejected implementation candidate: `aa54978f1a0f3ec578fbbc5791d60158d124b052`
- Implementation acceptance-record evidence HEAD: the documentation-only commit containing this record
- Alembic head: `e6b4c8d2f507`

The immutable accepted implementation boundary is exactly
`cc8fe1c169747e7da96e4f05ed78b996865018a1`. The previous candidate
`aa54978f1a0f3ec578fbbc5791d60158d124b052` is historical only and is not the
accepted boundary. The documentation-only commit containing this record is
evidence only; its exact commit hash is reported with delivery. It does not
replace, extend, or redefine the accepted implementation HEAD.

## Audit Decision and Findings

- Decision: `ACCEPT_PKG_016_IMPLEMENTATION`
- Professional decision: `NO_OMER_PROFESSIONAL_DECISION_REQUIRED`
- `D-016-I001`: `CLOSED`
- `D-016-I002`: `CLOSED`
- Findings: `NO_NEW_FINDING`

## Exact Accepted Implementation History

The accepted implementation consists of exactly these six linear commits above
master `d82c17e5fff5a111a43b0cd0cd0b4e27124af4a3`, in order:

1. `2ede1b9e2042879a16a35cad55e76d340a46c4c6` — `feat: add PKG-016 comparator frontend`
2. `80c01033072e764a99963a8f64826c1e31f216e3` — `test: prove PKG-016 comparator frontend boundaries`
3. `aa54978f1a0f3ec578fbbc5791d60158d124b052` — `test: verify PKG-016 application route`
4. `379ba7fd72e23ccc8a079be9e97cf159289bb9bb` — `fix: validate PKG-016 comparator responses fail closed`
5. `c6fa043090cec7deb4a5b503f18758eb10495f21` — `test: prove PKG-016 A-B-A stale-success isolation`
6. `cc8fe1c169747e7da96e4f05ed78b996865018a1` — `test: distinguish stale comparator monetary evidence`

The history contains no merge commit and no rewrite. The acceptance-record
commit is not an implementation commit.

## Accepted Implementation Scope

The accepted implementation candidate changed exactly these seven production
and test paths:

- `frontend/src/api/m10ComparisonApi.ts`
- `frontend/src/api/m10ComparisonApi.test.ts`
- `frontend/src/pages/M10ComparisonScreen.tsx`
- `frontend/src/pages/M10ComparisonScreen.test.tsx`
- `frontend/src/routes/AppRoutes.tsx`
- `frontend/src/pages/ClientDetailScreen.tsx`
- `frontend/src/pages/ClientDetailScreen.test.tsx`

No documentation, model, migration, persistence, backend, or unrelated path was
part of the accepted implementation candidate. This acceptance record is a
later documentation-evidence commit outside the accepted implementation
boundary.

## Accepted File Integrity Anchors

The blobs at accepted implementation HEAD
`cc8fe1c169747e7da96e4f05ed78b996865018a1` are:

| Accepted path | Blob SHA |
|---|---|
| `frontend/src/api/m10ComparisonApi.ts` | `75ad2550f48c1e2a5580487ea9368f56b5e10615` |
| `frontend/src/api/m10ComparisonApi.test.ts` | `b8be398766fb9fa8e12fb36aed61f247e4b6bc06` |
| `frontend/src/pages/M10ComparisonScreen.tsx` | `f287f820cfa0896de6c0cb80a5b62a9d51b92236` |
| `frontend/src/pages/M10ComparisonScreen.test.tsx` | `bb2aeee012ada972322cc2ae994be591d6296dc6` |
| `frontend/src/routes/AppRoutes.tsx` | `a3025c190e1a85fb2cb7e8ea14140ab092096214` |
| `frontend/src/pages/ClientDetailScreen.tsx` | `f903dad0cd0acc597cc5ddd041c26b5da6768bbd` |
| `frontend/src/pages/ClientDetailScreen.test.tsx` | `74b9a3ff6b9732923065be0fe6ba2ebf686e299c` |

These blobs are the future accepted implementation integrity anchors.

## Accepted Product Behavior

The accepted implementation provides:

- one client-scoped M10 comparator screen;
- server-evidenced M09 discovery;
- exactly one eligible and current baseline reference;
- server-evidenced eligible adjusted candidates;
- transient pair selection only;
- invocation of the exact existing comparator POST;
- exact server-response presentation;
- exact structured blocker presentation;
- strict runtime success-response validation;
- strict client-generation and request-owner isolation;
- no browser monetary calculation; and
- no backend semantic expansion.

It creates no rank, preference, recommendation, persistence, review, approval,
or downstream eligibility meaning.

## Existing API and Infrastructure Reuse

The accepted implementation reuses exactly the relevant existing authorities
and utilities:

- `listM09Subjects`
- `listM09SubjectRuns`
- server-owned `subject_type`
- server-owned `is_current`
- server-owned `eligible_for_m10`
- `useClientContextGeneration`
- `buildApiUrl`
- `ApiTransportError`
- `POST /api/clients/{client_id}/m10/compare`

No new backend route was introduced.

## Route and Navigation

- Accepted route: `/clients/:clientId/scenario-comparison`
- Accepted navigation label: `M10 Scenario Comparison`

This is neutral client-scoped navigation. It conveys no ranking, preference,
selection, recommendation, suitability, or professional conclusion.

## Server and Browser Authority Boundary

The browser owns presentation and invocation only. The server retains sole
authority for:

- currentness;
- M10 eligibility;
- pair admission;
- comparator arithmetic;
- deltas;
- numeric relations;
- blocker precedence; and
- fingerprinting.

There is no second calculation owner in the browser.

## D-016-I001 — Runtime Success-Response Validation

`D-016-I001` is `CLOSED`. An HTTP 200 response becomes M10 business evidence
only after strict runtime validation of the complete closed response contract.
A malformed successful response becomes `ApiTransportError` with API/schema
failure semantics. It does not become comparator success, partial success, or a
business blocker, and no missing evidence is defaulted or synthesized.

### Contract and Version Validation

The validator requires the exact accepted identities:

- `m10-scenario-comparison-v2`
- `m10-pair-admission-v2`
- `m10-comparison-result-v2`
- `m10-comparison-fingerprint-v2`

It also validates the exact M09, component-domain, upstream-domain, and M06
handoff evidence identities required by the accepted backend contract. There is
no alias, fallback, compatibility reinterpretation, or version negotiation.

### Monetary Validation

Authoritative money remains string-only evidence. The canonical accepted
backend Decimal representation and closed source/delta domains are validated as
strings. Validation uses no `Number`, `parseFloat`, `parseInt`, `Math` monetary
computation, rounding, normalization that changes authority, or frontend delta
arithmetic. The original accepted monetary strings remain the semantic values.

### Relation Validation

The accepted relation set is exactly:

- `equal`
- `compared_greater_than_reference`
- `compared_lower_than_reference`

No relation is derived from a monetary value or delta.

### Monthly and Range Validation

Complete runtime validation applies to monthly rows and range totals for:

- `gross_inflow_total`
- `gross_outflow_total`
- `period_net`

Every metric requires exactly `reference_value`, `compared_value`, `delta`, and
`relation`. Monthly rows also require their accepted month identity. Partial,
extra, null, malformed, zero-filled, or synthesized output is rejected.

### Run, Evidence, and Fingerprint Validation

- the reference role must be `baseline`;
- the compared role must be `adjusted`;
- required run and subject evidence is validated;
- required nested version and upstream evidence is validated;
- fingerprints are validated according to the accepted backend contract; and
- the browser neither synthesizes nor recalculates a fingerprint.

## Blocker Contract

The exact closed PKG-015 blocker set contains these 16 codes:

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

Each accepted code maps one-to-one without suppression, combination, invented
severity, or frontend precedence. Malformed blocker detail and an accepted code
on the wrong HTTP status remain API/transport failures rather than business
blockers.

## Client-Generation and Request-Owner Isolation

Every discovery and compare request captures the current `clientId`, monotonic
generation, and channel/request owner. Mutation from success, error, and
`finally` is permitted only when all captured ownership evidence still matches.
Abort is not the sole correctness mechanism.

## D-016-I002 — Deterministic Race Closure

`D-016-I002` is `CLOSED`. Controlled-promise tests prove both discovery and
compare A→B→A stale-success isolation. Successful A-old completion has zero
effect after returning to client A under a new generation. Only A-new evidence
can become visible or actionable.

The compare proof uses distinguishable monetary values, fingerprints, baseline
run IDs, and adjusted run IDs. It proves that stale success cannot replace
selection, result, blocker, error, loading ownership, or control state.

The accepted suite also preserves evidence for:

- A→B stale success;
- A→B→A stale rejection;
- stale `finally`;
- same-client R1→R2 request ownership; and
- immediate suppression of prior-client state.

## Acceptance-Criteria Evidence

- Criteria: `AC-016-001` through `AC-016-045`
- Result: `45 PASS / 0 FAIL / 0 AMBIGUOUS`

## Negative-Acceptance-Criteria Evidence

- Criteria: `NAC-016-001` through `NAC-016-032`
- Result: `32 PASS / 0 FAIL / 0 AMBIGUOUS`

## Stop-Condition Evidence

All 20 accepted stop conditions are `NOT_FIRED`:

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

No stop condition fired during the accepted implementation.

## Test and Build Evidence

| Evidence set | Accepted result |
|---|---:|
| Focused corrected tests | `2 files passed / 68 tests passed` |
| Full PKG-016 focused tests | `3 files passed / 74 tests passed` |
| Related regressions | `4 files passed / 66 tests passed` |
| Full frontend suite | `29 files passed / 956 tests passed` |
| Frontend production build and type-check | `PASS` |
| PKG-015 regression | `69 passed / 2 existing FastAPI deprecation warnings` |

## Backend, Migration, Persistence, and Documentation Proof

For the immutable accepted implementation candidate:

- `BACKEND_DIFF = NONE`
- `MIGRATION_DIFF = NONE`
- `PERSISTENCE_DIFF = NONE`
- `DOCS_DIFF = NONE`

The documentation diff created by this record is later evidence and is outside
the accepted implementation candidate.

## Definition and Artifact Integrity

- PKG-016 definition blob: `567976e3093ccacb55e277acb78fe8fe4a2d705d`
- Definition acceptance-record blob: `d8a6ec22caf2f7ad199c47a805a44049056a15b1`
- Business Build Plan blob: `e9c2bdd74cf80b28d62dcf1e8b2b1276dd1103b8`
- Alembic head: `e6b4c8d2f507`
- PKG-015 accepted artifacts: unchanged

The PKG-016 definition, definition acceptance record, Build Plan, PKG-015
artifacts, backend, models, migrations, and persistence were not modified by
this acceptance-record task.

## Immutable Boundary Distinction

- Accepted implementation HEAD: `cc8fe1c169747e7da96e4f05ed78b996865018a1`
- Implementation acceptance-record evidence HEAD: the documentation-only commit containing this record

The exact evidence-commit hash is intentionally reported after commit creation;
a commit cannot contain its own hash as content without changing that hash. The
evidence commit is not part of the accepted implementation candidate and does
not move the immutable implementation boundary.

## Governance State After Record Creation

- PKG-016 definition: `CLOSED_ON_MASTER`
- PKG-016 implementation: `ACCEPTED_PENDING_IMPLEMENTATION_RECORD_AUDIT`
- Accepted implementation HEAD: `cc8fe1c169747e7da96e4f05ed78b996865018a1`
- Implementation acceptance-record evidence: the commit containing this record
- Master merge: `NOT_AUTHORIZED`
- Broad M10: `BLOCKED_FOR_LOGIC_DETAIL`
- M11–M14: `NOT_AUTHORIZED`
- M08E: `EXCLUDED`
- 02M: `FROZEN`
- Next package: `NOT_AUTHORIZED`
- Production readiness: `NOT_CLAIMED`

This record accepts only the bounded PKG-016 implementation. It authorizes no
master merge, broad M10 work, next package, production-readiness claim, M11–M14
work, persistence, or backend expansion.

PKG_016_IMPLEMENTATION_ACCEPTED
