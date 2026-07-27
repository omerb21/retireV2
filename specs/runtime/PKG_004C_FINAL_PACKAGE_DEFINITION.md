# PKG-004C — M08A Eligibility Date Evidence Contract

## 1. Definition Status

| Field | Value |
|---|---|
| Package | `PKG-004C — M08A Eligibility Date Evidence Contract` |
| Package type | Exact PKG-004B1 calculation-input evidence-field contract |
| Definition status | `DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION` |
| Implementation | `NOT_STARTED` |
| Accepted dependencies | PKG-004B1 evidence foundation; PKG-004B2 calculation-input resolver framework; existing bounded M08A fixation engine |
| B2-to-M08A integration | `NOT_STARTED` and outside this package |
| Next package authorization | `NOT_AUTHORIZED` |

This document defines the meaning, representation, normalization, and future
resolver boundary of one PKG-004B1 evidence field. It does not authorize
implementation, register a production calculation manifest, or integrate
PKG-004B2 with fixation admission.

## 2. Purpose and Product Boundary

PKG-004C defines the exact B1 calculation-input evidence field required to
represent the date used by the existing bounded M08A fixation calculation:

`eligibility_date`

The field represents the applicable eligibility date ("יום הזכאות") for the
fixation-rights calculation. PKG-004C does not determine that date, derive it
from other facts, or decide which professional rule establishes it.

The value reaches B1 only as recorded source evidence, documentary evidence,
or a planner-entered assertion represented through the accepted PKG-004B1
boundary. The system preserves provenance and does not rank sources.

## 3. Authoritative Field Contract

| Property | Contract |
|---|---|
| Field code | `eligibility_date` |
| Meaning | Date of eligibility used by the bounded M08A fixation-rights calculation |
| Technical type | `date` |
| Canonical representation | ISO calendar date `YYYY-MM-DD` |
| Nullability for M08A | Not nullable |
| B1 representation | Existing generic fact evidence or planner assertion |
| Authority meaning | Evidence only; not professional authority or approval |
| Production M08A manifest | Not registered by this package |

The field is distinct from retirement age, planned retirement timing,
employment termination, pension commencement, and other adjacent dates.

## 4. Evidence Sources and B1 Boundary

The field may be represented through the existing accepted B1 evidence
channels:

- persisted source evidence;
- documentary evidence;
- planner assertion or manual entry first recorded in B1.

Every candidate remains client-scoped and retains its B1 evidence revision,
source references, and provenance. Manual input does not bypass B1 and is not
a direct B2 input channel.

PKG-004C uses the existing generic B1 fact-evidence persistence. It adds no
evidence lifecycle, current-authority selector, qualification, warning review,
accepted-for-use state, professional approval, or source-reliability decision.

## 5. Value and Normalization Contract

An `eligibility_date` candidate is technically usable only when it
deterministically normalizes to a valid calendar date in exact ISO
`YYYY-MM-DD` form.

The following are unusable:

- invalid calendar dates;
- datetimes whose use would require silent timezone conversion or date
  truncation;
- ages;
- a year without a complete date;
- blank or null values;
- free-text retirement descriptions;
- generic `retirement_timing` objects that do not explicitly contain the
  authorized `eligibility_date` field.

An unusable required value contributes to `missing_inputs`. It is not repaired,
inferred, coerced from an adjacent concept, or silently defaulted.

## 6. Eligibility-Year Derivation

`eligibility_year` is not a separate B1 evidence field in this contract. For a
future M08A consumer integration it is deterministically derived as:

`eligibility_date.year`

The derived value must remain equal to the year supplied to the existing
bounded M08A input contract and used for the applicable parameter resolution.
A caller may not supply a conflicting eligibility year, and no competing B1
candidate for `eligibility_year` is introduced by this package.

## 7. Deterministic Resolution Behavior

A future authorized M08A manifest will apply the accepted PKG-004B2 rules:

1. One technically valid normalized date is used automatically.
2. Multiple candidates normalizing to the same date are coalesced while all
   provenance is retained.
3. Multiple different normalized dates produce `ambiguous_inputs` until the
   user makes a valid explicit selection between available values.
4. Missing, invalid, or non-normalizable candidates produce `missing_inputs`.
5. No candidate is selected by source rank, timestamp, latest-wins, actor,
   verification label, or claimed authority.

This document does not register the manifest or execute those rules in
fixation admission.

## 8. Missing and Ambiguous Behavior

When `eligibility_date` is absent, invalid, or non-normalizable for the future
M08A calculation scope:

- the resolver result is `missing_inputs`;
- no M08A calculation-ready payload is emitted;
- no date or year is inferred or defaulted;
- unrelated calculation scopes remain available.

When different technically valid dates remain without a valid explicit user
selection:

- the resolver result is `ambiguous_inputs`;
- the conflicting normalized dates and source references remain visible;
- no M08A calculation-ready payload is emitted.

## 9. Prohibited Derivations

PKG-004C must not derive `eligibility_date` from:

- birth date;
- gender;
- retirement age;
- planned retirement date;
- employment termination date;
- first pension or pension-commencement date;
- current date;
- latest evidence timestamp;
- source priority, reliability rank, or authority rank.

Any automatic legal eligibility-date derivation requires a future separately
defined and authorized package.

## 10. Relationship to `retirement_timing`

The broad existing B1 evidence field `retirement_timing` is not
`eligibility_date`. It may contain an age, plan, timing description, date, or
structured object with another meaning.

