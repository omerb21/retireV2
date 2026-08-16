# PKG-015 Final Package Definition

## 1. Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-015` |
| Title | `M10 Stateless Persisted-Result Comparator Foundation` |
| Module | `M10` |
| M10 role | `COMPARATOR_ONLY` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Definition base | `6783eb50bb90291f38ddce68a429fe6085f3a1ff` |
| Accepted PKG-014 implementation HEAD | `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d` |
| Entering Alembic head | `e6b4c8d2f507` |

This document is a definition draft for independent acceptance audit. It is
not an accepted definition, implementation authorization, migration
authorization, professional recommendation, production-readiness decision, or
V1/V2 parity claim.

## 2. Authoritative Sources and Predecessor Boundaries

- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.
- Accepted PKG-013 contracts for `deterministic_monthly_cashflow/v1`, which
  remain unchanged.
- Accepted PKG-014 definition, implementation, evidence matrix, and acceptance
  record on master at `6783eb50bb90291f38ddce68a429fe6085f3a1ff`.
- Accepted PKG-014 implementation boundary
  `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d`.
- Frozen M10 design inputs approved by GPT Chat and reproduced normatively in
  this definition.

PKG-015 must consume accepted persisted M09 evidence without changing,
recalculating, normalizing, or reinterpreting M09 meaning.

## 3. Exact Product Outcome

PKG-015 defines the first narrow M10 comparator. It admits exactly one valid
pair consisting of a server-owned baseline-subject run in the `reference` role
and one adjusted-subject run in the `compared` role. For admitted pairs it
returns persisted M09 values side by side, exact numeric deltas, numeric
relations, persisted range-total deltas, and a deterministic server-owned
comparison fingerprint.

The output is mathematical comparison evidence only. It does not state that a
difference is desirable, significant, suitable, preferred, recommended, or
professionally sufficient.

## 4. Normative Authority Boundary

The M10 role is exactly `COMPARATOR_ONLY`.

M10 may own only:

- pair admission under this exact contract;
- retrieval and integrity verification of accepted persisted M09 run material;
- side-by-side exposure of directly persisted comparable values;
- exact Decimal subtraction;
- exact numeric relation classification; and
- deterministic comparison-payload fingerprinting.

M10 must not calculate or reconstruct upstream business values. M09 remains
the sole owner of its factual resolution, scenario aggregation, monthly
results, range totals, currentness, and per-run M10 eligibility. M10 does not
become an authority for M01-M09, tax, fixation, pension conversion, investment,
recommendation, ranking, selection, reports, or downstream M11/M12 admission.

## 5. Supported Scenario Contract

The only supported contract is:

- `scenario_family = declared_retirement_cashflow_adjustments`
- `scenario_contract_version = v1`

There is no generic compatibility registry, alias, fallback, caller-selected
family, or caller-selected version. An unsupported family/version fails closed.
Future family or version support requires a separately accepted contract.

## 6. M10 Contract Identifiers

The first-stage identifiers are exactly:

- `comparison_contract_version = m10-scenario-comparison-v1`
- `pair_admission_contract = m10-pair-admission-v1`
- `comparison_result_schema = m10-comparison-result-v1`
- `comparison_fingerprint_schema = m10-comparison-fingerprint-v1`

All four values are server-owned trusted constants. The caller cannot provide,
override, alias, or negotiate them.

## 7. Fixed Comparison Roles

The roles are semantic and immutable:

- `reference_run_id`: run of the unique server-owned PKG-014 baseline subject.
- `compared_run_id`: run of one PKG-014 adjusted subject containing at least
  one accepted declared adjustment.

The runs must reference different `scenario_subject_id` values. The server
resolves and validates subject type and sealed manifest evidence. The caller
cannot reverse roles, declare a baseline, or supply subject type. PKG-015 does
not support adjusted-versus-adjusted or arbitrary role reversal.

## 8. Pair Admission Contract

A comparison succeeds only when every condition below passes atomically:

1. Both run IDs resolve inside the requested client scope.
2. Both runs and both subjects belong to that same client.
3. The subjects are distinct.
4. Both runs use the exact supported scenario family/version.
5. `reference` is the unique server-owned baseline subject with a sealed
   canonical empty adjustment manifest and
   `server_resolved_no_scenario_adjustments` evidence.
6. `compared` is an adjusted subject with at least one sealed accepted declared
   adjustment.
