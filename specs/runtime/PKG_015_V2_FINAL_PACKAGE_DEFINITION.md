# PKG-015 V2 Corrected Package Definition

## 1. Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-015` |
| Title | `M10 Stateless Persisted-Result Comparator Foundation` |
| Module | `M10` |
| M10 role | `COMPARATOR_ONLY` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |
| Definition base | `8a0bd85a98d78f39d19eee937989b7ddd0192844` |
| Accepted PKG-014 implementation HEAD | `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d` |
| Entering Alembic head | `e6b4c8d2f507` |
| Original accepted v1 definition HEAD | `fcadcaf33cc877014ea84dc13eb9d83205ae9b4e` |
| Original v1 acceptance evidence | `1c302e0d760ab7e66c94c6c1695fc71cda6b4e7d` |
| Frozen v1 implementation candidate | `aca250f50409e569b30552ec312818ce50dcfc74` |

This document is a definition draft for independent acceptance audit. It is
not an accepted definition, implementation authorization, migration
authorization, professional recommendation, production-readiness decision, or
V1/V2 parity claim.

This artifact is a prospective contract correction. It preserves the original
accepted v1 definition and its acceptance record as immutable historical
evidence. If independently accepted, this v2 contract supersedes v1 only for
future PKG-015 implementation and re-audit. It does not retroactively reinterpret
v1 and does not accept the frozen v1 implementation candidate.

## 2. Authoritative Sources and Predecessor Boundaries

- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md`.
- Accepted PKG-013 contracts for `deterministic_monthly_cashflow/v1`, which
  remain unchanged.
- Accepted PKG-014 definition, implementation, evidence matrix, and acceptance
  record preserved on master.
- Accepted PKG-014 implementation boundary
  `0fd7fb82c3cea99dde4be098d6cb82b08c25c76d`.
- Frozen M10 design inputs approved by GPT Chat and reproduced normatively in
  this definition.
- Original accepted PKG-015 v1 definition
  `specs/runtime/PKG_015_FINAL_PACKAGE_DEFINITION.md` at immutable HEAD
  `fcadcaf33cc877014ea84dc13eb9d83205ae9b4e`.
- Original PKG-015 v1 definition acceptance record
  `specs/runtime/PKG_015_definition_acceptance_record.md` at evidence commit
  `1c302e0d760ab7e66c94c6c1695fc71cda6b4e7d`.

PKG-015 must consume accepted persisted M09 evidence without changing,
recalculating, normalizing, or reinterpreting M09 meaning.

### 2.1 Accepted Predecessor Facts

The corrected contract recognizes these repository facts as normative:

1. `M09SubjectMonthlyResult` persists `month` and no ordinal or sequence field.
2. Persistence guarantees unique `(run_id, month)` membership.
3. The accepted PKG-014 read authority returns rows in canonical chronological
   `ORDER BY month` representation.
4. `m09-subject-currentness-v1` requires that authoritative representation to
   equal the complete inclusive `_month_range(start_month, end_month)`.
5. Missing, extra, duplicate, or incomplete per-run membership therefore makes
   the run non-current before M10 pair-level month admission.
6. Physical database row or insertion order is not persisted semantic evidence.
7. A “reordered persisted sequence” is not representable under the accepted
   predecessor contract and must not be manufactured by M10.

No M09 ordinal, migration, persistence change, currentness bypass, eligibility
bypass, or alternate unordered read path is authorized or required.

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

The corrected v2 identifiers are exactly:

- `comparison_contract_version = m10-scenario-comparison-v2`
- `pair_admission_contract = m10-pair-admission-v2`
- `comparison_result_schema = m10-comparison-result-v2`
- `comparison_fingerprint_schema = m10-comparison-fingerprint-v2`

All four values are server-owned trusted constants. The caller cannot provide,
override, alias, or negotiate them.

V2 identifiers are mandatory because predecessor-compatible admission changes
externally observable blocker semantics. The identifiers also enter the success
response and fingerprint material; changing admission under v1 identifiers
would silently reinterpret accepted v1 evidence and is prohibited.

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

A comparison succeeds only when every predicate in the authoritative ordered
mapping below passes atomically. Individual per-run eligibility cannot replace
pair-level equality checks. A failure blocks the entire comparison; there is no
partial response.

### 8.1 Authoritative Predicate-to-Public-Code Order

The phases and rows below are normative. For a given persisted pair, every
compliant implementation MUST return the same first failing public code. An
implementation MUST NOT choose another code merely because multiple predicates
fail.

| Global order | Phase and exact predicate order | Public code |
|---:|---|---|
| 1 | Client-scoped lookup of `reference_run_id` is unavailable | `comparison_run_unavailable` |
| 2 | Client-scoped lookup of `compared_run_id` is unavailable | `comparison_run_unavailable` |
| 3 | Equal persisted `scenario_subject_id` | `comparison_same_subject` |
| 4 | Reference subject is not the unique server-owned `baseline`, or compared subject is not `adjusted` with at least one sealed accepted declared adjustment | `comparison_pair_role_invalid` |
| 5 | Either run has unsupported or unequal persisted `scenario_family` or `scenario_contract_version` | `comparison_scenario_contract_mismatch` |
| 6 | Persisted `start_month` or `end_month` differs | `comparison_horizon_mismatch` |
| 7 | Reference run/result `semantic_result_fingerprint` or `result_integrity_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 8 | Reference subject `calculation_semantic_fingerprint` or `integrity_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 9 | Reference `adjustment_manifest_fingerprint` or sealed-manifest parity is invalid | `comparison_fingerprint_invalid` |
| 10 | Reference `factual_inventory_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 11 | Reference `upstream_snapshot_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 12 | A present reference monthly row/value fingerprint or persisted result/range binding is invalid, excluding month membership/completeness owned by predecessor currentness | `comparison_fingerprint_invalid` |
| 13 | Compared run/result `semantic_result_fingerprint` or `result_integrity_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 14 | Compared subject `calculation_semantic_fingerprint` or `integrity_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 15 | Compared `adjustment_manifest_fingerprint` or sealed-manifest parity is invalid | `comparison_fingerprint_invalid` |
| 16 | Compared `factual_inventory_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 17 | Compared `upstream_snapshot_fingerprint` is invalid | `comparison_fingerprint_invalid` |
| 18 | A present compared monthly row/value fingerprint or persisted result/range binding is invalid, excluding month membership/completeness owned by predecessor currentness | `comparison_fingerprint_invalid` |
| 19 | Reference currentness under `m09-subject-currentness-v1` is false | `comparison_run_not_current` |
| 20 | Compared currentness under `m09-subject-currentness-v1` is false | `comparison_run_not_current` |
| 21 | Reference eligibility under `m09-to-m10-eligibility-v2` is false | `comparison_run_not_eligible` |
| 22 | Compared eligibility under `m09-to-m10-eligibility-v2` is false | `comparison_run_not_eligible` |
| 23 | Persisted `factual_baseline_material_fingerprint` values differ | `comparison_factual_baseline_material_mismatch` |
| 24 | Persisted `component_domain_contract_version` values differ or are unsupported | `comparison_component_domain_contract_mismatch` |
| 25 | Factual `ENGINE_VERSION` or persisted subject `upstream_snapshot.engine_version` differs or is unsupported | `comparison_engine_version_mismatch` |
| 26 | Factual `RESULT_SCHEMA_VERSION`, persisted `upstream_snapshot.result_schema_version`, persisted `upstream_snapshot.snapshot_schema_version`, or persisted `factual_inventory.inventory_schema_version` differs or is unsupported | `comparison_result_schema_version_mismatch` |
| 27 | The exact `factual_upstream_versions` projection in Section 9 differs, is malformed, or contains unsupported contract material | `comparison_factual_upstream_version_mismatch` |
| 28 | Persisted adjustment manifests are calculation-semantically identical | `comparison_semantically_identical_manifest` |
| 29 | Pair-level canonical month-sequence invariant guard: the two already-current authoritative canonical monthly sequences are unequal, or either canonical sequence differs from the accepted inclusive horizon representation despite having passed predecessor currentness | `comparison_month_alignment_mismatch` |
| 30 | An integrity-verified persisted monetary value cannot be represented or compared in the canonical Decimal domain | `comparison_numeric_domain_invalid` |

Rows 1-2 are a terminal resource-availability phase. They use client-owned
lookup only, in reference-then-compared order. Nonexistent, foreign-client, and
otherwise client-unreachable runs have the same public result. No global probe
may follow.

