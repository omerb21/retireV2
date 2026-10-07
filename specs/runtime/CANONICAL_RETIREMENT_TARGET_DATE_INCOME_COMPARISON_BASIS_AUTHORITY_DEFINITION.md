# CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_AUTHORITY

## 1. Definition status and governance

- Package ID: `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_AUTHORITY` (`RTICB`).
- Package class: `CLASS A / COMPLEX CLASS A`.
- Artifact status: `DEFINITION_DRAFT`.
- Governing protocol: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Binding owner decision: `OWNER-DECISION-RTICB-001`.
- Implementation: `NOT_AUTHORIZED`.
- Downstream implementation: `NOT_AUTHORIZED`.
- Production readiness: `NOT_CLAIMED`.

This Definition does not constitute Definition acceptance or implementation
authorization. After Definition acceptance and before any implementation
authorization, the protocol-required `PRE-IMPLEMENTATION CONTRACT ENUMERATION`
must be completed and accepted.

## 2. Objective and authority boundary

RTICB is a comparability authority only. It determines, deterministically and
per admitted target-date income source, whether the source's already-authoritative
native basis permits direct comparison with the confirmed retirement monthly
income target.

RTICB creates authority over:

1. the exact input identity used for a comparison assessment;
2. complete coverage of the current RTISA source universe;
3. in every successful result, one deterministic comparison classification per
   entry of the accepted ready RTISA source universe;
4. ordered reasons supporting every non-direct classification;
5. whether classification completed successfully; and
6. whether the complete admitted source set is ready for a future *direct*
   income-total/gap comparison without normalization.

RTICB does not create authority over normalized amounts, tax treatment,
inflation, totals, gaps, coverage, eligibility, withdrawals, allocation,
optimization, or scenarios. It does not change any upstream authority.

## 3. Binding owner decision

`OWNER-DECISION-RTICB-001` is applied as follows:

- Direct income-basis compatibility is exact equality: `GROSS` with `GROSS`,
  or `NET` with `NET`.
- Direct price-basis compatibility is exact equality:
  `NOMINAL_AT_RETIREMENT_TARGET_DATE` with the same basis, or
  `REAL_AT_REFERENCE_DATE` with the same basis.
- When both price bases are `REAL_AT_REFERENCE_DATE`, both authoritative
  reference dates must be present and exactly equal.
- `UNKNOWN`, missing, malformed, or unsupported basis evidence is not directly
  comparable.
- A mismatch is classified; it is never silently normalized.
- RTICB may say that normalization is required, but it never calculates or
  supplies a normalized value.

## 4. Upstream authorities consumed

RTICB consumes exactly two current result authorities:

1. `CANONICAL_RETIREMENT_MONTHLY_INCOME_TARGET_AUTHORITY`, including its
   `target_result_fingerprint`, `target_semantic_fingerprint`, current/confirmed
   authority state, and the authoritative target fields `income_basis`,
   `price_basis`, and `price_reference_date`.
2. `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_ADMISSION_AUTHORITY`
   (`RTISA`), including its `admission_result_fingerprint`, readiness and
   universe evidence, complete ordered source entries, admission states,
   upstream identities, native income basis, and native price evidence.

Those authorities already bind, transitively, the canonical planning input,
retirement target date, pension execution/portfolio, pension monthly amount
basis, pension temporal/indexation basis, and target-date resource-state
contracts. RTICB validates the supplied upstream identities; it does not
reconstruct those authorities or independently discover income sources.

## 5. Required upstream admissibility

A ready comparison result requires all of the following:

- both results belong to the requested positive integer `client_id`;
- both bind the same valid `planning_calculation_input_fingerprint`;
- both bind the same valid ISO `retirement_target_date`;
- the target result fingerprint and semantic fingerprint are valid and
  recompute exactly;
- the target is `CURRENT`, confirmed, and `target_ready = true`;
- the target currency is `ILS`;
- the target basis tuple is structurally valid under its accepted authority;
- the RTISA result fingerprint is valid and recomputes exactly;
- RTISA reports `COMPLETE_EVIDENCED`, `READY`, and `admission_ready = true`;
- RTISA source entries and included/excluded/unresolved ID partitions are
  complete, unique, sorted, disjoint, and exactly cover the entries;
- the ready RTISA result has an empty `unresolved_source_ids` partition and no
  entry whose `admission_state` is `UNRESOLVED`; and
- every preserved upstream source and pension-result identity satisfies the
  exact structural and relationship checks permitted by the fingerprint
  verification inventory in Section 12.6.

If one of these conditions fails, RTICB fails closed. It must not repair,
reinterpret, partially consume, or mix the two authorities.

## 6. Source universe and coverage

The RTICB source universe is exactly the complete `source_entries` sequence in
the current RTISA result. No source is added, removed, deduplicated, joined, or
rediscovered by RTICB.

For every entry of the accepted ready RTISA result, RTICB emits exactly one
comparison entry with the same `source_id`. Source entries are ordered by
ascending Unicode code-point order of
`source_id`, matching the canonical RTISA ordering. A source ID must be a
non-empty string equal to its own whitespace trim and contain no control
character. Duplicate, missing, unexpected, whitespace-padded, non-string, or
out-of-order source IDs invalidate the whole result.

Only entries whose RTISA `admission_state` is `INCLUDED` are economically
admitted comparison candidates. `EXCLUDED` entries remain in the result as
explicit coverage evidence and cannot contribute to a future direct total.
An RTISA `UNRESOLVED` entry makes RTISA `PARTIAL`, `NOT_READY`, and
`admission_ready = false` under the accepted upstream contract, so it is
rejected at the `rtisa_authority` stage and cannot appear in a successful RTICB
result. RTICB never bypasses or upgrades RTISA admission state.

## 7. Authoritative basis projection

Each comparison entry preserves, without inference:

- target `income_basis`, `price_basis`, and `price_reference_date`;
- source `native_income_basis`;
- source `native_price_evidence.price_basis`;
- source `native_price_evidence.price_reference_date`;
- RTISA `admission_state` and `reason_codes`;
- RTISA upstream source identity; and
- the relevant target and RTISA fingerprints.

Tax characterization, source category, description, origin, pension type,
employment intent, or other professional knowledge must never be used to fill
or infer a missing basis field. They may remain provenance only.

## 8. Per-source classification taxonomy

The smallest binding state taxonomy is:

