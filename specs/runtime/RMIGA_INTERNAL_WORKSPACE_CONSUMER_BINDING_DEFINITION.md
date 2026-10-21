# RMIGA Internal Workspace Consumer Binding — Definition Candidate

## 1. Identity and lifecycle

- Package: `RMIGA_INTERNAL_WORKSPACE_CONSUMER_BINDING`.
- Classification: `CLASS A / COMPLEX CLASS A`.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Definition base master: `12f0cba011c53f1ca750305f49e87fd922d43909`.
- Definition base TREE: `9288c14b95a2fb5fd801c1e28ad129e66142306c`.
- Accepted RMIGA Definition HEAD: `28082b0e95a95e722a145bbcafdb925807645de1`.
- Accepted RMIGA Definition blob: `519de1be94a1c3108dc71198d5ecbc05972fd4f4`.
- Accepted RMIGA implementation HEAD: `dfdbeb0cb1372676a321e3958b6db8ccf2128614`.
- Accepted RMIGA implementation TREE: `8d503ad0adc447b68e19418089034ca379c311db`.
- Status: `DEFINITION_CANDIDATE_PENDING_INDEPENDENT_ACCEPTANCE`.
- Implementation: `NOT_AUTHORIZED`.
- Downstream: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

This Definition is the proposed sole package-level authority for binding the
accepted RIT, CMIA and RMIGA results into the existing authenticated internal
professional workspace. It creates no calculation authority. The immutable
accepted RMIGA Definition remains the sole owner of gap semantics, schemas,
arithmetic, fingerprints, transaction behavior and professional boundaries.

## 2. Objective and authority boundary

The package exposes one explicit internal action that asks accepted RMIGA for
the arithmetic difference between the persisted confirmed RIT target and the
complete CMIA comparable monthly income. It then presents the exact accepted
RMIGA result to the authenticated professional user.

The package may:

1. bind authenticated transport to the accepted RMIGA request;
2. invoke RMIGA exactly once under RMIGA's own transaction boundary;
3. validate the returned public RMIGA envelope through an RMIGA-owned pure
   validator;
4. return that envelope byte-for-field without calculation or reconstruction;
5. render exact rational text and accepted source evidence in the existing
   internal workspace; and
6. discard stale browser state deterministically.

It may not recalculate RIT, CMIA or RMIGA; infer adequacy; normalize bases;
convert gross/net or nominal/real values; add tax, funding, withdrawal,
recommendation, forecast or scenario behavior; persist a gap; add a client
surface; or change an accepted upstream output or fingerprint.

`SHORTFALL`, `EQUAL` and `SURPLUS` remain arithmetic sign classifications only.

## 3. Inspected executable contracts

The proposal is bound to these base-master facts:

- `retirement_monthly_income_gap_service.assess()` accepts exactly
  `client_id`, `expected_planning_calculation_input_fingerprint` and
  `expected_retirement_target_date`; it owns a fresh read-only transaction and
  produces accepted `COMPLETE` or `BLOCK_NO_GAP` envelopes.
- RMIGA raises the accepted immutable `RMIGAContractError`,
  `RMIGANumericError` and `RMIGAFingerprintError`. Its bounded CMIA dependency
  may raise `CMIAResultValidationError` and accepted upstream/DB exceptions.
- the existing readiness router prefix is
  `/api/clients/{client_id}/retirement-income-readiness` and uses the shared
  `RTDIR_TRANSPORT_ERROR_V1` error envelope.
- production `RTDIRSecurityMiddleware` protects non-public API routes, binds a
  signed session to `request.state.trusted_professional_actor`, validates
  Origin before CSRF on ordinary unsafe routes, and adds no-store headers.
- the existing screen already uses one workspace generation counter and
  `AbortController`, reloads context/target from persisted state and contains
  no browser-persisted professional evidence.

No accepted contract grants the browser authority to supply an actor, target
amount, comparable amount, source list, result fingerprint or arithmetic.

## 4. Backend endpoint

The one endpoint is:

`POST /api/clients/{client_id}/retirement-income-readiness/gap`

It is an authenticated internal API route. It is not public, not idempotently
retried by the route, and not a persistence command.

### 4.1 Path and closed body

`client_id` is the existing FastAPI positive-integer path parameter. The body
has exactly two keys and no aliases:

