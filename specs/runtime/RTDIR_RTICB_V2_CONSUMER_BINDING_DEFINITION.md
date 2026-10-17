# RTDIR / RTICB V2 Consumer Binding — Focused Definition Correction Candidate

## 1. Identity, status and authority
- Package: `RTDIR_RTICB_V2_CONSUMER_BINDING`; class: dependent Class A consumer-contract correction.
- Status: `DEFINITION_CORRECTION_CANDIDATE`; independent Definition Acceptance pending.
- Canonical base master: `30b66d79f8d196a0a57d3199729b2584e93d372c`.
- Governing protocol: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Upstream accepted RTICB Definition HEAD: `3ce6fa2a027131db52721682bf0324e30f532c36`, blob `8bc236f71fd4a565b20823b247f805901632f1fb`.
- Dependency: `RTICB-ENUM-001 EXISTING_RTDIR_CONSUMER_CONTRACT_CONFLICT`.
- Owner decision: none required; no professional, security, authentication, transaction, session, client-isolation or deployment change.
- `IMPLEMENTATION=NOT_AUTHORIZED`; `DOWNSTREAM=NOT_AUTHORIZED`; `PRODUCTION_READINESS=NOT_CLAIMED`.

## 2. Exact replacement boundary / precedence
This document is a *focused amendment* to the already accepted `RETIREMENT_TARGET_DATE_INCOME_READINESS_VERTICAL_SLICE_DEFINITION.md` solely for consumer binding of the existing `POST /api/clients/{client_id}/retirement-income-readiness/comparison` route and its frontend display. It supersedes **only** that parent Definition's Section 9.3 RTICB success/failure response-shape paragraphs, its RTICB-specific producer validations and RTICB V1 field references in Sections 9.4–9.5, and RTICB result/entry rendering field references in Section 11.3. All other provisions of the accepted RTDIR Definition continue unchanged. Where inherited acceptance tests assert a V1 RTICB payload, that assertion must be migrated to the exact V2 contract described here. This amendment does not authorize editing or weakening other RTDIR surfaces. There is no dual V1/V2 fallback or version negotiation.

RTICB accepted Definition, Sections 4, 8–11, is the *sole normative authority* for RTICB V2 DTOs, field types, nullability, professional outcome codes, stage precedence, canonical fingerprints and producer behavior. This document specifies only RTDIR consumer adaptation and must not create competing semantic or fingerprint rules.

## 3. Existing endpoint and request remain unchanged
- Route: `POST /api/clients/{client_id}/retirement-income-readiness/comparison`. Authentication, authorization, CSRF, CORS, cache policy, path identity, request JSON framing and rate limits remain governed by accepted RTDIR.
- Body contains exactly `expected_planning_calculation_input_fingerprint` and `expected_retirement_target_date`; route validates body/path and injects `client_id` once to form the three-field request expected by RTICB. No extra fields, no secondary client lookup.
- The route passes the original pristine caller-supplied `Session` to `RTICB.assess` exactly once, without prior DB access, independent RTISA/CRTISBA call, second Session, nested transaction owner or frontend-inferred source data.
- There is no new endpoint, migration, persistence, calculation, or frontend-authentication behavior.

## 4. V2 success response adapter
When RTICB returns an accepted successful V2 result, RTDIR accepts and returns it *verbatim*, with exact keys:
`schema_version`, `client_id`, `planning_calculation_input_fingerprint`, `retirement_target_date`,
`target_result_fingerprint`, `target_semantic_fingerprint`, `crtisba_result_fingerprint`,
`comparison_input_fingerprint`, `source_comparisons`, `classification_state`,
`classification_complete`, `direct_comparison_state`, `direct_comparison_ready`,
`blockers`, `comparison_result_fingerprint`.