| State | Meaning |
|---|---|
| `DIRECTLY_COMPARABLE` | The source is admitted and every required basis dimension exactly matches the target. |
| `NORMALIZATION_REQUIRED` | The source is admitted, its relevant basis evidence is authoritative and known, but one or more dimensions differ from the target. |
| `BASIS_UNRESOLVED` | The source is admitted but required native basis evidence is authoritatively represented by RTISA as `UNKNOWN`, or an otherwise-valid real-price evidence object has a null reference date. |
| `NOT_ADMITTED` | RTISA explicitly excluded the source; RTICB performs no basis comparison for it. |

Reason codes are a sorted unique list. Their closed vocabulary is:

- `RTICB_SOURCE_NOT_ADMITTED`
- `RTICB_INCOME_BASIS_UNKNOWN`
- `RTICB_INCOME_BASIS_MISMATCH`
- `RTICB_PRICE_BASIS_UNKNOWN`
- `RTICB_PRICE_BASIS_MISMATCH`
- `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING`
- `RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH`

The state/reason mapping is exact:

- `DIRECTLY_COMPARABLE` has no reasons.
- `NORMALIZATION_REQUIRED` has one or more mismatch reasons and no unknown or
  not-admitted reason.
- `BASIS_UNRESOLVED` has one or more unknown/missing reasons. If both unresolved
  and mismatch conditions exist, `BASIS_UNRESOLVED` controls while every
  independently determinable mismatch reason is still preserved.
- `NOT_ADMITTED` has exactly `RTICB_SOURCE_NOT_ADMITTED`. No basis mismatch or
  unknown reason is emitted for an RTISA-excluded source. An RTISA
  `UNRESOLVED` entry cannot reach per-source classification because it fails
  the ready-authority gate in Section 5.

## 9. Classification algorithm

For each RTISA entry, in canonical source order:

1. If `admission_state = EXCLUDED`, emit `NOT_ADMITTED` according to Section 8
   and stop classification for that entry. `UNRESOLVED` is not a successful
   per-entry case: its presence deterministically selects
   `RTICB_RTISA_AUTHORITY_NOT_READY` before source classification. Any other
   admission-state value is a schema defect.
2. Validate source native income basis. The valid closed vocabulary is
   `GROSS`, `NET`, and `UNKNOWN`. The literal `UNKNOWN` produces
   `RTICB_INCOME_BASIS_UNKNOWN`; a value outside that vocabulary is malformed
   canonical authority data and routes to `block_no_result`. Otherwise,
   inequality with the target produces `RTICB_INCOME_BASIS_MISMATCH`.
3. Validate source native price basis. The valid closed vocabulary is
   `NOMINAL_AT_RETIREMENT_TARGET_DATE`, `REAL_AT_REFERENCE_DATE`, and `UNKNOWN`.
   The literal `UNKNOWN` with a null reference date produces
   `RTICB_PRICE_BASIS_UNKNOWN`; any other unsupported value or an `UNKNOWN`
   object with a non-null reference date is malformed canonical authority data
   and routes to `block_no_result`.
4. Validate source-local REAL reference-date evidence independently of the
   target price basis. Whenever source price basis is
   `REAL_AT_REFERENCE_DATE`, a null source date is valid incomplete evidence
   and produces `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING`; a non-null source
   date must be canonical ISO or the RTISA authority is malformed and the whole
   operation routes to `block_no_result`. This validation is unconditional even
   when target and source price bases differ.
5. If the source price basis is known and differs from the target price basis,
   emit `RTICB_PRICE_BASIS_MISMATCH`. This known mismatch is preserved even
   when Step 4 also produced unresolved source evidence.
6. Only when both price bases are `REAL_AT_REFERENCE_DATE` and both dates are
   valid, compare the dates for equality. The confirmed target authority already
   guarantees its REAL target date is present and canonical. Unequal dates
   produce `RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH`.
7. A `NOMINAL_AT_RETIREMENT_TARGET_DATE` source must have a null reference date
   under the upstream contract. A non-null value is invalid upstream authority,
   not a normalization case. The confirmed target authority independently owns
   and guarantees the corresponding target-side nullability rule.
8. Resolve the state from the complete reason set using Section 8. Any unknown
   or missing reason selects `BASIS_UNRESOLVED`; otherwise any mismatch reason
   selects `NORMALIZATION_REQUIRED`; otherwise select `DIRECTLY_COMPARABLE`.

Comparison never reads or changes amount fields. An admitted source with zero
amount is still classified because comparability is a basis property, not an
amount-materiality shortcut.

### 9.1 Binding admission and income-basis matrix

Admission is resolved before basis comparison:

| RTISA admission state | RTICB route |
|---|---|
| `INCLUDED` | continue with income and price classification |
| `EXCLUDED` | `NOT_ADMITTED` with exactly `[RTICB_SOURCE_NOT_ADMITTED]` |
| `UNRESOLVED` | no successful result; `RTICB_RTISA_AUTHORITY_NOT_READY` |
| any other/malformed value | no successful result; `RTICB_SOURCE_UNIVERSE_INVALID` |

For an `INCLUDED` source, after target and source structures are valid:

| Target income basis | Source income basis | Income contribution |
|---|---|---|
| `GROSS` | `GROSS` | no reason |
| `NET` | `NET` | no reason |
| `GROSS` | `NET` | `RTICB_INCOME_BASIS_MISMATCH` |
| `NET` | `GROSS` | `RTICB_INCOME_BASIS_MISMATCH` |
| either accepted target basis | `UNKNOWN` | `RTICB_INCOME_BASIS_UNKNOWN` |
| either accepted target basis | unsupported value, wrong type, missing key, or null | no successful result; `RTICB_SOURCE_BASIS_EVIDENCE_INVALID` |

### 9.2 Binding price-basis matrix

The following rows assume an `INCLUDED` source, matching resolved income bases,
and otherwise-valid identities/structures. Reasons are shown in canonical
Unicode code-point order.