Rows 7-18 are the integrity phase. Reference is verified completely before
compared. Rows 19-22 execute only after both sides pass integrity; therefore a
corruption that also makes currentness false returns
`comparison_fingerprint_invalid`, not `comparison_run_not_current`.
Integrity validates material that is present and its accepted bindings; it does
not reclassify a predecessor-detected missing, extra, duplicate, or incomplete
month set as a fingerprint blocker. Present-row value or fingerprint tampering
remains an integrity failure.

Rows 23-27 are the shared factual/version phase. The snapshot and inventory
identifiers are persisted contract/schema identifiers and map deterministically
to `comparison_result_schema_version_mismatch`; this mapping does not claim
that either is an M09 result schema. Row 28 follows all integrity and version
checks. Month alignment follows semantic-manifest comparison. Numeric-domain
validation is last.

Rows 19-20 retain complete authority over per-run month membership. A missing,
extra, duplicate, or incomplete authoritative row set returns
`comparison_run_not_current`, reference before compared. Predicate 29 neither
duplicates nor overrides that result. It compares only the canonical
chronological sequences exposed by accepted PKG-014 after both runs have passed
currentness and eligibility. It is a defensive invariant guard, executed after
predicate 28 and before predicate 30. Under accepted predecessor semantics it is
not normally reachable through a valid persisted pair: predicate 6 requires
equal `start_month` and `end_month`; reference currentness requires the reference
canonical months to equal the inclusive authoritative
`_month_range(start_month, end_month)`; and compared currentness requires the
compared canonical months to equal that same range. Both canonical sequences
therefore are equal before predicate 29 is reached. A predicate 29 failure
indicates an internal invariant breach or unexpected representational
inconsistency, not an ordinary accepted business-state outcome. M10 must not
inspect physical database order or insertion order, create an alternate raw-read
path, override predecessor currentness, or remap per-run membership defects into
predicate 29.

The externally observable v2 examples are therefore:

- reference missing/extra/duplicate/incomplete membership: predicate 19,
  `comparison_run_not_current`;
- compared missing/extra/duplicate/incomplete membership: predicate 20,
  `comparison_run_not_current`;
- actual present-row value or fingerprint corruption:
  `comparison_fingerprint_invalid`;
- semantic-manifest identity: predicate 28,
  `comparison_semantically_identical_manifest`;
- predicate 29 retains `comparison_month_alignment_mismatch` as a defensive
  invariant blocker, not as an outcome expected from a valid accepted
  predecessor state; and
- numeric-domain failure after valid admission: predicate 30,
  `comparison_numeric_domain_invalid`.

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
| Factual upstream versions | Exact projection named `factual_upstream_versions` from persisted `M09SubjectRun.factual_inventory.domains[].candidates[]` and, for M06, persisted `candidates[].components[].provenance.handoff_contract_version` |

The `factual_upstream_versions` value is a closed array. M10 walks persisted
`factual_inventory.domains` in its stored array order and, within each domain,
walks persisted `candidates` in stored array order. It emits one record for each
candidate whose persisted `included` value is exactly `true`; it does not sort,
deduplicate, or reconstruct candidates. Each record is exactly:

```json
{
  "domain_identity": "<persisted string>",
  "candidate_identity": "<persisted string>",
  "source_identity": "<persisted string>",
  "source_version": "<persisted string>",
  "source_fingerprint": "<persisted lowercase sha256 hex>",
  "handoff_contract_versions": ["<persisted contract string>"]
}
```

For recurring-income and recurring-expense candidates,
`handoff_contract_versions` is exactly `[]`. For an included
`m06_monthly_pension` candidate, every persisted component must carry the same
`provenance.handoff_contract_version`, exactly
`m06-to-m09-monthly-amount-v1`, and the projection is the singleton array
`["m06-to-m09-monthly-amount-v1"]`. Candidate order is already the accepted
server-produced dependency order; M10 may only preserve it.

Duplicate `(domain_identity, candidate_identity)` projection keys, a missing
required member, a non-Boolean/missing `included`, an absent M06 handoff
contract, unequal M06 handoff contracts across components, or malformed source
fingerprint fails closed. No included candidates produces `[]`. M10 does not
calculate new upstream evidence. It may compare persisted literal
`source_version = "unversioned"` only when both runs otherwise pass integrity,
factual-baseline equality, and exact projection equality; it must not invent
`unversioned` as a fallback.

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