`schema_version` is exactly `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2`.
Every entry of `source_comparisons` has the exact 22-key accepted V2 shape:
`source_id`, `source_kind`, `source_category`, `admission_state`, `rtisa_reason_codes`,
`decision_state`, `source_version`, `source_fingerprint`, `amount_authority_fingerprint`,
`decision_version`, `decision_fingerprint`, `income_basis`, `income_basis_provenance`,
`price_basis`, `price_reference_date`, `price_basis_provenance`, `target_income_basis`,
`target_price_basis`, `target_price_reference_date`, `comparison_state`, `reason_codes`,
`source_comparison_fingerprint`.

The route must not consume/require old V1 `rtisa_admission_result_fingerprint`, `target_basis`,
the V1 state-partition arrays, or V1 entry fields `rtisa_admission_state`,
`source_upstream_identity`, `source_income_basis`, `source_price_basis`,
`source_price_reference_date`. Nor may it fabricate their replacements. All accepted V2 nullable
values remain nullable, in particular absent source/amount/decision/basis authority on excluded,
delegated and unresolved paths. Response is detached plain data, returned without normalization,
reformatting, reason reordering, professional inference, hash repair or recalculation.

The RTDIR adapter checks exact schema and field shape, canonical primitive types and identities,
source order/entry coverage, and the accepted authoritative RTICB result's integrity at the
producer boundary, without recreating RTICB's classification, upstream CRTISBA source discovery
or hidden identity calculations. A superficially V2-shaped but malformed response must never
be declared valid only by checking `client_id`. RTICB remains the fingerprint owner.

## 5. V2 professional failure response adapter
A valid RTICB V2 `block_no_result` is an **HTTP 200 professional result**, not a transport
error, and is forwarded unmodified with exactly the 17 accepted keys:
`schema_version`, `client_id`, `supplied_planning_calculation_input_fingerprint`,
`supplied_retirement_target_date`, `observed_target_planning_calculation_input_fingerprint`,
`observed_target_retirement_target_date`, `observed_target_result_fingerprint`,
`observed_crtisba_planning_calculation_input_fingerprint`,
`observed_crtisba_retirement_target_date`, `observed_crtisba_result_fingerprint`,
`observed_crtisba_failure_fingerprint`, `observed_crtisba_failure_stage`,
`observed_crtisba_failure_detail_code`, `result_state`, `failure_stage`,
`failure_detail_code`, `result_fingerprint`.

`schema_version` is exactly `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2`;
`result_state` is `block_no_result`. Allowed stage/code pairs, presence/null observations and
failure identity follow RTICB Definition Sections 8–10 verbatim. Reject extra V1 RTISA observation
keys. The RTDIR route never substitutes path identity for a non-null foreign producer client,
and never treats an unvalidated CRTISBA professional block as a valid RTICB result.

## 6. Transport and producer failure boundary
- Exact valid professional success or blocked result: return HTTP 200, original JSON unchanged.
- Malformed/missing producer shape or invalid schema/version/identity: preserve the existing
  RTDIR `PRODUCER_RESPONSE_INVALID` / `RESPONSE_CLIENT_MISMATCH` transport taxonomy and
  binding precedence from the parent Definition; no API-side repair, downgrade or V1 fallback.
- RTICB documented domain failures are professional results, not newly invented HTTP errors.
- Existing RTICB database/transaction technical failures preserve the established RTDIR 503
  `RTICB_DATABASE_FAILURE` handling.
- A technical failure arising transitively from CRTISBA must follow the *actual accepted*
  CRTISBA exception class/code, mapped to an existing appropriate RTDIR 503 infrastructure
  response without converting it into `block_no_result`, inventing professional blocker codes,
  or claiming RTICB performs retries. A non-database construction/programming/hash exception
  remains HTTP 500 `INTERNAL_ERROR` under the accepted RTDIR transport envelope.
- Exact routing for each declared CRTISBA exception family must be enumerated and independently
  tested before RTDIR implementation authorization; any contradiction with accepted transport
  precedence is a Definition stop condition, not permission to invent a new status code.

## 7. Frontend projection
The existing Hebrew RTL readiness screen consumes server V2 result DTOs. It shows, in server order:
- Success: `direct_comparison_state`, `direct_comparison_ready`, ordered `blockers`.
- Each `source_comparisons` entry with `source_id`, `source_kind`, `source_category`,
  `admission_state`, `decision_state`, `income_basis`, `income_basis_provenance`,
  `price_basis`, `price_reference_date`, `price_basis_provenance`,
  `comparison_state` and ordered `reason_codes`.