| Key | Exact contract |
|---|---|
| `expected_planning_calculation_input_fingerprint` | strict string matching lowercase ASCII `[0-9a-f]{64}` |
| `expected_retirement_target_date` | strict canonical real ISO date `YYYY-MM-DD` |

Missing keys, extra keys, coercion, invalid hashes and non-calendar dates are
rejected by the production request-validation boundary. `client_id` is never
accepted in the body. The route constructs exactly:

```json
{
  "client_id": "<positive integer from path>",
  "expected_planning_calculation_input_fingerprint": "<body value>",
  "expected_retirement_target_date": "<body value>"
}
```

The notation above describes the source of the integer; the Python command
contains an integer, not a JSON string. No actor or financial value is added.

### 4.2 Authentication, Origin, CSRF and workspace isolation

In production, the existing middleware contract applies unchanged and in its
existing order:

1. Railway edge tuple validation;
2. signed session validation and trusted professional actor binding;
3. exact allowed Origin validation;
4. exact `X-RTDIR-CSRF` validation for this POST; and
5. route dispatch.

The route does not read an actor from the body, query string or arbitrary
header and does not replace `trusted_professional_actor`. RMIGA requires no
actor argument; authentication gates access but grants no calculation input.

This is a single-professional workspace. There is no per-client professional
ownership partition. Client isolation means instead:

- the positive path ID is the only client ID passed to RMIGA;
- the body cannot override it;
- nonexistent clients preserve the accepted `CLIENT_NOT_FOUND` transport;
- every validated returned result must have the same client ID as the path;
- planning fingerprint and retirement date must equal the exact submitted
  persisted identities; and
- an A/B browser transition cannot publish a response for the other client.

### 4.3 Session and producer invocation

`get_db` supplies one fresh SQLAlchemy Session. The route must not begin a
transaction, call `connection()`, flush, commit, retry, roll back or close the
Session around RMIGA. It invokes `retirement_monthly_income_gap_service.assess`
exactly once with that Session and the constructed command. RMIGA remains the
sole transaction owner and performs the accepted snapshot, rollback,
invalidation and permanent non-reuse behavior.

The route never invokes RIT, CMIA, RTICB or Planning Input separately. It does
not validate by recalculation. A producer exception is mapped once and never
causes another RMIGA call. A rollback-failed/poisoned Session is not touched by
route recovery and is discarded by the dependency lifecycle.

## 5. RMIGA-owned pure public-result validator

A future authorized implementation must add this bounded RMIGA-owned function
to the accepted RMIGA service:

`validate_public_result(result: Mapping[str, Any]) -> ValidatedRMIGAResult`

`ValidatedRMIGAResult` is a private frozen tagged value with exactly:

- `result_state`: `COMPLETE` or `BLOCK_NO_GAP`; and
- `result`: a recursively immutable exact deep copy of the input.

The function is pure: no Session, SQL, producer call, clock, retry, repair,
normalization, sorting, filtering or fingerprint construction for the caller.
The same input returns the same immutable value or raises the same deterministic
`RMIGAResultValidationError(ValueError)` with immutable:

- `stage="result_validation"`;
- `code="RMIGA_PUBLIC_RESULT_INVALID"`; and
- `client_id=<strict positive non-bool input client ID>|None`.

Its message contains no monetary value, unverified hash or upstream payload.

### 5.1 COMPLETE validation

The validator requires exact schema version
`RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_RESULT_V1`, `result_state="COMPLETE"`
and exactly these top-level keys:

`schema_version`, `result_state`, `client_id`,
`planning_calculation_input_fingerprint`, `retirement_target_date`,
`target_result_fingerprint`, `target_semantic_fingerprint`,
`cmia_result_fingerprint`, `target_income_basis`, `target_price_basis`,
`target_price_reference_date`, `target_monthly_amount`,
`comparable_monthly_income`, `monthly_gap`, `gap_state`,
`included_contributions`, `excluded_source_ids`, `source_count`,
`result_fingerprint`.

It proves:

- strict positive client ID, canonical date and lowercase SHA-256 identities;
- accepted income/price/reference-date combinations;
- `target_monthly_amount` and `comparable_monthly_income` are canonical
  nonnegative rationals and `monthly_gap` is a canonical signed rational;
- all rationals have exactly `numerator`, `denominator`, `currency`,
  `frequency`, reduced gcd, positive denominator, `ILS`, `MONTHLY`, canonical
  integer strings and arbitrary precision;