| Target price basis/date | Source price basis/date | Classification | Exact reasons |
|---|---|---|---|
| `NOMINAL_AT_RETIREMENT_TARGET_DATE` / null | `NOMINAL_AT_RETIREMENT_TARGET_DATE` / null | `DIRECTLY_COMPARABLE` | `[]` |
| `NOMINAL_AT_RETIREMENT_TARGET_DATE` / null | `REAL_AT_REFERENCE_DATE` / null | `BASIS_UNRESOLVED` | `[RTICB_PRICE_BASIS_MISMATCH, RTICB_REAL_PRICE_REFERENCE_DATE_MISSING]` |
| `NOMINAL_AT_RETIREMENT_TARGET_DATE` / null | `REAL_AT_REFERENCE_DATE` / valid date | `NORMALIZATION_REQUIRED` | `[RTICB_PRICE_BASIS_MISMATCH]` |
| `NOMINAL_AT_RETIREMENT_TARGET_DATE` / null | `UNKNOWN` / null | `BASIS_UNRESOLVED` | `[RTICB_PRICE_BASIS_UNKNOWN]` |
| `REAL_AT_REFERENCE_DATE` / valid date | `UNKNOWN` / null | `BASIS_UNRESOLVED` | `[RTICB_PRICE_BASIS_UNKNOWN]` |
| `REAL_AT_REFERENCE_DATE` / valid date | `REAL_AT_REFERENCE_DATE` / null | `BASIS_UNRESOLVED` | `[RTICB_REAL_PRICE_REFERENCE_DATE_MISSING]` |
| `REAL_AT_REFERENCE_DATE` / date D | `REAL_AT_REFERENCE_DATE` / same date D | `DIRECTLY_COMPARABLE` | `[]` |
| `REAL_AT_REFERENCE_DATE` / date D1 | `REAL_AT_REFERENCE_DATE` / different valid date D2 | `NORMALIZATION_REQUIRED` | `[RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH]` |
| `REAL_AT_REFERENCE_DATE` / valid date | `NOMINAL_AT_RETIREMENT_TARGET_DATE` / null | `NORMALIZATION_REQUIRED` | `[RTICB_PRICE_BASIS_MISMATCH]` |

A malformed non-null REAL source date is not a classification row: it is
malformed canonical authority data and routes to
`RTICB_SOURCE_BASIS_EVIDENCE_INVALID` under Section 13. A malformed target REAL
date is rejected earlier by the accepted target-authority validation contract.
An `UNKNOWN` source with a non-null date and a nominal source with a non-null
date follow the same fatal basis-evidence route. Independent income reasons are
combined with the price reason set; the state precedence in Section 8 then
selects one result without discarding any independently determinable reason.

## 10. Downstream readiness model

RTICB separates two booleans and their states:

### 10.1 Classification completion

`classification_state = COMPLETE` and `classification_complete = true` only
when both upstream authorities are valid/current, the RTISA universe is
complete, and every RTISA source has exactly one valid RTICB entry.

A complete result may contain `NORMALIZATION_REQUIRED`, `BASIS_UNRESOLVED`, or
`NOT_ADMITTED` entries. Completion means the comparison question was answered;
it does not mean a direct total is safe.

### 10.2 Direct-comparison readiness

`direct_comparison_state = READY` and `direct_comparison_ready = true` only
when classification is complete and every RTISA `INCLUDED` source is
`DIRECTLY_COMPARABLE`.

An empty admitted source set is direct-comparison ready only when RTISA itself
is complete and ready. This readiness says that a future complete direct total
would omit no admitted source; it does not calculate or authorize that total.

Otherwise the state is `NOT_READY`, and aggregate blockers are the sorted unique
union of:

- `RTICB_NORMALIZATION_REQUIRED` when any admitted source has that state;
- `RTICB_BASIS_UNRESOLVED` when any admitted source has that state.

An RTISA-unresolved source does not add an aggregate blocker because it cannot
appear in a successful RTICB result; it selects the earlier
`RTICB_RTISA_AUTHORITY_NOT_READY` failure envelope.

Future total/gap logic must not omit an admitted source with
`NORMALIZATION_REQUIRED` or `BASIS_UNRESOLVED`. It must stop until a separately
authorized authority resolves the basis or performs the required normalization.

## 11. Request and result contracts

### 11.1 Request contract

The public RTICB request is an object with exactly these keys:

- `client_id`: positive integer; booleans are not integers for this contract;
- `expected_planning_calculation_input_fingerprint`: lowercase 64-character
  hexadecimal SHA-256 string; and
- `expected_retirement_target_date`: canonical ISO date string `YYYY-MM-DD`.

Extra or missing keys are invalid. The expected planning fingerprint and date
are caller-supplied snapshot admission guards. They are not reconstructed from
the target or RTISA result.

The result schema constant name is `SCHEMA_VERSION` and its exact value is
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V1`.

### 11.2 Successful result

A successful result contains exactly:

- `schema_version`
- `client_id`
- `planning_calculation_input_fingerprint`
- `retirement_target_date`
- `target_result_fingerprint`
- `target_semantic_fingerprint`
- `rtisa_admission_result_fingerprint`
- `comparison_input_fingerprint`
- `target_basis`
- `source_comparisons`
- `directly_comparable_source_ids`
- `normalization_required_source_ids`
- `basis_unresolved_source_ids`
- `not_admitted_source_ids`
- `classification_state`
- `classification_complete`
- `direct_comparison_state`
- `direct_comparison_ready`
- `blockers`
- `comparison_result_fingerprint`

Every listed key is required and non-null except the explicitly nullable
`target_basis.price_reference_date` and source
`source_price_reference_date`/nested upstream identity values. No additional
key is permitted.

`target_basis` contains exactly `income_basis`, `price_basis`, and
`price_reference_date`. Each source comparison contains exactly:

- `source_id`
- `rtisa_admission_state`
- `source_upstream_identity`
- `source_income_basis`
- `source_price_basis`
- `source_price_reference_date`
- `comparison_state`
- `reason_codes`
- `source_comparison_fingerprint`

No normalized or calculated amount is present.

## 12. Determinism and exact fingerprint contracts

All fingerprints are lowercase SHA-256 over UTF-8 canonical JSON with sorted
object keys, compact separators, `ensure_ascii = false`, and non-finite values
rejected. Arrays remain in their contractually defined canonical order.

Null is serialized as JSON `null`; no nullable key is omitted. Reason and
blocker arrays are sorted ascending by Unicode code point, contain unique
strings, and are serialized even when empty. `source_comparisons` and every
source-ID partition are sorted ascending by `source_id`. Object-key sorting by
the canonical serializer does not replace these array-order rules.

The four and only four RTICB fingerprint contracts are below.

### 12.1 Input fingerprint

Constant name:
`INPUT_FINGERPRINT_CONTRACT`.

Exact constant value:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_INPUT_JSON_V1`.

`comparison_input_fingerprint` is SHA-256 of exactly this preimage (no wrapper
or additional key):

```json
{
  "contract": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_INPUT_JSON_V1",
  "client_id": 1,
  "planning_calculation_input_fingerprint": "<sha256>",
  "retirement_target_date": "YYYY-MM-DD",
  "target_result_fingerprint": "<sha256>",
  "target_semantic_fingerprint": "<sha256>",
  "rtisa_admission_result_fingerprint": "<sha256>"
}
```

All six identity values are required and non-null. The planning/date values are
the common, validated observed values and must also equal their request guards.

### 12.2 Per-entry fingerprint