7. Both horizons have identical `start_month` and `end_month`.
8. Both runs are current under `m09-subject-currentness-v1`.
9. Both runs are eligible under `m09-to-m10-eligibility-v2`.
10. Subject integrity, sealed-manifest parity, factual inventory, upstream
    snapshot, monthly result, semantic result, and result integrity checks pass.
11. The adjustment manifests are calculation-semantically different.
12. Persisted `factual_baseline_material_fingerprint` values are exactly equal.
13. Persisted `component_domain_contract_version` values are exactly equal and
    supported.
14. Trusted factual M09 engine/result-schema versions are exactly equal and
    supported.
15. Trusted subject aggregation engine/result-schema versions are exactly
    equal and supported.
16. Relevant factual upstream source/contract versions are exactly equal.
17. The ordered persisted month-key sequences are exact, complete, unique, and
    equal.

Individual per-run eligibility cannot replace pair-level equality checks. Any
failed condition blocks the entire comparison; there is no partial response.

## 9. Trusted Version Sources

Admission uses only persisted or server-owned accepted sources already present
in PKG-014:

| Admission dimension | Authoritative source |
|---|---|
| Component-domain contract | Persisted `M09SubjectRun.component_domain_contract_version`, expected `m09-component-domains-v1` |
| Factual M09 engine | Accepted server constant `ENGINE_VERSION`, expected `m09-aggregation-v1`, bound into persisted `factual_baseline_material_fingerprint` and revalidated by eligibility v2 |
| Factual M09 result schema | Accepted server constant `RESULT_SCHEMA_VERSION`, expected `m09-result-v1`, bound into persisted `factual_baseline_material_fingerprint` and revalidated by eligibility v2 |
| Subject aggregation engine | Persisted `M09SubjectRun.upstream_snapshot.engine_version`, expected `m09-subject-aggregation-v1` |
| Subject result schema | Persisted `M09SubjectRun.upstream_snapshot.result_schema_version`, expected `m09-subject-result-v1` |
| Subject snapshot schema | Persisted `M09SubjectRun.upstream_snapshot.snapshot_schema_version`, expected `m09-subject-upstream-snapshot-v1` |
| Factual inventory schema | Persisted `M09SubjectRun.factual_inventory.inventory_schema_version`, expected `m09-resolved-component-inventory-v1` |
| Factual upstream versions | For every included candidate in persisted `factual_inventory.domains`, exact `domain_identity`, `candidate_identity`, `source_identity`, `source_version`, and `source_fingerprint`; for included M06 component evidence, exact `provenance.handoff_contract_version`, expected `m06-to-m09-monthly-amount-v1` |

The canonical relevant-upstream-version projection includes only candidates
whose persisted `included` value is `true`, ordered by `domain_identity`, then
`candidate_identity`. Each projected candidate binds the exact fields named in
the table. M06 projected component provenance additionally binds the handoff
contract version. Missing, duplicate, malformed, unknown, or unequal version
material fails closed. M10 must not invent `unversioned` as a fallback; it may
compare an already persisted literal `unversioned` only when both otherwise
eligible runs contain the exact same server-produced source material and all
integrity and factual-baseline equality checks pass.

## 10. Currentness and Eligibility

Admission re-evaluates both runs at request time through the accepted PKG-014
currentness and eligibility authorities. Required values are:

- `assessment_contract_version = m09-subject-currentness-v1`
- `is_current = true`
- `eligibility_contract_version = m09-to-m10-eligibility-v2`
- `eligible_for_m10 = true`

Caller-authored currentness, eligibility, reason codes, assessment timestamps,
or contract identifiers are never trusted.

## 11. Directly Comparable Persisted Fields

For every persisted monthly result row, M10 may compare only:

- `month`
- `gross_inflow_total`
- `gross_outflow_total`
- `period_net`

For persisted `range_totals`, M10 may compare only:

- `gross_inflow_total`
- `gross_outflow_total`
- `period_net`

M10 must use the accepted persisted values as read and integrity-verified. It
must not derive a missing value.

## 12. Arithmetic Contract

The sign convention is exactly:

`delta_direction = compared_minus_reference`

For every comparable persisted monetary value:

`delta = compared_value - reference_value`

Allowed arithmetic is limited to exact Decimal subtraction and exact numeric
comparison. The closed relation vocabulary is:

- `equal`
- `compared_greater_than_reference`
- `compared_lower_than_reference`