- `gap_state` equals only the exact sign of `monthly_gap.numerator`;
- contribution entries have CMIA's exact accepted closed schema, canonical
  contribution rational and fingerprints, are strictly source-ID sorted and
  unique, and preserve exact source identity;
- excluded source IDs are sorted, unique and disjoint from included IDs;
- `source_count` equals the contribution count; and
- the exact accepted RMIGA complete fingerprint is independently reconstructed
  from UTF-8 canonical JSON under
  `RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_RESULT_JSON_V1`.

The validator does not recompute the gap from upstream producers; RMIGA already
owns that calculation. Structural and fingerprint validity are both required.
A coherently rehashed schema, source, rational, sign or closed-key violation is
rejected.

### 5.2 BLOCK_NO_GAP validation

The validator requires exact schema version
`RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_BLOCK_NO_GAP_V1`,
`result_state="BLOCK_NO_GAP"` and exactly:

`schema_version`, `result_state`, `client_id`,
`supplied_planning_calculation_input_fingerprint`,
`supplied_retirement_target_date`, `observed_cmia_result_fingerprint`,
`observed_cmia_failure_stage`, `observed_cmia_failure_detail_code`,
`observed_cmia_blocked_source_ids`, `failure_stage`,
`failure_detail_code`, `result_fingerprint`.

It requires canonical identity fields; canonical observed CMIA fields; sorted
unique blocked source IDs; `failure_stage="upstream_authority"`;
`failure_detail_code="RMIGA_COMPARABLE_INCOME_BLOCKED"`; absence of every
numeric, contribution and sign field; and independent reconstruction under
`RETIREMENT_MONTHLY_INCOME_GAP_AUTHORITY_BLOCK_JSON_V1`.

### 5.3 Route binding after validation

The route consumes only `ValidatedRMIGAResult.result`. For both tags,
`client_id` must equal the path ID. For `COMPLETE`,
`planning_calculation_input_fingerprint` and `retirement_target_date` must equal
the submitted body fields. For `BLOCK_NO_GAP`, the corresponding
`supplied_planning_calculation_input_fingerprint` and
`supplied_retirement_target_date` must equal them. Any mismatch is a producer
integrity failure. A recomputed result fingerprint never cures request mismatch.

On success, the route returns the original validated dictionary unchanged in a
`JSONResponse` with `Cache-Control: no-store, private` and `Pragma: no-cache`.
It adds no wrapper and removes no key.

## 6. Deterministic transport contract

Every error uses the existing exact envelope:

```json
{
  "schema_version": "RTDIR_TRANSPORT_ERROR_V1",
  "code": "<machine code>",
  "message": "<shared neutral Hebrew message>",
  "field_paths": ["<sorted unique JSON pointers>"],
  "request_id": "<middleware request ID>"
}
```

All endpoint success, block and error responses are no-store. No exception
text, SQL, monetary value, fingerprint payload, cookie, CSRF token, stack trace
or driver detail appears.

| Boundary / actual exception | HTTP | Public code | Exact field paths |
|---|---:|---|---|
| invalid path/body rejected before route | 422 | `REQUEST_SCHEMA_INVALID` | pointers emitted by the accepted global handler, including `/path/client_id` or the exact body field |
| nonexistent addressed client (`PensionProductError` code `CLIENT_NOT_FOUND`) | 404 | `CLIENT_NOT_FOUND` | `/path/client_id` |
| returned validated client differs from path | 500 | `RESPONSE_CLIENT_MISMATCH` | empty |
| `CMIAResultValidationError`, `RMIGAResultValidationError`, or valid outer result with body-identity mismatch | 500 | `PRODUCER_RESPONSE_INVALID` | empty |
| `RMIGAContractError` at `request_validation`, `cmia_authority`, `target_authority`, `cross_authority_identity`, `basis_compatibility` or `amount_authority` | 500 | `PRODUCER_RESPONSE_INVALID` | empty |
| `RMIGAContractError` at `snapshot_admission` | 503 | `RTICB_DATABASE_FAILURE` | empty |
| SQLAlchemy `OperationalError`, `IntegrityError` or `DBAPIError` | 503 | `RTICB_DATABASE_FAILURE` | empty |
| accepted upstream technical exception (`RetirementTargetIncomeSourceAdmissionTechnicalError` or `CRTISBA_UPSTREAM_TECHNICAL_FAILURE`) | 503 | `RTICB_UPSTREAM_TECHNICAL_FAILURE` | empty |
| `RMIGANumericError`, `RMIGAFingerprintError`, CMIA/CRTISBA/RTICB fingerprint construction error, rollback/cleanup error, host-resource error or unknown exception | 500 | `INTERNAL_ERROR` | empty |