PKG-004C creates no implicit mapping, conversion, or fallback from
`retirement_timing` to `eligibility_date`. Existing values are not rewritten,
backfilled, or reinterpreted. Any future conversion or mapping requires its own
explicit scope and authorization.

## 11. Future B2 and M08A Boundary

A future, separately authorized M08A consumer manifest will need to define:

- the bounded fixation calculation scope;
- field code `eligibility_date`;
- technical type `date`;
- ISO-date normalization;
- null not permitted;
- deterministic `eligibility_year = eligibility_date.year`.

That later package must resolve a finalized client-scoped B1 revision and
adapt only a `resolved` result into the existing M08A input boundary. PKG-004C
does not register the manifest, change `M07EntryContext`, remove obsolete
qualification gates, modify fixation admission, or change dependency
manifests.

## 12. Expected Implementation Shape

If implementation is separately authorized, the expected work remains within
the existing B1 generic fact-evidence contract and focused tests for the exact
field identity and strict date representation.

No new B1 table, schema migration, evidence lifecycle, resolution-history
aggregate, historical backfill, or production API is expected. Implementation
must stop if repository inspection proves that the existing B1 contract cannot
safely represent a strict ISO date under field code `eligibility_date`.

## 13. Explicit Exclusions

PKG-004C excludes:

- B2-to-M08A integration;
- production M08A manifest registration;
- changes to `M07EntryContext`;
- removal of obsolete qualification or warning-review gates;
- fixation admission or dependency-manifest changes;
- calculation-engine or formula changes;
- M08B, M08C, or M08D changes;
- automatic legal eligibility-date calculation;
- UI or API work;
- historical conversion or backfill;
- M08E and full M08F;
- M09-M14;
- formal 161D;
- 02M;
- production readiness;
- V1/V2 parity.

## 14. Acceptance Criteria

| ID | Acceptance criterion |
|---|---|
| AC-C-001 | The exact B1 field code is `eligibility_date`, meaning the date of eligibility used by the bounded M08A fixation-rights calculation. |
| AC-C-002 | The field accepts only a valid calendar date that deterministically normalizes to ISO `YYYY-MM-DD`; blank, null, partial, free-text, age, year-only, and silently truncated datetime values are unusable. |
| AC-C-003 | Persisted source evidence, documentary evidence, and planner-entered assertions represented through B1 may supply candidates; no direct B2 manual-entry channel exists. |
| AC-C-004 | Every candidate remains client-isolated and traceable to its B1 revision, evidence record, source references, and provenance. |
| AC-C-005 | Multiple available facts that normalize to the same date coalesce into one usable value while retaining all source references. |
| AC-C-006 | Multiple different normalized dates produce `ambiguous_inputs` until the user makes a valid explicit selection between available values. |
| AC-C-007 | Missing, invalid, or non-normalizable required values produce `missing_inputs`, emit no M08A calculation-ready payload, and do not block unrelated scopes. |
| AC-C-008 | `eligibility_year` is not a separate B1 evidence field and is deterministically derived as `eligibility_date.year`; a conflicting caller-supplied year is rejected. |
| AC-C-009 | No eligibility date is automatically derived, inferred, defaulted, ranked, or selected from adjacent facts, timestamps, or source characteristics. |
| AC-C-010 | The contract uses existing B1 generic persistence and requires no new table, schema migration, historical backfill, or conversion of existing `retirement_timing` values. |

## 15. Negative Acceptance Criteria

| ID | Prohibited behavior |
|---|---|
| NAC-C-001 | Treating `retirement_timing`, a generic retirement-timing object, or an adjacent date as `eligibility_date` without an explicitly authorized mapping. |
| NAC-C-002 | Accepting a separate or caller-supplied `eligibility_year` that conflicts with `eligibility_date.year`. |
| NAC-C-003 | Deriving the field from birth date, gender, retirement age, planned retirement date, employment termination, pension commencement, or current date. |
| NAC-C-004 | Selecting a candidate by latest-wins, evidence timestamp, source priority, reliability, actor, verification label, or authority rank. |
| NAC-C-005 | Allowing manual entry to bypass B1 through a direct B2 or fixation-admission input channel. |
| NAC-C-006 | Backfilling, rewriting, converting, or silently reinterpreting historical evidence or `retirement_timing` values. |
| NAC-C-007 | Registering a production M08A manifest, integrating B2 with fixation admission, changing `M07EntryContext`, removing qualification gates, or changing dependency manifests in this package. |
| NAC-C-008 | Changing formulas, the fixation engine, M08B, M08C, M08D, UI, APIs, or adding automatic legal eligibility-date calculation. |
| NAC-C-009 | Expanding into M08E, full M08F, M09-M14, formal 161D, 02M, production readiness, or V1/V2 parity. |

## 16. Stop Conditions

Implementation must stop and return for product or architecture direction if:

- the exact meaning of `eligibility_date` would need to change;
- a professional or legal derivation rule would need to be invented;
- an adjacent fact would need to be silently reinterpreted;
- source ranking, latest-wins, qualification, approval, or authority workflow
  would be required;
- manual input could not remain represented through B1;
- the existing B1 contract could not safely represent a strict ISO date under
  this field code;
- a new table, migration, evidence lifecycle, historical backfill, or
  resolution-history subsystem became necessary;
- fixation admission, dependency manifests, the engine, M08B-M08D, UI, API,
  M08E, full M08F, M09-M14, formal 161D, or 02M would need to change.

## 17. Final Gate

`PKG_004C_DEFINED_PENDING_IMPLEMENTATION_AUTHORIZATION`

This gate confirms only that the final package definition exists. It does not
authorize implementation or the later B2-to-M08A integration package.