The accepted predecessor, not M10, owns per-run completeness and canonical row
ordering. Before predicate 29, each run must already have passed
`m09-subject-currentness-v1`, whose authoritative `ORDER BY month` representation
must equal the complete inclusive `_month_range(start_month, end_month)`.

Predicate 29 requires:

- identical `start_month`;
- identical `end_month`;
- identical authoritative canonical `monthly_results[].month` sequences; and
- equality of each canonical sequence to the accepted inclusive horizon
  representation after predecessor currentness has passed.

This is a defensive pair-level invariant guard. Under the accepted predecessor
contract, predicate 6 establishes an equal horizon and each successful
currentness decision establishes equality to the same inclusive authoritative
range, so a valid persisted pair necessarily passes predicate 29. Its failure
branch is retained to fail closed on an internal invariant breach or unexpected
representational inconsistency and is not an ordinary accepted business state.

Missing, extra, duplicate, or incomplete membership is a predecessor-currentness
failure and is not remapped to predicate 29. M10 must not inspect physical row
order, infer insertion order, independently sort an unordered result, add an
ordinal, reindex, insert zero rows, drop rows, or reinterpret currentness.
Physical reinsertion is not semantic evidence. No physical-row-reorder test is
required. Partial-range comparison is not supported.

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
  "reference_run_id": "<existing opaque M09 run-id string>",
  "compared_run_id": "<existing opaque M09 run-id string>"
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
the exact ordered table in Section 8.1 and returns its first applicable public
code. Internal diagnostics may retain multiple reasons but cannot change the
public result or leak foreign resource existence.

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

For `m10-comparison-result-v2`, the successful public semantic object is closed
and has exactly this shape:

```json
{
  "comparison_contract_version": "m10-scenario-comparison-v2",
  "pair_admission_contract": "m10-pair-admission-v2",
  "comparison_result_schema": "m10-comparison-result-v2",
  "comparison_fingerprint_schema": "m10-comparison-fingerprint-v2",
  "comparison_fingerprint": "<lowercase sha256 hex>",
  "delta_direction": "compared_minus_reference",
  "client_id": 123,
  "scenario_family": "declared_retirement_cashflow_adjustments",
  "scenario_contract_version": "v1",
  "horizon": {
    "start_month": "YYYY-MM",
    "end_month": "YYYY-MM"
  },
  "factual_baseline_material_fingerprint": "<persisted lowercase sha256 hex>",
  "component_domain_contract_version": "m09-component-domains-v1",
  "versions": {
    "factual_engine_version": "m09-aggregation-v1",
    "factual_result_schema_version": "m09-result-v1",
    "subject_engine_version": "m09-subject-aggregation-v1",
    "subject_result_schema_version": "m09-subject-result-v1",
    "upstream_snapshot_schema_version": "m09-subject-upstream-snapshot-v1",
    "factual_inventory_schema_version": "m09-resolved-component-inventory-v1",
    "factual_upstream_versions": []
  },
  "reference_run": {
    "run_id": "<existing opaque M09 run-id string>",
    "scenario_subject_id": "<existing opaque M09 subject-id string>",
    "subject_type": "baseline",
    "calculation_semantic_fingerprint": "<persisted lowercase sha256 hex>",
    "integrity_fingerprint": "<persisted lowercase sha256 hex>",
    "adjustment_manifest_fingerprint": "<persisted lowercase sha256 hex>",
    "factual_inventory_fingerprint": "<persisted lowercase sha256 hex>",
    "upstream_snapshot_fingerprint": "<persisted lowercase sha256 hex>",
    "semantic_result_fingerprint": "<persisted lowercase sha256 hex>",
    "result_integrity_fingerprint": "<persisted lowercase sha256 hex>"
  },
  "compared_run": {
    "run_id": "<existing opaque M09 run-id string>",
    "scenario_subject_id": "<existing opaque M09 subject-id string>",
    "subject_type": "adjusted",
    "calculation_semantic_fingerprint": "<persisted lowercase sha256 hex>",
    "integrity_fingerprint": "<persisted lowercase sha256 hex>",
    "adjustment_manifest_fingerprint": "<persisted lowercase sha256 hex>",
    "factual_inventory_fingerprint": "<persisted lowercase sha256 hex>",
    "upstream_snapshot_fingerprint": "<persisted lowercase sha256 hex>",
    "semantic_result_fingerprint": "<persisted lowercase sha256 hex>",
    "result_integrity_fingerprint": "<persisted lowercase sha256 hex>"
  },
  "monthly_comparisons": [],
  "range_totals": {
    "gross_inflow_total": {
      "reference_value": "0.00",
      "compared_value": "0.00",
      "delta": "0.00",
      "relation": "equal"
    },
    "gross_outflow_total": {
      "reference_value": "0.00",
      "compared_value": "0.00",
      "delta": "0.00",
      "relation": "equal"
    },
    "period_net": {
      "reference_value": "0.00",
      "compared_value": "0.00",
      "delta": "0.00",
      "relation": "equal"
    }
  }
}
```