- Null decision/source/basis fields are displayed neutrally, not filled with inferred values.
- Delegated/excluded entries remain visible as `NOT_ADMITTED`. Unresolved entries remain
  `BASIS_UNRESOLVED`, including valid NOT_READY CRTISBA collections.
- Blocked: exact `failure_stage` and `failure_detail_code`, and no source results.
- Unknown valid codes use neutral fallback labels and retain raw values for traceability.
No frontend code determines comparison state, professional readiness, gross/net, nominal/real,
missing decisions, totals, Gap/Surplus, tax, normalization, source admission or funding.
Existing generation/AbortController protections, cross-client isolation, current-context
refresh, caching, session expiry/logout, RTL, and error-state handling are preserved.

## 8. Executable criteria and negative boundaries
- `AC-01` V2 success exact top-level shape and version, including CRTISBA fingerprint.
- `AC-02` V2 22-field entry coverage, order, nullability and one-to-one source preservation.
- `AC-03` V2 17-field professional failure shape and permitted observation fields.
- `AC-04` Exact response client/path equality without rewriting producer output.
- `AC-05` Correct 200 professional success/blocked vs existing 500/503 transport split.
- `AC-06` Accepted CRTISBA technical exception family routed under existing RTDIR contract.
- `AC-07` Exactly one pristine-session RTICB invocation; no independent RTISA/CRTISBA read.
- `AC-08` UI binds V2 fields, state reasons, nulls and ordered blockers verbatim.
- `AC-09` No regression to authentication, CSRF, proxy security, generation isolation or RTL.
- `AC-10` V1-only response and mixed V1/V2 near-misses rejected.
- `AC-11` Original definition/implementation boundaries and accepted upstream RTICB fingerprints unchanged.
- `AC-12` No migrations/models/new API/normalization/totals/Gap/Surplus/production authorization.
- `NAC-01` Never reintroduce a V1/RTISA source-basis authority or compatibility downgrade.
- `NAC-02` Never silently drop, rename, infer or reorder professional producer fields.
- `NAC-03` Never treat a professional blocked result as a technical 500/503 or vice versa.
- `NAC-04` Never bypass accepted session, security, client or transaction ownership controls.
- `NAC-05` Never have frontend derive amounts, basis conversions or comparison readiness.
- `NAC-06` Never accept a V1 DTO merely because its client identity matches.
- `SC-01` If any accepted RTICB V2 DTO cannot be represented under the existing route/UI without professional inference, stop and return for Definition correction.
- `SC-02` If CRTISBA technical exception handling cannot be mapped to accepted RTDIR transport behavior without invented status/code semantics, stop.
- `SC-03` If implementation requires modifying accepted RTICB, CRTISBA, session, authorization or transaction authority, stop.
- `SC-04` If full nullable/source-identity coverage or deterministic malformed-output detection cannot be tested, stop.

## 9. Implementation and evidence boundaries
Expected eventual scope, *only after independent Definition Acceptance, governed closure and
separate authorization*: `backend/app/api/retirement_income_readiness_routes.py`,
`backend/tests/test_rtdir_vertical_slice.py`,
`backend/tests/test_rtdir_producer_inventory.py`,
`frontend/src/pages/RetirementIncomeReadinessScreen.tsx`,
`frontend/src/pages/RetirementIncomeReadinessScreen.test.tsx`, and limited API typing/tests if
needed. No production code changed by this Definition candidate.

For focused independent Definition Acceptance, verify against immutable RTICB V2 result shape
and actual CRTISBA technical exception family; confirm that this document supersedes only
the specified V1 consumer-binding paragraphs rather than the rest of RTDIR's large accepted
definition. Before separate implementation permission, enumerate real producer return paths,
request preemption, transport precedence, and frontend null/ordering mutation oracles.
No double audit of accepted RTICB professional semantics is authorized by this addendum.