The relation is numeric only, including for outflows. It carries no favorable,
unfavorable, better, worse, preferred, or suitability meaning.

## 13. Delta Numeric Domain and Serialization

Persisted M09 inputs are bounded by `Numeric(20,2)`. Exact subtraction must
support the full closed domain:

- minimum: `-1999999999999999999.98`
- maximum: `1999999999999999999.98`

PKG-015 is stateless and does not store the delta in `Numeric(20,2)`. Every
reference value, compared value, and delta is serialized as a canonical exact
Decimal string:

- exactly two fractional digits;
- no scientific notation;
- no plus sign, separators, whitespace, or silent rounding;
- no leading integer zero except the single zero in `0.00`;
- a minus sign only for a strictly negative value;
- negative zero canonicalized to `0.00`; and
- delta shape `^-?(0|[1-9][0-9]{0,18})\.[0-9]{2}$`, additionally bounded by
  the closed delta domain above.

Float authority, clipping, coercion, implicit quantization, and non-finite
values are prohibited. Any precision or representability conflict fails closed.

## 14. Monthly Alignment Contract

Both runs must have:

- identical `start_month`;
- identical `end_month`;
- identical ordered `monthly_results[].month` sequences;
- no missing month;
- no extra month;
- no duplicate month; and
- every expected inclusive month represented exactly once.

M10 must validate the sequence as exposed by the accepted persisted M09 read
path. It must not independently sort, reindex, insert zero rows, drop rows, or
otherwise conceal a persisted ordering or membership mismatch. Partial-range
comparison is not supported.

## 15. Prohibited Reconstruction

PKG-015 must not:

- sum components to reconstruct monthly totals;
- sum monthly rows to reconstruct `range_totals`;
- recompute `period_net`;
- recompute component values;
- insert missing-month zeros;
- sort or reindex mismatched result material;
- normalize, annualize, prorate, interpolate, or calculate percentages;
- apply materiality thresholds;
- calculate tax, fixation, exemption, pension, conversion, investment return,
  NPV, score, weighted score, forecast, or probability; or
- rank, recommend, optimize, select, or assess suitability.

Persisted values are compared as-is or the request fails closed.

## 16. Stateless Architecture

PKG-015 introduces no persistence. It explicitly excludes:

- comparison model or table;
- migration;
- persisted comparison or history;
- selected comparison;
- comparison currentness;
- review, supersession, correction, archival, or revocation lifecycle; and
- downstream comparison eligibility.

Each request repeats all M09 admission and integrity checks. A response is
point-in-time evidence only, not a “current comparison.” A later request may
fail if either M09 run becomes stale, superseded, ineligible, or invalid.

## 17. API Contract

The only PKG-015 endpoint is:

`POST /api/clients/{client_id}/m10/compare`

The strict request body is exactly:

```json
{
  "reference_run_id": "string",
  "compared_run_id": "string"
}
```

The request schema uses `extra = forbid`. `client_id` appears only in the path.
The body cannot contain family, version, subject type, horizon, currentness,
eligibility, fingerprints, engine versions, schema versions, baseline marker,
actor, timestamp, result material, or comparison output.

The endpoint performs admission and comparison atomically. There is no separate
validation, admission, preview, currentness, history, or selection endpoint.

## 18. Failure Shape and Status Boundary

- Foreign or nonexistent run IDs return HTTP `404` with public code
  `comparison_run_unavailable`.
- Strict request-schema violations return HTTP `422` through the repository's
  standard validation envelope.
- All other pair-admission blockers return HTTP `409` through the repository's
  structured error envelope with one public code from the closed vocabulary.
- A blocked request returns no monthly comparison, range comparison, delta, or
  comparison fingerprint.

If multiple non-leaking admission failures are present, the service evaluates
the fixed admission order in Section 8 and returns the first applicable public
code. Internal diagnostics may retain multiple reasons but cannot leak foreign
resource existence.

## 19. Closed Blocking Vocabulary

The public first-stage vocabulary is exactly:

- `comparison_run_unavailable`
- `comparison_same_subject`
- `comparison_pair_role_invalid`
- `comparison_scenario_contract_mismatch`
- `comparison_horizon_mismatch`
- `comparison_factual_baseline_material_mismatch`
- `comparison_component_domain_contract_mismatch`
- `comparison_engine_version_mismatch`
- `comparison_result_schema_version_mismatch`
- `comparison_factual_upstream_version_mismatch`
- `comparison_run_not_current`
- `comparison_run_not_eligible`
- `comparison_fingerprint_invalid`
- `comparison_semantically_identical_manifest`
- `comparison_month_alignment_mismatch`
- `comparison_numeric_domain_invalid`