No new public error code is introduced. `RTICB_DATABASE_FAILURE` and
`RTICB_UPSTREAM_TECHNICAL_FAILURE` retain their current readiness-router
status, envelope and sanitized meaning. Known `CRTISBAError` values
`PRODUCER_RESPONSE_INVALID` and
`RESPONSE_CLIENT_MISMATCH` retain those exact 500 codes. Other upstream domain
errors use the existing `_transport` mapping only when their actual accepted
code/status pair is already supported; otherwise they fail closed as
`INTERNAL_ERROR`.

Production middleware continues to own, before route execution:

- `400 EDGE_REQUEST_INVALID`;
- `401 SESSION_MISSING`, `SESSION_INVALID` or `SESSION_EXPIRED`;
- `403 ORIGIN_FORBIDDEN`; and
- `403 CSRF_INVALID`.

Origin precedes CSRF for this ordinary unsafe route. None of these failures
opens a Session or calls RMIGA.

## 7. Frontend API contract

`retirementIncomeReadinessApi.ts` adds closed TypeScript shapes mirroring the
two accepted RMIGA envelopes and:

`calculateMonthlyGap(clientId, body, signal?)`.

The path is `/clients/${clientId}/retirement-income-readiness/gap`; method is
POST; body contains only the two fields in Section 4.1. `apiFetch` supplies
same-origin production `/api`, credentials and the existing CSRF header. The
API function rejects a nonmatching non-null response `client_id` with the
existing `RESPONSE_CLIENT_MISMATCH` behavior. It performs no numeric conversion
or result reconstruction.

## 8. Internal workspace presentation

`RetirementIncomeReadinessScreen` adds one section headed exactly:

`פער חודשי חשבוני במועד היעד`

The section is internal and Hebrew RTL. It contains one explicit calculation
action. The action is enabled only when the currently loaded persisted context
provides a canonical planning fingerprint and retirement target date and the
loaded target is current/ready. It sends those identities; it never sends form
amounts, comparison objects or browser-calculated evidence.

### 8.1 COMPLETE

For a validated `COMPLETE` response, present:

- exact approved target rational;
- exact comparable monthly-income rational;
- exact signed monthly-gap rational;
- the exact arithmetic state `SHORTFALL`, `EQUAL` or `SURPLUS` with neutral
  Hebrew wording stating only arithmetic sign;
- target, CMIA and RMIGA result fingerprints as technical traceability;
- every included contribution in backend order with its source ID, source kind,
  source version, source/amount/comparison/contribution fingerprints and exact
  monthly rational; and
- every excluded source ID in backend order.

No item is hidden because it is excluded, zero or inconvenient. No browser
sorting, aggregation, source matching or total verification is authoritative.

### 8.2 BLOCK_NO_GAP

For `BLOCK_NO_GAP`, present a neutral no-result state with the exact failure
stage, detail code, observed CMIA fingerprint/code/stage and blocked source IDs.
Do not display target, comparable income, gap, sign or numeric zero. Preserve
exact unknown codes visibly; never infer a recommendation.

### 8.3 Exact rational rendering

The browser treats numerator and denominator as strings. It must never call
`Number`, `parseInt`, `parseFloat`, `BigInt` arithmetic, decimal division,
locale numeric conversion or rounding on authoritative amounts.

The canonical display function is pure string projection:

- if denominator is exactly `"1"`, display numerator unchanged;
- otherwise display `numerator + "/" + denominator` unchanged.

Render the value in an LTR-isolated `<bdi dir="ltr">` inside the RTL section.
Currency/frequency labels may be translated, but digits and sign remain exact.

## 9. Browser lifecycle and stale-result exclusion

Gap state is separate from target and RTICB comparison state. Before starting
any gap request, clear the previous gap and abort the prior active mutation.
The response may publish only if both the captured generation and captured
workspace key still match the current client workspace.

Clear gap state synchronously on:

1. any target form edit, including amount, income basis, price basis,
   reference date or source kind;