The JSON integers are limited to `client_id`; accepted PKG-014 `run_id` and
`scenario_subject_id` are existing opaque string identities and therefore stay
JSON strings. This repository-bound type is authoritative and avoids inventing
integer aliases for accepted M09 resources.

The `versions` object has exactly the seven keys shown. Its
`factual_upstream_versions` array has exactly the element shape and persisted
ordering defined in Section 9. No additional version field is permitted.

Each element of `monthly_comparisons` is exactly:

```json
{
  "month": "YYYY-MM",
  "gross_inflow_total": {
    "reference_value": "0.00",
    "compared_value": "0.00",
    "delta": "0.00",
    "relation": "equal"
  },
  "gross_outflow_total": {
    "reference_value": "0.00",
    "compared_value": "0.00",
    "delta": "0.00",
    "relation": "equal"
  },
  "period_net": {
    "reference_value": "0.00",
    "compared_value": "0.00",
    "delta": "0.00",
    "relation": "equal"
  }
}
```

Every `relation` is exactly one value from the closed vocabulary in Section 12.
Array order equals persisted accepted month order. Comparison and fingerprinting
must not sort it. The `range_totals` object has exactly the three comparison
objects shown and reads the corresponding persisted M09 `range_totals` values
directly. No response object or nested semantic object permits extra keys.

Every successful semantic field is required and non-null. Missing or null
persisted material fails closed through the first applicable Section 8.1
blocker; semantic null placeholders and optional semantic fields are forbidden.

The semantic tree permits JSON objects, arrays, strings, and integers only where
the closed schema specifies them. Boolean values are permitted only for the
persisted `included` predicate used to select the Section 9 projection and are
not emitted in the successful response. JSON floating-point numbers, `null`,
NaN, and Infinity are prohibited. All monetary Decimals are strings.

Contract identifiers, hashes, enum values, `YYYY-MM` values, and Decimal strings
are ASCII only. No free-text, display text, or user-authored label enters the
response or its fingerprint material; Unicode normalization is therefore not a
semantic fingerprint operation.

## 22. Deterministic Comparison Fingerprint

The normative object `comparison_fingerprint_material` is exactly the successful
Section 21 response object with its `comparison_fingerprint` key omitted. It
contains every other success-response key and nothing else. This single rule is
the complete `m10-comparison-fingerprint-v2` input schema.

The accepted PKG-014 `result_integrity_fingerprint` in each run object already
binds that run's ordered monthly `result_fingerprint` values and persisted
`range_totals`; those lower-level fingerprints are not duplicated as extra M10
response or fingerprint-material fields.

Canonical bytes are produced exactly as follows:

1. Encode as UTF-8.
2. Sort JSON object keys lexicographically by Unicode code point; all semantic
   keys are ASCII, so this is deterministic ASCII lexical order.
3. Preserve every array's contract-defined order.
4. Emit no insignificant whitespace.
5. Use separators exactly `,` and `:`.
6. Apply standard JSON string escaping.
7. Reject NaN, Infinity, floating-point monetary values, and `null`.
8. Serialize monetary values as the canonical two-decimal strings in Section 13.
9. Serialize `client_id` as a JSON integer and accepted opaque M09 identities as
   JSON strings.
10. Reject every extra object key.

`comparison_fingerprint` is the lowercase hexadecimal SHA-256 digest of those
canonical UTF-8 bytes. Identical semantic material produces identical bytes and
fingerprint; changing any bound semantic field changes the fingerprint. The
role pair and all persisted arrays must never be sorted before hashing.

Actor, request timestamp, request ID, display labels, hidden diagnostics, and
implementation-only fields are absent from both the public v1 response and
`comparison_fingerprint_material`; they cannot affect semantic identity.