There is no public `comparison_client_mismatch`. Foreign ownership is mapped to
`comparison_run_unavailable` before existence-sensitive behavior.

## 20. Client Isolation and Non-Leakage

Every run, subject, monthly-result, currentness, and eligibility lookup is
scoped by the route `client_id`. Foreign IDs and nonexistent IDs are publicly
indistinguishable in status, code, and response shape. The service must not load
a run globally and then reveal that its client differs. Direct-service paths
must enforce the same boundary as the public route.

The caller cannot supply trusted ownership, role, subject type, contract,
version, currentness, eligibility, provenance, or fingerprint evidence.

## 21. Successful Response Schema

A successful response exposes at minimum:

- `comparison_contract_version`
- `pair_admission_contract`
- `comparison_result_schema`
- `comparison_fingerprint_schema`
- `comparison_fingerprint`
- `delta_direction`
- `client_id`
- `reference_run`
- `compared_run`
- `scenario_family`
- `scenario_contract_version`
- `horizon`
- `factual_baseline_material_fingerprint`
- `component_domain_contract_version`
- trusted factual and subject engine/result-schema versions
- relevant factual upstream version projection
- `monthly_comparisons`
- `range_total_comparisons`

Each role-bound run identity/provenance object includes `run_id`,
`scenario_subject_id`, `subject_type`, `calculation_semantic_fingerprint`,
`subject_integrity_fingerprint`, `adjustment_manifest_fingerprint`,
`upstream_snapshot_fingerprint`, `semantic_result_fingerprint`, and
`result_integrity_fingerprint`.

Each monthly comparison includes `month` plus comparison objects for
`gross_inflow_total`, `gross_outflow_total`, and `period_net`. Each range-total
comparison includes the same three field names. Every comparison object includes
exactly `reference_value`, `compared_value`, `delta`, and `relation`.

## 22. Deterministic Comparison Fingerprint

The comparison fingerprint is the lowercase hexadecimal SHA-256 digest of the
exact canonical comparison payload using the accepted repository
canonicalization:

- convert supported values to JSON-compatible canonical values;
- serialize JSON with UTF-8, `ensure_ascii = false`, lexicographically sorted
  object keys, and compact separators `,` and `:`;
- preserve array order;
- preserve semantic `reference` then `compared` role order; and
- exclude the `comparison_fingerprint` field itself from its input.

The fingerprint payload binds at minimum:

- all four M10 contract identifiers;
- `delta_direction`;
- client ID;
- role-bound run and subject IDs;
- supported scenario family/version;
- horizon;
- factual-baseline material fingerprint;
- component-domain contract version;
- factual and subject engine/result-schema versions;
- relevant factual upstream version projection;
- both run semantic and integrity fingerprints;
- both subject semantic and integrity fingerprints;
- both adjustment-manifest fingerprints;
- ordered monthly result fingerprints; and
- the exact canonical monthly and range-total comparison payload.

The role pair must never be sorted before hashing. Actor, request timestamp,
request ID, display labels, and metadata-only fields are excluded from semantic
identity.

## 23. Currentness, Staleness, and Point-in-Time Meaning

Admission occurs at request time. If either run becomes superseded, non-current,
ineligible, fingerprint-invalid, factually stale, or upstream-version stale, a
new request fails closed. Previously returned payloads are historical
point-in-time evidence only. PKG-015 adds no mutation, revocation, or currentness
lifecycle for comparisons.

## 24. Frontend Boundary

PKG-015 contains no frontend work: no route integration, screen, comparison
card, UI state, async workflow, or client-side comparison. A future frontend
package requires separate definition and authorization after comparator
authority is accepted.

## 25. Recommendation and Ranking Prohibition

No response, error, schema, route, field, or internal semantic value may express
or imply:

- better or worse scenario;
- preferred or recommended scenario;
- rank, score, or weighted score;
- suitability or professional recommendation;
- retirement, tax, pension, or capital optimization;
- significance or materiality;
- forecast or probability; or
- automated selection.

## 26. PKG-013 and PKG-014 Preservation