2. target save start, success or failure;
3. explicit refresh start, success or failure;
4. client path change, including A-to-B-to-A;
5. context or target load failure;
6. gap request failure or abort;
7. authentication expiry through the existing application gate; and
8. component unmount.

Every client change/unmount increments the generation and aborts the active
controller. A late response, including an A response received after A-to-B-to-A,
cannot write state merely because the numeric client ID again equals A; its old
generation is stale. No gap, identity, source or request is written to
`localStorage`, `sessionStorage`, URL/query/hash or a global cache.

## 10. Minimal implementation allowlist

Only these paths may change in a future separately authorized implementation:

1. `backend/app/services/retirement_monthly_income_gap_service.py` — add only
   the pure immutable public-result validator; no calculation or transaction
   semantic change.
2. `backend/app/schemas/retirement_income_readiness.py` — add the strict closed
   two-field request model (or prove exact reuse of the identical existing
   model without changing its accepted behavior).
3. `backend/app/api/retirement_income_readiness_routes.py` — add the one route,
   exact single producer call, validation, binding and error mappings.
4. `backend/tests/test_rtdir_rmiga_consumer.py` — backend route, security,
   producer, response and mutation-sensitive acceptance evidence.
5. `backend/tests/test_governance_baseline.py` — exact path/route inventory only
   if required by existing governance gates.
6. `frontend/src/api/retirementIncomeReadinessApi.ts` — exact types and one API
   function.
7. `frontend/src/pages/RetirementIncomeReadinessScreen.tsx` — bounded internal
   section and lifecycle integration.
8. `frontend/src/pages/RetirementIncomeReadinessScreen.test.tsx` — ordinary,
   negative, isolation and mutation-sensitive frontend evidence.

No accepted RMIGA calculation behavior, CMIA, RIT, RTICB, Planning Input,
database model, migration, authentication middleware, application router
registration, generation-guard module or unrelated UI path may change.

## 11. Ordinary acceptance inventory

| ID | Required executable proof |
|---|---|
| `RMIGA-IWCB-AC-001` | Exact package identity, base, accepted RMIGA boundary, Class A status and eight-path allowlist; implementation remains separately unauthorized. |
| `RMIGA-IWCB-AC-002` | POST path and closed two-field strict request produce exactly one RMIGA command whose client comes only from the path. |
| `RMIGA-IWCB-AC-003` | Production session, edge, Origin and CSRF checks execute before route/Session/producer; trusted actor cannot be supplied or forged by the browser. |
| `RMIGA-IWCB-AC-004` | Nonexistent path client yields exact 404 `CLIENT_NOT_FOUND` and `/path/client_id`; body cannot address another client. |
| `RMIGA-IWCB-AC-005` | One fresh dependency Session and exactly one RMIGA invocation occur; route performs no second producer read, transaction start, write, flush, commit, rollback or retry. |
| `RMIGA-IWCB-AC-006` | RMIGA pure validator accepts an independently fixed valid COMPLETE golden and returns a recursively immutable exact copy. |
| `RMIGA-IWCB-AC-007` | COMPLETE validation proves every closed key, type, nullable field, rational, source identity, contribution/count/order/disjointness invariant, sign classification and result fingerprint. |
| `RMIGA-IWCB-AC-008` | RMIGA pure validator accepts an independently fixed valid BLOCK_NO_GAP golden and proves exact failure fields, blocked IDs, absence of numeric fields and block fingerprint. |
| `RMIGA-IWCB-AC-009` | Route separately binds validated COMPLETE client/planning/date and BLOCK client/supplied-planning/supplied-date to path/body. |
| `RMIGA-IWCB-AC-010` | COMPLETE and BLOCK_NO_GAP dictionaries are returned unchanged, with exact schema/fingerprint/source order and no-store headers. |
| `RMIGA-IWCB-AC-011` | Every mapping in Section 6 has an ordinary route oracle asserting exact status, code, field_paths, envelope and sanitized body. |
| `RMIGA-IWCB-AC-012` | RMIGA transaction cleanup remains owner-controlled on success, block, original exception and rollback failure; route never reuses a poisoned Session. |
| `RMIGA-IWCB-AC-013` | API request uses `/api`, credentials, CSRF, exact body and AbortSignal; returned client mismatch is rejected. |
| `RMIGA-IWCB-AC-014` | Section heading and explicit action use only currently persisted approved planning/date identities. |
| `RMIGA-IWCB-AC-015` | COMPLETE presents exact target, comparable income, signed gap, arithmetic state, trace fingerprints, all contributions and excluded sources in backend order. |
| `RMIGA-IWCB-AC-016` | BLOCK_NO_GAP visibly preserves exact codes/blocked IDs and renders no numeric result or zero. |
| `RMIGA-IWCB-AC-017` | Integer and non-unit arbitrary-precision positive/zero/negative rational vectors render exact string text without JavaScript numeric conversion. |
| `RMIGA-IWCB-AC-018` | SHORTFALL, EQUAL and SURPLUS wording is neutral and contains no adequacy, recommendation, funding or scenario interpretation. |
| `RMIGA-IWCB-AC-019` | Every invalidation event in Section 9 clears stale gap state; failures never leave the prior result visible. |
| `RMIGA-IWCB-AC-020` | Abort and generation checks reject late responses, including A-to-B-to-A, request failure and unmount. |
| `RMIGA-IWCB-AC-021` | No credential, actor, CSRF, client DTO, gap DTO or source evidence is stored in browser persistence or URL state. |
| `RMIGA-IWCB-AC-022` | Existing context, target, save and comparison behavior remains byte/field/order compatible under focused frontend regressions. |
| `RMIGA-IWCB-AC-023` | Governance inventory proves no endpoint, path or authority outside the allowlist and no migration/model/auth/router-registration change. |
| `RMIGA-IWCB-AC-024` | Focused backend/frontend tests and production frontend build pass at an implementation candidate; broader suites follow diff-based invalidation. |