Constant name:
`ENTRY_FINGERPRINT_CONTRACT`.

Exact constant value:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V1`.

`source_comparison_fingerprint` is SHA-256 of exactly:

```json
{
  "contract": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V1",
  "comparison_input_fingerprint": "<sha256>",
  "source_comparison": {
    "source_id": "<non-empty string>",
    "rtisa_admission_state": "INCLUDED|EXCLUDED",
    "source_upstream_identity": {
      "source_fingerprint": "<sha256>",
      "pension_source_result_fingerprint": null,
      "resolution": null
    },
    "source_income_basis": "GROSS|NET|UNKNOWN",
    "source_price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE|REAL_AT_REFERENCE_DATE|UNKNOWN",
    "source_price_reference_date": null,
    "comparison_state": "DIRECTLY_COMPARABLE|NORMALIZATION_REQUIRED|BASIS_UNRESOLVED|NOT_ADMITTED",
    "reason_codes": []
  }
}
```

The nested `source_comparison` contains every successful entry field except
`source_comparison_fingerprint`, with exactly the key set shown. The displayed
nulls are nullable positions, not fixed values:

- `pension_source_result_fingerprint` is null or a valid SHA-256;
- `source_price_reference_date` is null or a canonical ISO date; and
- `resolution` is null or exactly
  `{decision_kind, record_version, income_fingerprint, canonical_source_id,
  canonical_fingerprint}` in canonical JSON key order. `record_version` is a
  positive integer; `income_fingerprint` is a SHA-256; the two canonical fields
  are either both null or respectively a non-empty string and SHA-256.

No other RTISA fields, amount, actor, or RTICB execution metadata enter the
entry preimage. Distinct source identities therefore remain distinct even when
their basis classifications are equal.

### 12.3 Successful-result fingerprint

Constant name:
`RESULT_FINGERPRINT_CONTRACT`.

Exact constant value:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V1`.

`comparison_result_fingerprint` is SHA-256 of exactly:

```json
{
  "contract": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V1",
  "result": {
    "schema_version": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V1",
    "client_id": 1,
    "planning_calculation_input_fingerprint": "<sha256>",
    "retirement_target_date": "YYYY-MM-DD",
    "target_result_fingerprint": "<sha256>",
    "target_semantic_fingerprint": "<sha256>",
    "rtisa_admission_result_fingerprint": "<sha256>",
    "comparison_input_fingerprint": "<sha256>",
    "target_basis": {
      "income_basis": "GROSS|NET",
      "price_basis": "NOMINAL_AT_RETIREMENT_TARGET_DATE|REAL_AT_REFERENCE_DATE",
      "price_reference_date": null
    },
    "source_comparisons": [],
    "directly_comparable_source_ids": [],
    "normalization_required_source_ids": [],
    "basis_unresolved_source_ids": [],
    "not_admitted_source_ids": [],
    "classification_state": "COMPLETE",
    "classification_complete": true,
    "direct_comparison_state": "READY|NOT_READY",
    "direct_comparison_ready": true,
    "blockers": []
  }
}
```

The nested result is the exact Section 11 successful result excluding only
`comparison_result_fingerprint`. Placeholder null/empty/boolean values take
their actual validated values. `target_basis.price_reference_date` is null for
nominal basis and a canonical ISO date for real basis.

### 12.4 Failure fingerprint

Constant name:
`FAILURE_FINGERPRINT_CONTRACT`.

Exact constant value:
`CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_FAILURE_JSON_V1`.

`result_fingerprint` on `block_no_result` is SHA-256 of exactly:

```json
{
  "contract": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_FAILURE_JSON_V1",
  "failure": {
    "schema_version": "CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V1",
    "client_id": null,
    "supplied_planning_calculation_input_fingerprint": null,
    "observed_target_planning_calculation_input_fingerprint": null,
    "observed_rtisa_planning_calculation_input_fingerprint": null,
    "supplied_retirement_target_date": null,
    "observed_target_retirement_target_date": null,
    "observed_rtisa_retirement_target_date": null,
    "observed_target_result_fingerprint": null,
    "observed_rtisa_admission_result_fingerprint": null,
    "result_state": "block_no_result",
    "failure_stage": "<closed stage>",
    "failure_detail_code": "<closed code>"
  }
}
```

The nested failure is the exact Section 13 failure envelope excluding only
`result_fingerprint`. Every nullable identity key is present. A supplied value
is included only if it passes its own lexical/type validation; otherwise it is
null. Each authority-specific observed value follows the extraction and stage
rules in Section 13.1; no generic observed field or authority-precedence alias
is permitted.

### 12.5 Metadata sensitivity boundary

RTICB must not independently add local actor, audit timestamp, execution time,
request time, or observer metadata to any preimage. Such RTICB-local metadata is
fingerprint-invariant.

RTICB nevertheless binds accepted upstream fingerprints verbatim. The target
result fingerprint transitively includes the upstream target authority's
`confirmation_actor` and `confirmed_at`. If that upstream contract changes its
result fingerprint because such metadata changed, the RTICB input, entry, and
result identities must change accordingly. RTICB must not strip, reconstruct,
reinterpret, or weaken that upstream sensitivity.

### 12.6 Fingerprint ownership and verification inventory

Fingerprint verification follows three closed categories. "Complete preimage"
means the permitted target and RTISA result objects contain every canonical
field required by the fingerprint owner's accepted contract. A projected
object plus a fingerprint is not presumed to be a complete preimage.

#### Category A — RTICB-owned fingerprints

RTICB independently constructs and verifies every fingerprint it owns:

| Exact field | Owner | Complete preimage available | RTICB recomputation required | Structural validation required | Transitively bound into RTICB identity |
|---|---|---:|---:|---:|---:|
| `comparison_input_fingerprint` | RTICB | YES | YES | YES | YES |
| `source_comparison_fingerprint` | RTICB | YES | YES | YES | YES |
| `comparison_result_fingerprint` | RTICB | YES | YES | YES | final identity |
| failure `result_fingerprint` | RTICB | YES | YES | YES | final failure identity |

Their only canonical preimages are Sections 12.1 through 12.4.

#### Category B — consumed upstream fingerprints with complete preimage present

| Exact field | Owner | Complete preimage available in permitted result | RTICB recomputation required | Structural validation required | Transitively bound into RTICB identity |
|---|---|---:|---:|---:|---:|
| target `target_result_fingerprint` | canonical retirement monthly income target authority | YES — the complete target result excluding this field is present | YES | YES | YES, in RTICB input and result |
| target `target_semantic_fingerprint` | canonical retirement monthly income target authority | YES — the complete authoritative `target` object is present | YES | YES | YES, in RTICB input and result |
| RTISA `admission_result_fingerprint` | RTISA | YES — the complete RTISA result excluding this field is present | YES | YES | YES, in RTICB input and result |