PKG-015 does not retrofit or rewrite existing runs. It does not change:

- `deterministic_monthly_cashflow/v1`;
- `m09-currentness-v1`;
- `m09-to-m10-eligibility-v1`;
- `declared_retirement_cashflow_adjustments/v1`;
- `m09-subject-currentness-v1`;
- `m09-to-m10-eligibility-v2`;
- accepted M09 persistence, formulas, fingerprints, or predecessor chains; or
- accepted PKG-014 baseline/adjusted meaning.

## 27. Explicit Deferred and Excluded Scope

Deferred or excluded from PKG-015 are:

- comparison persistence and history;
- comparison currentness, review, selection, supersession, and archival models;
- frontend;
- adjusted-versus-adjusted comparison;
- more than two scenarios;
- other scenario families or versions;
- a generic compatibility registry;
- partial-horizon comparison or missing-value rules;
- percentage change and materiality thresholds;
- recommendation, ranking, optimization, suitability, or selection;
- report or client-output authority;
- downstream M11/M12 eligibility or execution;
- M13/M14 work;
- M08E;
- changes to `02M`;
- production readiness; and
- V1/V2 parity.

Broader Q-019 and Q-020 concerns remain deferred. This package freezes only the
narrow baseline-versus-one-adjusted numeric comparator contract.

## 28. Expected Implementation Shape

If separately authorized after definition acceptance, the expected shape is a
strict request/response schema, one client-scoped route, a stateless service,
read-only use of accepted M09 persistence and services, deterministic Decimal
and fingerprint helpers, and focused/full backend tests. No migration,
comparison model, persistence, frontend, or implementation is authorized by
this section.

## 29. Stop Conditions

Future implementation must stop and return the named blocker if any condition
is required:

1. `PKG_015_UPSTREAM_RECALCULATION_REQUIRED`
2. `PKG_015_NON_PERSISTED_VALUE_COMPARISON_REQUIRED`
3. `PKG_015_PAIR_ROLE_BYPASS_REQUIRED`
4. `PKG_015_CALLER_FORGED_AUTHORITY_REQUIRED`
5. `PKG_015_FOREIGN_RESOURCE_LEAKAGE_BLOCKED`
6. `PKG_015_MONTH_ALIGNMENT_BYPASS_REQUIRED`
7. `PKG_015_PARTIAL_COMPARISON_REQUIRED`
8. `PKG_015_DECIMAL_DOMAIN_CONFLICT`
9. `PKG_015_COMPARISON_PERSISTENCE_REQUIRED`
10. `PKG_015_FRONTEND_REQUIRED`
11. `PKG_015_RECOMMENDATION_OR_RANKING_REQUIRED`
12. `PKG_015_ADJUSTED_VS_ADJUSTED_REQUIRED`
13. `PKG_015_UNSUPPORTED_SCENARIO_CONTRACT_REQUIRED`
14. `PKG_015_PREDECESSOR_SEMANTIC_REWRITE_REQUIRED`
15. `PKG_015_M11_PLUS_AUTHORITY_REQUIRED`

Stop conditions are definition boundaries, not implementation authorization.

## 30. Acceptance Criteria