Acceptance range: `RMIGA-IWCB-AC-001` through `RMIGA-IWCB-AC-024`; count: `24`.

## 12. Negative and mutation-sensitive acceptance inventory

| ID | Prohibited outcome / required negative proof |
|---|---|
| `RMIGA-IWCB-NAC-001` | Missing/extra/coerced body fields or invalid path/hash/date reach RMIGA. |
| `RMIGA-IWCB-NAC-002` | Missing/invalid/expired session, forged actor, wrong Origin or invalid CSRF reaches the route or producer. |
| `RMIGA-IWCB-NAC-003` | Body, query, header or browser state overrides path client or supplies target/comparable/source/arithmetic evidence. |
| `RMIGA-IWCB-NAC-004` | More than one RMIGA invocation, a direct upstream invocation, retry, route-owned transaction, write, flush, commit or second rollback occurs. |
| `RMIGA-IWCB-NAC-005` | Validator accepts extra/missing keys, wrong schema/state/type/nullability or malformed canonical identity. |
| `RMIGA-IWCB-NAC-006` | Validator accepts invalid, unreduced, noncanonical, rounded, truncated or numerically converted rational evidence. |
| `RMIGA-IWCB-NAC-007` | Coherently rehashed contribution/count/membership/order/source/disjointness/sign/schema violation passes validation. |
| `RMIGA-IWCB-NAC-008` | Invalid complete/block fingerprint or a coherently rehashed forbidden block field passes validation. |
| `RMIGA-IWCB-NAC-009` | Path/body/result client, planning fingerprint or retirement-date mismatch is accepted. |
| `RMIGA-IWCB-NAC-010` | Malformed producer evidence is returned, repaired, rehashed or converted to BLOCK_NO_GAP. |
| `RMIGA-IWCB-NAC-011` | Technical exception text, SQL, monetary evidence, hash payload, cookie or token leaks through the public error body. |
| `RMIGA-IWCB-NAC-012` | Route catches a rollback failure and returns a result, retries, or reuses the poisoned Session. |
| `RMIGA-IWCB-NAC-013` | Browser uses `Number`, `parseInt`, `parseFloat`, arithmetic `BigInt`, decimal division, locale conversion or rounding for authoritative display. |
| `RMIGA-IWCB-NAC-014` | BLOCK_NO_GAP shows a numeric target, comparable value, gap, sign or inferred zero. |
| `RMIGA-IWCB-NAC-015` | Contributions or excluded sources are hidden, reordered, deduplicated, reconstructed or reaggregated. |
| `RMIGA-IWCB-NAC-016` | Target edit/save/refresh/client change/failure/auth expiry/unmount leaves a prior gap visible. |
| `RMIGA-IWCB-NAC-017` | An aborted or stale response mutates current workspace state, including A-to-B-to-A. |
| `RMIGA-IWCB-NAC-018` | Arithmetic sign becomes adequacy, funding, recommendation, withdrawal or scenario advice. |
| `RMIGA-IWCB-NAC-019` | Existing readiness context, target, comparison, RTL, authentication or logout behavior regresses. |
| `RMIGA-IWCB-NAC-020` | Any path outside the allowlist, migration, model, middleware, app routing registration or accepted authority is modified. |
| `RMIGA-IWCB-NAC-021` | Definition acceptance is treated as implementation, downstream or production authorization. |