For `m10-comparison-result-v2` and `m10-comparison-fingerprint-v2`, adding,
removing, retyping, optionally populating, or implementation-specifically
enriching any semantic field is forbidden. Any semantic schema change requires
a separately accepted new schema/contract version.

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

### 28.1 Corrected Future Runtime Evidence

After independent v2 acceptance and separate implementation authorization,
runtime evidence must prove without bypassing accepted predecessor authorities:

- reference missing/extra/duplicate/incomplete membership returns predicate 19
  `comparison_run_not_current`;
- compared missing/extra/duplicate/incomplete membership returns predicate 20
  `comparison_run_not_current`;
- predecessor-detected invalid membership is not remapped to
  `comparison_fingerprint_invalid`;
- predecessor currentness and eligibility remain authoritative;
- a valid reference and valid compared current pair passes predicate 29 through
  integration evidence;
- actual present-row integrity corruption returns
  `comparison_fingerprint_invalid` through integration evidence;
- manifest semantic identity remains predicate 28 and precedes predicate 29;
- numeric-domain validation remains predicate 30 and follows predicate 29;
- the predicate 29 unequal-array branch is tested only by a pure helper test or
  isolated structural guard test that supplies canonical month arrays directly
  and returns `comparison_month_alignment_mismatch`;
- that isolated failure test does not represent a valid persisted PKG-014 pair
  and must not monkeypatch predecessor currentness or eligibility to manufacture
  a purportedly valid persisted mismatch;
- no raw database-order, reinsertion-order, or impossible persisted-order test
  is required;
- D-015-I002 rejects Decimal authority requiring rounding, implicit
  quantization, invalid scale, exponent representation, non-finite values,
  floats, and out-of-domain values before formatting, while preserving both
  exact input and full delta boundaries; and
- D-015-I003 validates every included M06 component and every component's
  object-shaped provenance and exact handoff version without skipping malformed
  entries.

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
16. `PKG_015_NONDETERMINISTIC_BLOCKER_MAPPING_REQUIRED`
17. `PKG_015_FINGERPRINT_OR_RESPONSE_SCHEMA_NOT_EXACT`

Stop conditions are definition boundaries, not implementation authorization.
`PKG_015_PREDECESSOR_SEMANTIC_REWRITE_REQUIRED` is a successful fail-closed
boundary: implementation must stop if it would require an M09 ordinal, migration,
new ordering authority, currentness/eligibility rewrite, or unordered raw read.

### 29.1 Defect State Entering V2 Acceptance

- `D-015-I001`:
  `BLOCKED_BY_ACCEPTED_V1_CONTRACT_INCOMPATIBILITY`;
  `RESOLUTION_REQUIRES_ACCEPTED_V2_CONTRACT`. It remains open until this v2
  definition is independently accepted and implementation is updated and
  re-audited. Physical-row reorder detection is not a v2 implementation duty.
- `D-015-I002`: `OPEN`; exact Decimal authority must be validated before any
  formatting, quantization, or canonical serialization.
- `D-015-I003`: `OPEN`; every M06 component must have complete object-shaped
  provenance and the exact accepted handoff version before projection.

No implementation correction is authorized by these states.

## 30. Acceptance Criteria