- **AC-015-001:** Definition work starts on `pkg-015-review` from exact base `6783eb50bb90291f38ddce68a429fe6085f3a1ff` with only the authorized documentation changes.
- **AC-015-002:** Package identity, title, M10 module, and `COMPARATOR_ONLY` role are exact, and implementation remains unauthorized.
- **AC-015-003:** Only `declared_retirement_cashflow_adjustments/v1` is supported; every other family/version fails closed without a compatibility fallback.
- **AC-015-004:** The four M10 contract identifiers are exact server-owned constants and cannot be caller supplied.
- **AC-015-005:** The request roles are exactly baseline `reference_run_id` and adjusted `compared_run_id`; arbitrary reversal and adjusted-versus-adjusted are rejected.
- **AC-015-006:** Both runs and subjects are resolved within one route-client scope before existence-sensitive behavior.
- **AC-015-007:** Foreign and nonexistent run IDs are publicly identical as `comparison_run_unavailable`.
- **AC-015-008:** Pair admission requires distinct subjects and exact reference-baseline/compared-adjusted sealed-manifest semantics.
- **AC-015-009:** Both runs must be current under `m09-subject-currentness-v1` at request time.
- **AC-015-010:** Both runs must be eligible under `m09-to-m10-eligibility-v2` at request time.
- **AC-015-011:** Subject, manifest, inventory, snapshot, monthly-result, semantic-result, and result-integrity verification is fail closed.
- **AC-015-012:** Pair admission requires exact equal persisted `factual_baseline_material_fingerprint` values.
- **AC-015-013:** Pair admission requires exact equal supported `component_domain_contract_version` values.
- **AC-015-014:** Exact factual and subject engine/result-schema sources and expected values are defined without fallback.
- **AC-015-015:** Relevant included factual upstream source versions/fingerprints and M06 handoff contract versions are canonically projected and exactly equal.
- **AC-015-016:** Horizons and complete ordered persisted month-key sequences are exactly equal, unique, and gap free.
- **AC-015-017:** No partial-range, missing-month, extra-month, duplicate-month, zero-fill, sorting, or reindexing path exists.
- **AC-015-018:** Only persisted monthly `gross_inflow_total`, `gross_outflow_total`, and `period_net` are compared directly.
- **AC-015-019:** Only persisted `range_totals` fields with those exact three names are compared directly.
- **AC-015-020:** No monthly, range, component, or net value is reconstructed or normalized.
- **AC-015-021:** Delta direction is exactly `compared_minus_reference` for every value.
- **AC-015-022:** Relations use only `equal`, `compared_greater_than_reference`, and `compared_lower_than_reference` as numeric facts.
- **AC-015-023:** Decimal subtraction is exact, float-free, and supports the full difference domain without `Numeric(20,2)` overflow.
- **AC-015-024:** Reference, compared, and delta outputs use the frozen canonical two-decimal string format without scientific notation or rounding.
- **AC-015-025:** A successful response contains the exact contract, identity, provenance, horizon, version, monthly, range, and fingerprint evidence defined here.
- **AC-015-026:** The comparison fingerprint uses accepted canonical JSON plus SHA-256 and binds role order, version evidence, run/subject fingerprints, ordered result fingerprints, and exact comparison payload.
- **AC-015-027:** Actor, request time, request ID, and display labels do not affect comparison semantic identity.
- **AC-015-028:** PKG-015 is stateless and each request re-evaluates admission; responses are point-in-time evidence only.
- **AC-015-029:** No comparison model, table, migration, history, currentness, lifecycle, or downstream eligibility is introduced.
- **AC-015-030:** Exactly one endpoint exists: `POST /api/clients/{client_id}/m10/compare`.
- **AC-015-031:** The strict request body contains only `reference_run_id` and `compared_run_id`, with `extra = forbid`.
- **AC-015-032:** There is no separate validation/admission endpoint or split-brain validation state.
- **AC-015-033:** Every blocker returns no partial comparison payload or comparison fingerprint.
- **AC-015-034:** Public blocker codes, status boundaries, and deterministic admission order are closed and non-leaking.
- **AC-015-035:** No frontend route, component, UI state, or client-side comparison is included.
- **AC-015-036:** No recommendation, ranking, optimization, suitability, significance, materiality, forecast, or probability semantics are included.
- **AC-015-037:** Accepted PKG-013 and PKG-014 families, currentness, eligibility, persistence, formulas, fingerprints, and history remain unchanged.
- **AC-015-038:** M11-M14 remain unauthorized, M08E remains excluded, and `02M` remains frozen.
- **AC-015-039:** Verification proves exactly the definition file and narrow Business Build Plan synchronization changed, with protected paths untouched.
- **AC-015-040:** The only next gate is independent definition acceptance audit; M10 implementation and the next package remain `NOT_AUTHORIZED`.

## 31. Negative Acceptance Criteria