These are the only consumed upstream fingerprints RTICB independently
recomputes. Their preimages and contract namespace values come from the
accepted owning authority, not an RTICB reconstruction.

#### Category C — transitively bound upstream fingerprints without complete preimage

| Exact field/location | Owner | Complete preimage available in permitted results | RTICB recomputation required | Structural validation required | Transitively bound into RTICB identity |
|---|---|---:|---:|---:|---:|
| target and RTISA `planning_calculation_input_fingerprint` | canonical planning input authority | NO | NO | YES; also require all supplied/observed relationships in this Definition | YES, directly in RTICB input/result |
| RTISA `pension_portfolio_result_fingerprint` | canonical pension target-date portfolio authority | NO — portfolio result is not carried by RTISA | NO | YES | YES through the recomputed RTISA result fingerprint |
| each entry `upstream_identity.source_fingerprint` | canonical planning/source snapshot authority for that source | NO — complete canonical source record is not carried | NO | YES | YES, directly in the RTICB entry and therefore result |
| each entry `upstream_identity.pension_source_result_fingerprint` when non-null | pension target-date execution authority | NO — complete pension source result is not carried | NO | YES | YES, directly in the RTICB entry and therefore result |
| each non-null resolution `income_fingerprint` | canonical planning recurring-income authority | NO — complete recurring-income source record is not carried | NO | YES | YES inside the entry resolution |
| each non-null resolution `canonical_fingerprint` | canonical pension source authority | NO — complete canonical pension source record is not carried | NO | YES | YES inside the entry resolution |

RTISA exposes no `source_entry_fingerprint` field. Consequently there is no
RTISA per-entry fingerprint to recompute or bind beyond the exact nested fields
listed above and the top-level RTISA result fingerprint.

For every Category C field, RTICB must:

1. validate required presence/nullability and canonical SHA-256 structure under
   the consumed RTISA/target schema;
2. validate relationships available from the supplied results, including
   repeated planning identity equality and paired resolution nullability;
3. preserve the fingerprint byte-for-byte;
4. bind it at the exact RTICB preimage location specified above; and
5. rely on the accepted upstream producer as owner of its computation.

RTICB must not synthesize a preimage from projected fields, query raw recurring
income or pension rows, reconstruct canonical source records, discover sources,
bypass RTISA, open a second session/snapshot, or invoke a transaction-owning
reader solely to recompute a Category C fingerprint. Absence of the complete
preimage is not a fingerprint mismatch.

If separately authorized upstream work later includes a complete preimage, a
Category C fingerprint does not automatically become Category B. Reclassification
requires an explicit Definition change.

## 13. Failure and fail-closed contract

Expected authority invalidity/unavailability is represented by one deterministic
`block_no_result` envelope rather than a partial successful result. It has
exactly these required keys and types:

| Key | Type and null rule |
|---|---|
| `schema_version` | exact non-null `SCHEMA_VERSION` value |
| `client_id` | positive integer when the request client is valid; otherwise null |
| `supplied_planning_calculation_input_fingerprint` | valid SHA-256 string or null |
| `observed_target_planning_calculation_input_fingerprint` | target authority's valid SHA-256 string or null |
| `observed_rtisa_planning_calculation_input_fingerprint` | RTISA authority's valid SHA-256 string or null |
| `supplied_retirement_target_date` | canonical ISO date or null |
| `observed_target_retirement_target_date` | target authority's canonical ISO date or null |
| `observed_rtisa_retirement_target_date` | RTISA authority's canonical ISO date or null |
| `observed_target_result_fingerprint` | valid SHA-256 string or null |
| `observed_rtisa_admission_result_fingerprint` | valid SHA-256 string or null |
| `result_state` | exact literal `block_no_result` |
| `failure_stage` | one closed stage below |
| `failure_detail_code` | one code assigned to that stage below |
| `result_fingerprint` | valid SHA-256 under Section 12.4 |

No key may be absent and no additional key is permitted.

Observed identity extraction is field-local and deterministic. For an authority
that has been evaluated, an observed planning fingerprint/date is copied when
the authority value is present and independently passes that field's primitive
canonical validation (lowercase SHA-256 or canonical ISO date), even if another
part of the authority object makes the whole authority structurally invalid.
A missing, null, or locally invalid value is represented by null. No value is
copied from the request or from the other authority.

Authority evaluation and null rules by failure stage are exact:

| Failure stage | Target observed fields | RTISA observed fields |
|---|---|---|
| `request_validation` | null; no authority is evaluated | null; no authority is evaluated |
| `snapshot_admission` | null; no authority is evaluated | null; no authority is evaluated |
| `target_authority` | field-local observations from the evaluated target result, otherwise null | null; RTISA is not evaluated after target-stage failure |
| `rtisa_authority` | observations from the already validated target result | field-local observations from the evaluated RTISA result, otherwise null |
| `cross_authority_identity` | observations from the validated target result | observations from the validated RTISA result |
| `source_universe` | observations from the validated target result | observations from the validated RTISA result |
| `classification` | observations from the validated target result | observations from the validated RTISA result |

Thus, when request `A`, target `B`, and RTISA `C` disagree, the supplied field
is `A`, the target-specific observed field is `B`, and the RTISA-specific
observed field is `C`. Neither observed authority has precedence over or
replaces the other, and there is exactly one failure envelope representation.

### 13.1 Closed condition-to-code mapping and precedence

Stages are evaluated in the table order. Codes inside a stage are evaluated in
the displayed order. The first true condition is the sole authoritative
failure; later conditions are not reported.