- **AC-015-001:** V2 definition work starts on `pkg-015-v2-definition-correction` from exact master `8a0bd85a98d78f39d19eee937989b7ddd0192844` with only the new definition artifact and narrow Build Plan synchronization.
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
- **AC-015-016:** PKG-014 currentness remains authoritative: missing, extra, duplicate, or incomplete per-run canonical month membership returns `comparison_run_not_current`, reference before compared.
- **AC-015-017:** Predicate 29 is a defensive pair-level canonical month-sequence invariant guard under accepted predecessor semantics: it compares only two already-current canonical chronological sequences for exact pair equality and accepted inclusive-horizon equality, and no ordinal, physical-order inspection, zero-fill, sorting, or reindexing path exists.
- **AC-015-018:** Only persisted monthly `gross_inflow_total`, `gross_outflow_total`, and `period_net` are compared directly.
- **AC-015-019:** Only persisted `range_totals` fields with those exact three names are compared directly.
- **AC-015-020:** No monthly, range, component, or net value is reconstructed or normalized.
- **AC-015-021:** Delta direction is exactly `compared_minus_reference` for every value.
- **AC-015-022:** Relations use only `equal`, `compared_greater_than_reference`, and `compared_lower_than_reference` as numeric facts.
- **AC-015-023:** Decimal subtraction is exact, float-free, and supports the full difference domain without `Numeric(20,2)` overflow.
- **AC-015-024:** Reference, compared, and delta outputs use the frozen canonical two-decimal string format without scientific notation or rounding.
- **AC-015-025:** A successful `m10-comparison-result-v2` response has exactly the closed top-level and nested semantic schema in Section 21, with no extra or optional semantic field.
- **AC-015-026:** `comparison_fingerprint_material` is exactly the successful response with only `comparison_fingerprint` omitted, and implementation-specific enrichment is rejected.
- **AC-015-027:** Actor, request time, request ID, display labels, hidden diagnostics, and implementation metadata are absent from the response and fingerprint input and cannot affect comparison semantic identity.
- **AC-015-028:** PKG-015 is stateless and each request re-evaluates admission; responses are point-in-time evidence only.
- **AC-015-029:** No comparison model, table, migration, history, currentness, lifecycle, or downstream eligibility is introduced.
- **AC-015-030:** Exactly one endpoint exists: `POST /api/clients/{client_id}/m10/compare`.
- **AC-015-031:** The strict request body contains only `reference_run_id` and `compared_run_id`, with `extra = forbid`.
- **AC-015-032:** There is no separate validation/admission endpoint or split-brain validation state.
- **AC-015-033:** Every blocker returns no partial comparison payload or comparison fingerprint.
- **AC-015-034:** The Section 8.1 v2 predicate table is authoritative: predicates representing valid predecessor states require integration evidence; predicate 29 requires integration proof that valid current pairs pass plus isolated structural/helper guard evidence for its unequal-array failure branch; integrity precedes currentness, reference precedes compared, predecessor month-set failures remain predicates 19/20, semantic identity remains 28, and numeric domain remains 30.
- **AC-015-035:** No frontend route, component, UI state, or client-side comparison is included.
- **AC-015-036:** No recommendation, ranking, optimization, suitability, significance, materiality, forecast, or probability semantics are included.
- **AC-015-037:** Accepted PKG-013 and PKG-014 families, chronological read authority, currentness, eligibility, persistence, formulas, fingerprints, and history remain unchanged; no predecessor schema or semantic rewrite is required.
- **AC-015-038:** M11-M14 remain unauthorized, M08E remains excluded, and `02M` remains frozen.
- **AC-015-039:** Verification proves exactly the new v2 definition artifact and narrow Business Build Plan synchronization changed, while the v1 definition, v1 acceptance record, code, tests, migrations, frontend, and protected paths remain untouched.
- **AC-015-040:** The only next gate is independent v2 definition acceptance audit; the frozen implementation candidate is not accepted, implementation correction remains paused, and the next package remains `NOT_AUTHORIZED`.
- **AC-015-041:** Every successful semantic field is required and non-null; missing/null persisted material fails closed without a null placeholder.
- **AC-015-042:** All reference, compared, and delta monetary values are JSON strings in the one canonical two-decimal format, including normalization of negative zero to `0.00`.
- **AC-015-043:** `monthly_comparisons` preserves the exact accepted PKG-014 canonical chronological representation, has the exact element schema, and never treats physical database order as semantic evidence.
- **AC-015-044:** `versions` has exactly the seven defined keys, and `factual_upstream_versions` is the exact closed projection of accepted persisted PKG-014 dependency material in stored domain/candidate order.
- **AC-015-045:** Canonical JSON uses exact UTF-8, key ordering, array ordering, escaping, whitespace, separator, primitive, and no-null rules and produces byte-identical material for identical semantics.
- **AC-015-046:** The comparison fingerprint is deterministic lowercase SHA-256: identical semantic material produces the same fingerprint and a change to any bound semantic field produces a different fingerprint.
- **AC-015-047:** No public v2 response or fingerprint-material object accepts an extra key, retyped key, alternate payload, optional semantic value, or implementation-specific field; v1 is not silently reinterpreted.
- **AC-015-048:** The 16 public blockers remain closed: every reachable accepted state has deterministic exact public mapping, defensive predicate 29 has deterministic structural guard mapping to `comparison_month_alignment_mismatch`, and exact precedence prevents alternate public-code selection.

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
- **NAC-015-010:** Admission of a run whose authoritative canonical month membership is missing, extra, duplicate, or incomplete; or admission of an unequal canonical pair sequence after predecessor currentness passes.
- **NAC-015-011:** Fill-with-zero, physical-row-order inspection, insertion-order inference, independent sorting, reindexing, interpolation, proration, annualization, or normalization.
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
- **NAC-015-027:** Retrofit or rewrite of PKG-013/PKG-014 runs, schema, ordering semantics, currentness, eligibility, fingerprints, or persistence, including any new ordinal.
- **NAC-015-028:** M11/M12 downstream eligibility, report authority, or execution.
- **NAC-015-029:** M13/M14 work, M08E work, or change to `02M`.
- **NAC-015-030:** Production-readiness or V1/V2 parity claim.
- **NAC-015-031:** Implementation code, test, migration, persistence, frontend, v1-history rewrite, or acceptance record during v2 definition drafting.
- **NAC-015-032:** Acceptance of the frozen v1 implementation, authorization of v2 implementation correction, or authorization of any next package by this definition.
- **NAC-015-033:** Selecting an alternate public code when predicate 29 is invoked, treating its defensive status as permission to omit or remap the guard, or manufacturing a predecessor-invalid state and presenting it as valid persisted integration evidence.
- **NAC-015-034:** Alternate or expanded fingerprint payload, optional semantic fingerprint member, or hidden implementation-defined fingerprint enrichment.
- **NAC-015-035:** Any extra success-response field under `m10-comparison-result-v2` without a separately accepted schema version.
- **NAC-015-036:** A null or optional semantic field in a successful response or fingerprint material.
- **NAC-015-037:** JSON floating-point encoding of a monetary value, NaN, Infinity, or a JSON numeric Decimal.
- **NAC-015-038:** Non-canonical Decimal text, including leading plus, unnecessary leading zero, scientific notation, excess/missing fractional digits, or negative zero.
- **NAC-015-039:** Inspecting or fingerprinting physical database row order, inventing a month-order authority, altering the accepted canonical monthly representation, or sorting/reordering the factual-upstream projection.
- **NAC-015-040:** Alternate canonicalization, separator, encoding, key-order, array-order, whitespace, escaping, or hash rule.
- **NAC-015-041:** Emitting corrected admission semantics under v1 identifiers, or adding, removing, retyping, or optionally populating v2 semantic material without another separately accepted contract/schema version.