- **NAC-015-001:** Any family/version other than `declared_retirement_cashflow_adjustments/v1`.
- **NAC-015-002:** Generic compatibility registry, alias, negotiation, fallback, or caller-selected contract.
- **NAC-015-003:** Adjusted-versus-adjusted, baseline-versus-baseline, arbitrary role reversal, or more than two runs.
- **NAC-015-004:** Caller-authored baseline marker, subject type, family, version, horizon, currentness, eligibility, or fingerprint authority.
- **NAC-015-005:** Global run lookup followed by foreign-client disclosure or public `comparison_client_mismatch`.
- **NAC-015-006:** Same-subject comparison or semantically identical adjustment manifests.
- **NAC-015-007:** Admission of a non-current, ineligible, superseded, stale, failed, unsupported, or integrity-invalid run.
- **NAC-015-008:** Admission when factual-baseline material fingerprints differ.
- **NAC-015-009:** Admission when component-domain, engine, result-schema, snapshot-schema, inventory-schema, source-version, or M06 handoff-version material differs or is unsupported.
- **NAC-015-010:** Missing, extra, duplicate, reordered, partial, or unequal month sequence.
- **NAC-015-011:** Fill-with-zero, sorting, reindexing, interpolation, proration, annualization, or normalization.
- **NAC-015-012:** Summing components to recreate monthly totals.
- **NAC-015-013:** Summing monthly rows to recreate range totals.
- **NAC-015-014:** Recomputing `period_net` or any persisted M09 value.
- **NAC-015-015:** Comparison of a non-persisted or caller-provided monetary value.
- **NAC-015-016:** Float authority, scientific notation, implicit quantization, silent rounding, clipping, or overflow.
- **NAC-015-017:** Delta direction other than `compared_minus_reference`.
- **NAC-015-018:** Qualitative relation such as better, worse, preferred, suitable, or recommended.
- **NAC-015-019:** Percentage change or materiality/significance threshold.
- **NAC-015-020:** Tax, fixation, exemption, pension, conversion, investment, NPV, probability, or forecast calculation.
- **NAC-015-021:** Rank, score, weighted score, recommendation, optimization, suitability, or automatic selection.
- **NAC-015-022:** Partial comparison response or fingerprint after any blocker.
- **NAC-015-023:** Comparison persistence, table, migration, history, currentness, review, supersession, archival, or revocation lifecycle.
- **NAC-015-024:** Separate validation, admission, preview, selection, currentness, or history endpoint.
- **NAC-015-025:** Request-body `client_id` or any field beyond the two role-bound run IDs.
- **NAC-015-026:** Frontend route, screen, card, state, async workflow, or browser-side comparison.
- **NAC-015-027:** Retrofit or rewrite of PKG-013/PKG-014 runs, semantics, currentness, eligibility, fingerprints, or persistence.
- **NAC-015-028:** M11/M12 downstream eligibility, report authority, or execution.
- **NAC-015-029:** M13/M14 work, M08E work, or change to `02M`.
- **NAC-015-030:** Production-readiness or V1/V2 parity claim.
- **NAC-015-031:** Implementation code, test, migration, persistence, frontend, or acceptance record during definition drafting.
- **NAC-015-032:** Authorization of PKG-015 implementation or any next package by this definition.

## 32. Verification Matrix

| Area | Required future evidence |
|---|---|
| Base/scope | Exact branch/base; docs-only definition diff; protected paths untouched |
| Contract/roles | Exact family/version and baseline-reference/adjusted-compared enforcement |
| Admission | Same-client, distinct subjects, currentness v1, eligibility v2, integrity, horizon, factual and version equality |
| Non-leakage | Foreign and nonexistent run/service paths return equivalent public behavior |
| Persisted values | Direct monthly/range field reads; no component/month reconstruction |
| Alignment | Exact ordered complete month sequence; mismatch blocks |
| Arithmetic | Decimal-only subtraction, full delta domain, canonical string output, numeric relation |
| Fingerprint | Canonical role-bound payload and deterministic SHA-256 replay |
| Statelessness | No model/table/migration/history/currentness/lifecycle |
| API | One strict atomic compare endpoint and no validation route |
| Authority audit | No recommendation, ranking, materiality, optimization, report, or M11+ semantics |
| Regression | PKG-013 and PKG-014 behavior and artifacts unchanged |

## 33. Authorization Boundary

- PKG-015 definition acceptance: `NOT_YET_DECIDED`.
- PKG-015 implementation: `NOT_AUTHORIZED`.
- Migration creation or execution: `NOT_AUTHORIZED`.
- Persistence: `NOT_AUTHORIZED`.
- Frontend: `NOT_AUTHORIZED`.
- M11-M14 implementation: `NOT_AUTHORIZED`.
- Next package: `NOT_AUTHORIZED`.
- M08E: `EXCLUDED`.
- `02M`: `FROZEN`.
- Production readiness: `NOT_CLAIMED`.

The only permitted next gate is independent PKG-015 definition acceptance
audit.

PKG_015_DEFINITION_PROPOSED_FOR_ACCEPTANCE