| Stage | Ordered code | Exact condition |
|---|---|---|
| `request_validation` | `RTICB_REQUEST_SCHEMA_INVALID` | request is not an object or its key set is not exact |
|  | `RTICB_CLIENT_ID_INVALID` | `client_id` is bool, non-integer, or not positive |
|  | `RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID` | supplied planning fingerprint is not lowercase SHA-256 |
|  | `RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID` | supplied target date is not canonical ISO date |
| `snapshot_admission` | `RTICB_REQUIRES_FRESH_TRANSACTION` | supplied session already has transaction/new/dirty/deleted state |
|  | `RTICB_UNSUPPORTED_DATABASE` | dialect is neither PostgreSQL nor the accepted SQLite test dialect |
| `target_authority` | `RTICB_TARGET_AUTHORITY_SCHEMA_INVALID` | returned target object/key/type/enum/nullability structure is not its accepted schema |
|  | `RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID` | structurally valid Category B target result or semantic fingerprint is not canonical or does not recompute from its complete supplied preimage |
|  | `RTICB_TARGET_AUTHORITY_UNAVAILABLE` | a structurally and cryptographically valid target result has `authority_state = UNAVAILABLE` |
|  | `RTICB_TARGET_AUTHORITY_NOT_READY` | a valid non-`UNAVAILABLE` target result is not simultaneously `CURRENT`, confirmed under its accepted contract, and `target_ready = true` |
| `rtisa_authority` | `RTICB_RTISA_AUTHORITY_SCHEMA_INVALID` | returned RTISA top-level object/key/type/enum/nullability structure is not its accepted schema; this validates that source/partition fields are arrays but defers entry contents and partition relationships to `source_universe` |
|  | `RTICB_RTISA_AUTHORITY_FINGERPRINT_INVALID` | structurally valid Category B `admission_result_fingerprint` is not canonical or does not recompute from the complete supplied RTISA result preimage |
|  | `RTICB_RTISA_AUTHORITY_UNAVAILABLE` | a structurally and cryptographically valid RTISA result has `universe_completeness_state = UNAVAILABLE` |
|  | `RTICB_RTISA_AUTHORITY_NOT_READY` | a valid non-`UNAVAILABLE` RTISA result is not simultaneously `COMPLETE_EVIDENCED`, `READY`, and `admission_ready = true` |
| `cross_authority_identity` | `RTICB_CLIENT_ID_MISMATCH` | valid target/RTISA/request client IDs are not all equal |
|  | `RTICB_PLANNING_IDENTITY_MISMATCH` | valid target/RTISA/supplied planning fingerprints are not all equal |
|  | `RTICB_RETIREMENT_TARGET_DATE_MISMATCH` | valid target/RTISA/supplied retirement dates are not all equal |
| `source_universe` | `RTICB_SOURCE_UNIVERSE_INVALID` | source ID/order/uniqueness, non-basis entry shape, or nested Category C identity structure/relationship is invalid |
|  | `RTICB_SOURCE_COVERAGE_MISMATCH` | valid entry IDs and included/excluded/unresolved partitions are not exact, disjoint coverage, or a ready RTISA contains an unresolved ID/entry |
| `classification` | `RTICB_SOURCE_BASIS_EVIDENCE_INVALID` | an included entry uses an unsupported basis enum, wrong basis-field type, missing/null required basis key, malformed non-null basis date, or illegal basis/date nullability combination |

The table is the complete `failure_stage` and `failure_detail_code` vocabulary.
Codes cannot move between stages. There is no `result_identity` failure stage,
`RTICB_RESULT_IDENTITY_CONSTRUCTION_FAILED` code, or
`RTICB_CLASSIFICATION_CONSTRUCTION_FAILED` code. After semantic validation,
classification cardinality, result assembly, canonical JSON, and fingerprint
construction are deterministic implementation obligations. Failure of their
machinery is an internal technical exception, not a semantic input condition.

### 13.2 Classification versus fatal authority data

The route boundary is exact:

- Valid source-level evidence producing classification is limited to the
  accepted enums and null forms: income `UNKNOWN`, price `UNKNOWN` with null
  date, and `REAL_AT_REFERENCE_DATE` with null source date. These produce
  `BASIS_UNRESOLVED`, never a fatal envelope.
- Source-local REAL reference-date validation occurs regardless of target price
  basis. A null REAL source date contributes
  `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING`; any simultaneously known price-basis
  mismatch is also preserved. The unresolved reason controls the state.
- Known valid unequal bases/dates contribute mismatch reasons and, only when no
  unknown/missing reason exists, produce `NORMALIZATION_REQUIRED`; they never
  produce a fatal envelope.
- Wrong types, missing required keys, unsupported enum strings, malformed
  non-null dates, illegal enum/date nullability, malformed upstream identity,
  a Category A/B recomputation mismatch, or a structurally invalid Category C
  fingerprint are malformed canonical authority data. Top-level
  object/fingerprint defects route at `target_authority` or `rtisa_authority`;
  RTISA per-entry non-basis shape and nested Category C identity defects route
  at `source_universe`; and source-basis defects route at `classification`.
  Each produces the exact mapped `block_no_result` code. Failure to
  independently recompute Category C is not a legal failure condition because
  its complete preimage is not a permitted RTICB input.
- Internal failures while producing a per-source classification, assembling a
  successful result or failure envelope, canonicalizing JSON, encoding UTF-8,
  or computing SHA-256 are not detectable semantic input conditions. They are
  technical exceptions. This remains true when all semantic values were already
  validated and when the exception occurs while constructing a failure
  fingerprint; RTICB must not emit a partially built or substitute envelope.
- Exceptions raised by SQLAlchemy/database/driver operations, transaction
  setup/completion, upstream execution before a result object exists, rollback,
  or non-domain runtime failures are technical. RTICB rolls back and re-raises
  the original exception; it does not convert it to a failure envelope or a
  professional classification. If rollback itself fails, the connection is
  invalidated and that technical failure remains raised.

Thus the same validated input cannot legally select more than one route.

### 13.3 Binding malformed-boundary routing

The following near-miss classes have one route and do not depend on catching a
runtime exception:

| Near miss | Exact route |
|---|---|
| request missing/extra key or wrong container | `request_validation` / `RTICB_REQUEST_SCHEMA_INVALID` |
| request null, bool-as-int, malformed or whitespace-padded scalar | the first field-specific request code in Section 13.1 |
| uppercase, wrong-length, or non-hex SHA-256 | the owning request/authority fingerprint-invalid code |
| malformed date, datetime text in a date field, or whitespace-padded date | the owning request/authority schema code, except source basis dates which use `RTICB_SOURCE_BASIS_EVIDENCE_INVALID` |
| target/RTISA missing or extra top-level key, wrong top-level container/type (including a non-array source/partition field), or unsupported top-level enum | the owning authority schema-invalid code |
| valid Category B structure with canonical stored fingerprint that does not recompute | the owning authority fingerprint-invalid code |
| malformed Category C identity or invalid relationship visible in an RTISA entry | `source_universe` / `RTICB_SOURCE_UNIVERSE_INVALID` |
| duplicate/empty/whitespace-padded/non-string/out-of-order source ID or malformed non-basis entry shape | `source_universe` / `RTICB_SOURCE_UNIVERSE_INVALID` |
| source-universe omission/addition, partition overlap, state/partition mismatch, or unresolved source in a purported ready RTISA | `source_universe` / `RTICB_SOURCE_COVERAGE_MISMATCH` |
| included source missing a basis key, null/wrong-type/unsupported basis enum, malformed non-null REAL date, or non-null date with `UNKNOWN`/nominal price basis | `classification` / `RTICB_SOURCE_BASIS_EVIDENCE_INVALID` |
| REAL source with null date | valid `BASIS_UNRESOLVED` classification with `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING` |
| unexpected serializer, JSON, SHA-256, assertion, programming, or other internal runtime failure | technical exception; rollback/re-raise, no semantic envelope |