## 32. Verification Matrix

| Area | Required future evidence |
|---|---|
| Base/scope | Exact branch/base; docs-only definition diff; protected paths untouched |
| Contract/roles | Exact family/version and baseline-reference/adjusted-compared enforcement |
| Admission | Exact ordered predicate/code precedence; same-client, distinct subjects, integrity-before-currentness, predecessor-authoritative predicates 19/20, eligibility v2, horizon, factual and version equality |
| Non-leakage | Foreign and nonexistent run/service paths return equivalent public behavior |
| Persisted values | Direct monthly/range field reads; no component/month reconstruction |
| Alignment | Integration: reference invalid membership maps through predicate 19, compared invalid membership through predicate 20, and a valid current pair passes predicate 29. Structural/helper: directly supplied unequal canonical arrays map exactly to `comparison_month_alignment_mismatch`, without claiming a valid persisted predecessor pair. No raw-row-order, reinsertion-order, or predecessor-monkeypatch test |
| Arithmetic | Decimal-only subtraction, full delta domain, canonical string output, numeric relation |
| Response/fingerprint | Closed no-null/no-extra response; response-minus-fingerprint material; exact persisted upstream projection; canonical bytes and deterministic SHA-256 replay |
| Statelessness | No model/table/migration/history/currentness/lifecycle |
| API | One strict atomic compare endpoint and no validation route |
| Authority audit | No recommendation, ranking, materiality, optimization, report, or M11+ semantics |
| Regression | PKG-013 and PKG-014 behavior and artifacts unchanged |

## 33. Authorization Boundary

- PKG-015 definition acceptance: `NOT_YET_DECIDED`.
- PKG-015 implementation: `NOT_AUTHORIZED`.
- Frozen v1 implementation candidate: `NOT_ACCEPTED`; `BLOCKED_PENDING_CONTRACT_CORRECTION`.
- Implementation work: `PAUSED` pending independent v2 definition acceptance.
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

PKG_015_V2_DEFINITION_PROPOSED_FOR_ACCEPTANCE
