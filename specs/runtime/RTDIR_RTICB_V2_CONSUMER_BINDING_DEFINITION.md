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

## 6. Exhaustive RTICB / CRTISBA technical-to-transport contract
The existing RTDIR transport envelope is exactly `RTDIR_TRANSPORT_ERROR_V1` with keys
`schema_version`, `code`, `message`, `field_paths`, `request_id`. All transport rows
below use the existing `error(request, status, code, fields)` construction, returning
`Cache-Control: no-store, private` and `Pragma: no-cache`; `field_paths=[]` unless
explicitly stated. They never enter the HTTP 200 professional `block_no_result` flow.
There is no automatic retry for any row; a user-initiated retry is possible after
infrastructure recovery for 503 and is not automatically appropriate for 404/500.
The first matching exception family/code in the table wins. Transport authentication,
CSRF and request-schema preemption from the accepted parent RTDIR Definition remains prior.

| Producer result or exception | Reachability in RTICB V2 path | HTTP | Exact public machine code | field_paths | Retry |
|---|---|---:|---|---|---|
| Canonical RTICB V2 success or professional blocked envelope | ordinary result | 200 | none: original complete professional DTO | n/a | not automatic |
| RTICB returned malformed, missing, unrecognized, mixed-V1/V2 DTO or invalid fingerprint | reachable consumer guard | 500 | `PRODUCER_RESPONSE_INVALID` | `[]` | no automatic retry |
| RTICB returned structurally canonical non-null foreign `client_id` | reachable, identity guard precedes field-shape check | 500 | `RESPONSE_CLIENT_MISMATCH` | `[]` | no automatic retry |
| `CRTISBAError("CRTISBA_UPSTREAM_TECHNICAL_FAILURE", 503)` | reachable from `derive_in_snapshot` transitive RTISA technical exception | 503 | `RTICB_UPSTREAM_TECHNICAL_FAILURE` | `[]` | manual after recovery |
| `CRTISBAError("PRODUCER_RESPONSE_INVALID", 500)` | reachable from CRTISBA Planning/Portfolio/RTISA verification | 500 | `PRODUCER_RESPONSE_INVALID` | `[]` | no automatic retry |
| `CRTISBAError("RESPONSE_CLIENT_MISMATCH", 500)` | reachable from foreign RTISA response during CRTISBA derivation | 500 | `RESPONSE_CLIENT_MISMATCH` | `[]` | no automatic retry |
| `CRTISBAError("CLIENT_NOT_FOUND", 404)` | CRTISBA producer path reachable in isolation; ordinarily preempted by earlier RIT target path for a truly nonexistent client; preserve mapping if encountered | 404 | `CLIENT_NOT_FOUND` | `["/path/client_id"]` | no |
| `CRTISBAError("CRTISBA_DATABASE_FAILURE", 503)` | possible only if downstream wraps a DB failure through an accepted owner path; raw snapshot DBAPI is the normal in-snapshot route | 503 | `RTICB_DATABASE_FAILURE` | `[]` | manual after recovery |
| Raw `DBAPIError`, `OperationalError`, `IntegrityError` from RTICB snapshot/CRTISBA transitive reads | reachable | 503 | `RTICB_DATABASE_FAILURE` | `[]` | manual after recovery |
| `CRTISBAFingerprintConstructionError` | reachable from CRTISBA canonical JSON/hash construction | 500 | `INTERNAL_ERROR` | `[]` | no automatic retry |
| `RTICBFingerprintConstructionError` | reachable from RTICB-owned canonical JSON/hash construction | 500 | `INTERNAL_ERROR` | `[]` | no automatic retry |
| Unexpected programming, serialization, framework exception | reachable | 500 | `INTERNAL_ERROR` | `[]` | no automatic retry |
| `CRTISBAError("CRTISBA_REQUIRES_FRESH_TRANSACTION", 503)`, `CRTISBA_UNSUPPORTED_DATABASE`, `CRTISBA_ROLLBACK_FAILED` | public CRTISBA `read()/write()` transaction owner only; **not reachable** through non-owning `derive_in_snapshot`; RTICB owns freshness/transaction/rollback | n/a | n/a | n/a | n/a |
| `CRTISBA_SOURCE_NOT_FOUND`, `CRTISBA_SOURCE_NOT_CURRENT`, `CRTISBA_SOURCE_KIND_MISMATCH`, `CRTISBA_SOURCE_DECISION_FORBIDDEN`, `CRTISBA_AMOUNT_AUTHORITY_UNAVAILABLE`, and CRTISBA decision/write/flush/commit/conflict/immutability codes | public write/clear/classify or persistence route only; **not reachable** through `derive_in_snapshot(...,operation="READ")` | n/a | n/a | n/a | n/a |

The reachable `CRTISBAError` whitelist is therefore `CRTISBA_UPSTREAM_TECHNICAL_FAILURE`,
`PRODUCER_RESPONSE_INVALID`, `RESPONSE_CLIENT_MISMATCH`, `CLIENT_NOT_FOUND` and the
conditional database wrapper `CRTISBA_DATABASE_FAILURE`. An unexpected `CRTISBAError`
code or status on this in-snapshot path is **not** forwarded as an arbitrary public code;
it fails closed as HTTP 500 `INTERNAL_ERROR`, `field_paths=[]`, with the same transport
envelope and cache headers. This prevents accepted public-reader/write-only CRTISBA codes
from leaking through the consumer. No `CRTISBAError` is remapped to a professional result.

The specific catch ordering for the future RTDIR adapter is: the accepted RTDIR
authentication/request preemption; one RTICB producer call; returned result validation
with non-null foreign-client check before malformed-shape check; CRTISBA upstream-specific
errors by exact class/code/status whitelist; raw DBAPI family; RTICB-owned typed technical
errors; unexpected failures. The existing broad `PensionProductError` transport fallback
must not precede this classification for CRTISBA errors. Any RTICB domain exception
authorized by the accepted parent RTDIR mapping stays under that original mapping,
except where it would conflict with an explicitly listed CRTISBA row.

An HTTP 200 accepted RTICB result is forwarded verbatim. The adapter never repairs
source IDs, decision state, admission, reasons, fingerprints, nulls or ordering.
A valid CRTISBA professional blocked result is consumed by RTICB and appears only
inside RTICB's own accepted professional failure envelope. Invalid CRTISBA producer
objects must be classified by RTICB according to its accepted Definition; RTDIR
does not invent an additional producer authority.

Executable obligation: parameterize one real RTDIR comparison-route invocation for
each reachable class/code/status row and at least one synthetic injected forbidden
public/write-only CRTISBA error, asserting exact HTTP status, `RTDIR_TRANSPORT_ERROR_V1`
fields, `field_paths`, both cache headers, no automatic retry and a single RTICB
call. Prove that the forbidden code does not leak as its original public machine code.
Cover ordinary success and `block_no_result` as 200 controls and preemption for a
nonexistent client as a production-path test where a genuine target preemption exists.
Tests may inject typed exception values at the transport seam; producer reachability
claims must be confirmed against actual CRTISBA and RTICB entry points.
 
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
- `AC-06` Every reachable and preempted CRTISBA/RTICB technical exception is classified by the exhaustive Section 6 table, with exact HTTP/code/field_paths/transport envelope/cache headers/retry policy and ordinary plus negative test controls.
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
- `SC-02` If a real CRTISBA/RTICB producer exception is neither mapped nor demonstrably preempted by Section 6, or its mapping contradicts accepted RTDIR transport precedence, stop before implementation.
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