Primitive validation is lexical and type-strict: booleans are not integers;
canonical SHA-256 is lowercase 64-character hexadecimal; canonical dates are
exact `YYYY-MM-DD` dates rather than datetime strings; enum values and IDs are
not trimmed; and exact-object contracts reject extra keys. Failure fingerprints
use only the authority-specific observations permitted by Sections 12.4 and 13,
never a substituted request or other-authority value.

## 14. Transaction and execution boundary

One public RTICB operation receives one caller-supplied SQLAlchemy `Session` and
owns one transaction/snapshot for the complete target-plus-RTISA assessment.

- PostgreSQL uses one repeatable-read, read-only transaction.
- SQLite uses the repository's accepted equivalent test boundary.
- The operation requires a fresh session transaction state.
- All upstream reads used to produce the two consumed results occur within that
  same snapshot and supplied session.
- Public upstream endpoints/readers that open, commit, retry, or own another
  transaction must not be nested.
- No second session, commit, write, flush, autoflush, hidden retry, or
  cross-snapshot result reuse is permitted.
- After the full result or semantic failure envelope is assembled and
  fingerprinted, the operation ends its read-only transaction exactly once by
  rollback/release before returning the detached plain result. Success never
  calls `commit()` merely to close a read-only transaction.
- Any failure after RTICB starts its transaction rolls back the complete
  operation; a failed rollback invalidates the connection according to
  established repository discipline. `RTICB_REQUIRES_FRESH_TRANSACTION` is
  detected before RTICB starts or owns a transaction and therefore does not
  rollback, commit, or otherwise mutate the caller's pre-existing session
  state. A request-validation failure likewise performs no transaction action.

Implementation may expose/reuse non-public, non-owning upstream derivation
boundaries solely to preserve this snapshot discipline. Such extraction must
not change accepted upstream semantics.

## 15. Persistence, API, and UI posture

RTICB is a pure derived authority. No persistence requirement has been found.
The expected implementation introduces no table, column, migration, stored
decision, audit row, write command, or mutation endpoint.

No API or frontend surface is required for this package. A future consumer may
be authorized separately, but this Definition does not authorize exposure or
workflow changes.

## 16. Explicit exclusions

RTICB must not own or perform:

- tax calculation or tax characterization inference;
- gross-to-net, net-to-gross, gross-up, or net-down conversion;
- CPI calculation, price indexation, price normalization, reference-date
  conversion, or future inflation projection;
- income totals, income gaps, funding coverage, or resource eligibility;
- withdrawals, capital conversion, annuitization, allocation, optimization, or
  scenario execution;
- source discovery, admission, deduplication, identity resolution, or
  applicability decisions;
- changes to target, pension, RTISA, planning-input, resource-state, M09/M10,
  M11-M14, `02M`, or `M08E` semantics.

## 17. Expected implementation surface

Subject to later authorization, the expected minimum surface is:

- one backend pure-derived comparison service;
- focused unit/contract tests;
- focused PostgreSQL snapshot/boundary tests;
- governance inventory/traceability updates if required by current tests; and
- at most narrow non-public extraction in the two upstream services when needed
  to preserve the single-snapshot boundary without semantic change.

Expected absent surfaces: models, migrations, persistence schemas, write APIs,
frontend code, navigation, totals/gap engines, and normalization engines.

## 18. Acceptance criteria

- `AC-01`: package identity, class, governance version, and owner decision are explicit.
- `AC-02`: only the current target authority and current RTISA result are direct inputs.
- `AC-03`: target and RTISA client identity must match the request.
- `AC-04`: target and RTISA planning fingerprints must match exactly.
- `AC-05`: target and RTISA retirement target dates must match exactly.
- `AC-06`: Category B target result and semantic fingerprints are independently recomputed from their complete supplied preimages.
- `AC-07`: the Category B RTISA result fingerprint is independently recomputed from its complete supplied result preimage; nested Category C fingerprints follow Section 12.6 without reconstruction.
- `AC-08`: stale, unavailable, malformed, or non-ready target authority fails closed.
- `AC-09`: partial, unavailable, malformed, or non-ready RTISA fails closed.
- `AC-10`: source universe equals RTISA source entries exactly.
- `AC-11`: every entry of the accepted ready RTISA result has exactly one ordered comparison entry.
- `AC-12`: only RTISA `INCLUDED` entries undergo basis comparison.
- `AC-13`: excluded RTISA entries remain explicit successful-result coverage evidence; any unresolved RTISA entry makes the upstream authority not ready and prevents a successful RTICB result.
- `AC-14`: `GROSS/GROSS` and `NET/NET` income bases match directly.
- `AC-15`: known unequal income bases require normalization.
- `AC-16`: the accepted source literal `UNKNOWN` is unresolved; unsupported or malformed income-basis authority is fatal.
- `AC-17`: equal nominal-at-target price bases match directly.
- `AC-18`: known unequal price bases always contribute the price-basis mismatch reason and require normalization when no unresolved source evidence takes precedence.
- `AC-19`: the accepted source literal `UNKNOWN` with null date is unresolved; unsupported or malformed price-basis authority is fatal.
- `AC-20`: equal real price bases require equal valid reference dates.
- `AC-21`: every REAL source requires source-local reference-date validation regardless of target basis; null is unresolved, while a malformed non-null date is fatal authority data.
- `AC-22`: unequal real reference dates require normalization.
- `AC-23`: nominal authorities require null reference dates and malformed upstream data fails closed.
- `AC-24`: classification reasons use only the closed vocabulary and canonical ordering.
- `AC-25`: unresolved evidence takes state precedence over known mismatches without hiding either reason, including a REAL source with null date whose price basis also mismatches the target.
- `AC-26`: zero-amount admitted sources are still classified.
- `AC-27`: classification completion is independent from direct-comparison readiness.
- `AC-28`: normalization-required sources permit a complete classification result but block direct comparison.
- `AC-29`: unresolved-basis sources permit a complete classification result but block direct comparison.
- `AC-30`: an empty admitted universe is ready only when RTISA is complete and ready.
- `AC-31`: no admitted source may be silently omitted from future total/gap readiness.
- `AC-32`: source ordering and every ID partition are deterministic.
- `AC-33`: Category A input, entry, failure, and result fingerprints use the four exact, distinct, versioned namespaces and preimages defined in Section 12; failure identity uses the same authority-specific observations as its envelope.
- `AC-34`: source identity remains bound independently of equal basis semantics; Category C identities are structurally validated, relationship-checked, preserved, and transitively bound without false recomputation.
- `AC-35`: RTICB-local actor/time metadata is fingerprint-invariant, while metadata transitively bound by accepted upstream result fingerprints retains its upstream identity sensitivity.
- `AC-36`: one supplied session and one snapshot cover all authoritative reads.
- `AC-37`: no second session, nested public reader, commit, write, flush, or hidden retry occurs; the one read-only transaction is ended by rollback/release after result construction.
- `AC-38`: every expected invalidity/unavailability condition uses the exact envelope, authority-specific observed-value/null rules, code mapping, and precedence in Section 13.
- `AC-39`: SQLAlchemy/database/driver, transaction, upstream-execution, rollback, canonical serialization/JSON/UTF-8/SHA-256 machinery, assertion/programming, classification/result/failure-envelope construction, and other non-domain runtime failures rollback where possible and remain technical exceptions; no `*_CONSTRUCTION_FAILED` semantic code exists.
- `AC-40`: no persistence, migration, API, frontend, total/gap, or normalization behavior is introduced.