Material implementation evidence must use unchanged ordinary oracles and prove
PASS -> actual production mutation reached -> FAIL -> restoration -> PASS for:

1. exactly-one RMIGA invocation and forbidden direct/second producer call;
2. COMPLETE and BLOCK closed-schema/fingerprint validator branches;
3. complete contribution/count/order/source and rational/sign validation;
4. client/planning/date route binding for each result state;
5. technical-error sanitization and failed/poisoned Session non-reuse;
6. exact rational display without numeric conversion;
7. COMPLETE source/excluded order and BLOCK numeric-field exclusion; and
8. generation/workspace-key/abort protection under A-to-B-to-A.

Acceptance range: `RMIGA-IWCB-NAC-001` through `RMIGA-IWCB-NAC-021`; count: `21`.

## 13. Stop conditions

Stop definition acceptance or the affected future implementation path if:

1. `RMIGA_IWCB_ACCEPTED_RMIGA_DRIFT` — consuming the endpoint would require a
   change to accepted RMIGA calculation, schema, fingerprint or transaction
   semantics.
2. `RMIGA_IWCB_PUBLIC_VALIDATION_AMBIGUOUS` — exact COMPLETE/BLOCK validation
   cannot be extracted without recomputation or new professional semantics.
3. `RMIGA_IWCB_REQUEST_IDENTITY_AMBIGUOUS` — path, planning fingerprint or
   retirement-date binding cannot be exact.
4. `RMIGA_IWCB_TRANSACTION_OWNERSHIP_CONTRADICTION` — the route cannot use one
   fresh Session and leave all ownership/cleanup to RMIGA.
5. `RMIGA_IWCB_ERROR_MAPPING_INCOMPLETE` — a reachable exception lacks one
   deterministic sanitized mapping.
6. `RMIGA_IWCB_SECURITY_BOUNDARY_WEAKENED` — authentication, edge, Origin,
   CSRF, actor or client isolation would be bypassed or weakened.
7. `RMIGA_IWCB_EXACT_RATIONAL_PRESENTATION_UNAVAILABLE` — exact values would
   require JavaScript numeric conversion, rounding or truncation.
8. `RMIGA_IWCB_STALE_RESPONSE_ISOLATION_UNAVAILABLE` — late responses cannot be
   rejected under client churn and A-to-B-to-A.
9. `RMIGA_IWCB_EXISTING_SCREEN_REGRESSION_REQUIRED` — integration requires
   removal or semantic change of accepted target/comparison behavior.
10. `RMIGA_IWCB_SCOPE_EXPANSION_REQUIRED` — implementation requires a path
    outside the allowlist, model, migration, middleware, app router, new
    persistence, client-facing output or downstream calculation.
11. `RMIGA_IWCB_UNRESOLVED_PROFESSIONAL_DECISION` — presentation would require
    interpreting arithmetic sign as adequacy, funding or advice.

Stop-condition range: item 1 through item 11; count: `11`.

## 14. Evidence strategy and next gate

This package is complex Class A because it crosses authentication, API,
transaction, calculation-result validation and browser-lifecycle boundaries.
After independent Definition acceptance and closure on master, Governance v1.1
requires independent pre-implementation contract enumeration before any
implementation authorization. That enumeration must bind the exact exception
matrix, validator field inventory, reusable RMIGA/RTDIR fixtures, frontend
ordinary oracles and risk-scoped mutation sites. It is not a new Definition.

No unresolved professional or technical decision is identified. Section 6
reuses existing readiness-router public transport codes and adds none. No
production implementation, test execution, migration, deployment, downstream
package or production-readiness claim is authorized by this candidate.

RMIGA_INTERNAL_WORKSPACE_CONSUMER_BINDING_DEFINITION_CANDIDATE_READY_FOR_INDEPENDENT_AUDIT