Acceptance range: `AC-01` through `AC-40` (40 criteria).

## 19. Negative acceptance criteria

- `NAC-01`: inferring gross/net from source category, tax labels, or pension type.
- `NAC-02`: inferring nominal/real basis from source origin or general knowledge.
- `NAC-03`: inventing a real-price reference date.
- `NAC-04`: treating `UNKNOWN` as a match.
- `NAC-05`: treating unequal known bases as directly comparable.
- `NAC-06`: performing gross/net conversion or tax calculation.
- `NAC-07`: performing CPI/indexation/reference-date conversion.
- `NAC-08`: emitting a normalized source amount.
- `NAC-09`: calculating income totals, gaps, coverage, or eligibility.
- `NAC-10`: independently discovering or rebuilding the source universe.
- `NAC-11`: bypassing RTISA admission state.
- `NAC-12`: dropping an admitted non-comparable source from readiness assessment.
- `NAC-13`: upgrading an excluded source to admitted, or admitting/classifying an unresolved RTISA source instead of failing at upstream readiness.
- `NAC-14`: accepting partial or non-ready RTISA as complete.
- `NAC-15`: accepting a stale or unconfirmed target authority.
- `NAC-16`: accepting mismatched client/planning/target identities.
- `NAC-17`: accepting malformed upstream fingerprints or a non-recomputing Category B fingerprint, attempting to recompute Category C without its complete authoritative preimage, or converting an internal serialization/hash/construction exception into a semantic fingerprint mismatch or construction-failed envelope.
- `NAC-18`: non-deterministic source, reason, blocker, or failure ordering, including a generic/alternate observed-authority representation in a failure envelope or preimage.
- `NAC-19`: collapsing distinct source identities solely because their bases match.
- `NAC-20`: independently adding RTICB-local actor/time metadata to fingerprint preimages, or stripping/weakening actor/time sensitivity already bound by an accepted upstream fingerprint.
- `NAC-21`: opening a second session or cross-snapshot authority read.
- `NAC-22`: nested public reader, any commit, write/autoflush, or hidden retry.
- `NAC-23`: introducing persistence, schema, migration, API, or frontend scope.
- `NAC-24`: changing accepted upstream semantics to simplify RTICB.
- `NAC-25`: authorizing normalization, total/gap execution, or any downstream package.

Negative-acceptance range: `NAC-01` through `NAC-25` (25 criteria).

## 20. Stop conditions

- `SC-01`: an accepted upstream contract cannot expose its result within one RTICB snapshot without semantic change.
- `SC-02`: an admitted source requires a basis interpretation not already authoritative upstream.
- `SC-03`: target and source basis vocabularies conflict beyond exact mapping stated here.
- `SC-04`: an additional Owner/Product Decision is needed to classify a valid input combination.
- `SC-05`: complete coverage would require independent source discovery or bypassing RTISA.
- `SC-06`: correctness would require persistence, normalization, totals, gaps, tax, CPI, or scenario semantics.
- `SC-07`: implementation would require reopening a closed authority rather than narrow non-semantic extraction.
- `SC-08`: deterministic identity or single-snapshot behavior cannot be proven, a fingerprint classified as Category B lacks its complete canonical preimage in the permitted results, or implementation would independently recompute/reclassify Category C without an explicit Definition change.

Stop-condition range: `SC-01` through `SC-08` (8 conditions). Encountering any
condition stops Definition/implementation progression and requires explicit
owner/governance resolution; no implementation workaround is implied.

### 20.1 Fingerprint-boundary implementation stop rule

If implementation finds that any Category B fingerprint lacks its complete
canonical preimage inside the two permitted consumed result objects, it must
stop and return for Definition clarification. It must not fetch hidden/raw
evidence, reconstruct an upstream record, or add a reader as a workaround.

Implementation likewise must stop rather than independently recompute or
silently reclassify any Category C fingerprint. Moving a fingerprint between
Categories B and C requires a separately authorized Definition change, even if
an upstream producer later exposes additional evidence.

## 21. Pre-implementation contract enumeration requirement

After Definition acceptance, the mandatory enumeration must cover at least:

- all upstream ready/unavailable/stale/malformed producer routes;
- every admitted income-basis and price-basis combination;
- nominal and real reference-date equality, mismatch, missing, and malformed cases;
- admitted and excluded successful-entry states, plus the unresolved RTISA
  whole-authority not-ready route;
- empty, singleton, and multi-source universes;
- valid combinations and malformed near-misses;
- deterministic failure envelopes and precedence, plus mutation controls proving
  serializer/hash/programming failures remain technical exceptions;
- fingerprint mutation controls for every Category A/B recomputable identity,
  plus structural, relationship, preservation, and transitive-binding controls
  for every Category C identity and relevant non-input;
- source coverage/order mutations;
- single-session/snapshot transaction mutations; and
- reusable harnesses for later implementation acceptance.

The enumeration is not performed or accepted by this Definition draft.

## 22. Current decisions and unresolved matters

`OWNER-DECISION-RTICB-001` fully resolves the professional ownership boundary
needed for this draft. No additional Owner/Product Decision is unresolved.

Implementation remains `NOT_AUTHORIZED`. Downstream authorization remains
`NOT_AUTHORIZED`. Production readiness remains `NOT_CLAIMED`.
