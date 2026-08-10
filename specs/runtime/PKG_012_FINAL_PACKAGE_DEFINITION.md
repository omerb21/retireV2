# PKG-012 — M08C/M08D Exempt Grant Offset and Historical Indexation Foundation

## Package Identity and Status

| Field | Value |
|---|---|
| Package | `PKG-012` |
| Module | `M08C/M08D` |
| Consumer | narrow `M08A` handoff |
| Base | `49caa28275c453f3b7cb45d9b2c86a3cc144bf94` |
| Migration expectation | `ADDITIVE_MIGRATION_REQUIRED` |
| Frontend expectation | `NARROW_FRONTEND_CHANGE_REQUIRED` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Implementation | `NOT_AUTHORIZED` |

## Authoritative Sources and Predecessor Contracts

This definition is bounded by:

- `specs/runtime/V2_RETIREMENT_PLANNING_BUSINESS_BUILD_PLAN.md` as synchronized by the separate PKG-012 plan-alignment commit;
- the accepted PKG-002 CBS/Lamas foundation, including series `120010`, server-owned evidence, typed failure, and no authoritative fallback;
- the accepted PKG-004A parameter-set foundation and accepted parameter context;
- accepted production manifest `m08a_fixation` version `1` for the existing M07-to-M08A eligibility-date dependency;
- accepted M01 client isolation, current fixation saved-run behavior, and immutable saved calculation history; and
- the locked product and professional decisions stated in this definition.

PKG-012 does not reopen those predecessor contracts. Its implementation, if separately authorized, must remain subordinate to them.

## Exact Product Outcome

PKG-012 accepts direct professional-user-entered exempt-grant records and computes a bounded historical exempt-grant offset using the exact accepted V1-derived formula, PKG-002 CBS authority, deterministic evidence, and a narrow M08A handoff.

The package does not compute remaining exempt capital. It supplies M08A with the aggregate exempt-grant offset and complete per-grant evidence needed by a separately authorized M08A calculation.

## Locked Authority Principles

### Direct professional-user authority

For this package, the six structured business values entered by the professional user are authoritative calculation inputs.

- No second professional approval is required.
- No evidence-sufficiency layer is required.
- No source-ranking, reliability, or candidate-resolution layer is required.
- The system validates technical and formula preconditions but does not decide professional sufficiency, reliability, or external truth.

### Empty collection semantics

Zero exempt-grant records means exactly:

`no exempt grants`

It does not mean unknown, not collected, missing evidence, or unresolved history. The aggregate exempt-grant offset is deterministically zero.

### No prior-withdrawal model

There is no separate prior-withdrawal business event for this calculation. The relevant historical event is an exempt grant, whether or not money was physically withdrawn.

PKG-012 prohibits a prior-withdrawal record, status, formula, or discovery workflow.

### No prior-fixation workflow

Prior fixation is outside the new-client fixation workflow. PKG-012 introduces no `prior_fixation_status`, repeat-fixation discovery, prior-fixation evidence resolution, or prior-fixation ambiguity.

### Documents

Document presence is supporting material only. The calculation consumes the structured business values entered by the professional user. PKG-012 performs no automatic Form 161 or 161D interpretation and creates no document-presence inference.

## Exact Exempt-Grant Record Contract

Each authoritative exempt-grant record contains exactly six business facts:

1. `employer_name`
2. `employer_withholding_file_number`
3. `employment_start_date`
4. `employment_end_date`
5. `grant_receipt_date`
6. `exempt_grant_amount`

A server-generated technical `grant_id` is required for record identity but is not a seventh business fact.

All six fields are required for a new authoritative calculation record. No user-entered `indexed_amount` is accepted; indexed amount is a system-derived calculation result.

### Field validation

- `employer_name` is required and nonblank.
- `employer_withholding_file_number` is required and nonblank. No additional Israeli-format rule may be invented without a separately accepted contract.
- All three dates are required exact ISO calendar dates.
- `employment_start_date < employment_end_date` is required.
- No rule requires `grant_receipt_date == employment_end_date` or otherwise orders those two dates.
- `grant_receipt_date` after the eligibility date is not a valid historical input for an authoritative calculation.
- `exempt_grant_amount` is a finite canonical monetary value greater than or equal to zero.
- Explicit zero is valid; negative, non-finite, or malformed amounts are prohibited.

## Exact 15-Year Relevance Rule

The reference date is `grant_receipt_date`.

For legacy compatibility only, an already-stored historical legacy record may have used `employment_end_date` when its grant date was absent. New authoritative records require `grant_receipt_date` and never use that fallback.

The exact calculation is:

```text
years_difference =
    eligibility_year - grant_year
    + (eligibility_month - grant_month) / 12
    + (eligibility_day - grant_day) / 365.25
```

Then:

```text
if years_difference > 15:
    grant is outside the relevant period
    per_grant_offset = 0
else:
    grant remains relevant
```

Exactly 15 years is included. Only `years_difference > 15` excludes the grant.

This is a whole-record inclusion/exclusion rule. It is not a proportional 15-year calculation and must not be replaced by a calendar-date cutoff such as `grant_date <= eligibility_date - 15 calendar years`.

## Exact 32-Year Proportionality Rule

Define:

```text
window_start = eligibility_date - 11,688 days

total_employment_days =
    (employment_end_date - employment_start_date).days

overlap_start =
    max(employment_start_date, window_start)

overlap_end =
    min(employment_end_date, eligibility_date)

overlap_days =
    max((overlap_end - overlap_start).days, 0)

ratio = overlap_days / total_employment_days
ratio = min(max(ratio, 0), 1)
```

Required characteristics:

- `total_employment_days > 0` for an authoritative valid record.
- Units are days and no inclusive endpoint day is added.
- Leap years flow through ordinary date subtraction.
- The window is exactly `11,688` days.
- Employment after eligibility is excluded from the numerator.
- Full employment duration remains the denominator.
- Employment longer than 32 years does not automatically receive ratio `1`.
- The ratio is not rounded before monetary multiplication.

The divergent formula `work_days / days_in_32_year_window` is prohibited as the authoritative V1-equivalent formula.

## Exact CBS Indexation Contract

PKG-012 consumes the accepted PKG-002 CBS foundation using series `120010`.

For a normal authoritative grant:

```text
value  = exempt_grant_amount
date   = grant_receipt_date
toDate = eligibility_date
```

The backend owns request construction and retains the accepted request/response evidence. The raw CBS result is preserved separately from the rounded application amount.

```text
indexed_full = CBS result rounded to 0.01
```

If required CBS indexation fails, no authoritative successful result exists. The affected calculation returns accepted typed failure behavior.

The following are prohibited:

- caller-forged CBS evidence;
- a user-entered value presented as a CBS result;
- nominal fallback presented as indexed;
- cached, estimated, asserted, or hard-coded data presented as current CBS authority.

An explicit zero grant amount may produce a deterministic zero offset without a CBS call. No CBS request or response evidence may be fabricated for that case.

## Exact Formula and Monetary Checkpoints

For each grant that remains relevant under the 15-year rule:

```text
indexed_full =
    round_CBS_application_amount_to_0_01(...)

limited_indexed_amount =
    round(indexed_full * ratio, 2)

per_grant_offset =
    round(limited_indexed_amount * 1.35, 2)
```

The ratio is never rounded before multiplication. The monetary checkpoints occur in the order shown.

### Exact 1.35 rule

The professional multiplier is exactly `1.35`. It applies only to the proportional indexed per-grant amount.

It does not apply directly to nominal amount, full indexed amount before proportionality, an aggregate of grants, actual capitalizations, or M06 conversions.

PKG-012 consumes `grant_impact_multiplier = 1.35` from accepted parameter context for provenance and fails closed if the required value is missing or incompatible. There is no hidden or default fallback, and this definition makes no claim that `1.35` varies annually.

## Per-Grant Processing and Aggregation

Each grant is processed independently in this exact business order:

```text
grant
 -> 15-year relevance
 -> CBS indexed amount
 -> 32-year proportionality
 -> round proportional amount
 -> x 1.35
 -> round per-grant offset
```

A grant already deterministically excluded by the 15-year rule need not trigger an unnecessary CBS call, provided the business result is identical and evidence does not claim that a request occurred.

```text
aggregate_grant_offset =
    sum(per_grant_offset for each entered grant)
```

Every per-grant offset is rounded before aggregation. Early aggregation is prohibited.

Zero grant rows yield `aggregate_grant_offset = 0`.

Multiple records are not automatically consolidated, deduplicated, or silently merged by employer, withholding-file number, grant date, equal amount/date, or overlapping employment. The server-generated `grant_id` is record identity. The withholding-file number is business metadata, not a mathematical deduplication key.

## Actual Capitalizations Boundary

Actual capitalizations remain a separate historical category. They are not exempt grants, prior withdrawals, or M06 conversion results.

PKG-012 does not redesign actual-capitalization persistence and does not apply CBS grant indexation, the 32-year grant ratio, the 15-year grant rule, or `1.35` to actual capitalizations.

Separate record IDs, input sections, snapshot sections, and calculation effects remain required.

## M06 Exclusion

M06 is not a dependency. A generated pension/capital conversion cannot become an exempt grant, an actual capitalization, or a historical prior-use fact.

## M08C Ownership Boundary

M08C owns:

- direct professional-user-entered exempt-grant records;
- the exact six-field business record contract;
- client-scoped CRUD before calculation;
- zero records equals no exempt grants;
- separate future-grant reservation ownership; and
- separate actual-capitalization record ownership.

Every valid entered grant participates in a new calculation. No separate include/exclude approval, accepted-for-use step, collection-state approval, conflict approval, or ambiguity approval exists for this direct-user path.

A removed record is absent from future calculations. Existing saved-run snapshots remain immutable.

## M08D Ownership Boundary

M08D owns the complete exempt-grant historical offset calculation:

1. 15-year relevance;
2. 32-year ratio;
3. PKG-002 CBS indexation;
4. monetary rounding checkpoints;
5. the `1.35` multiplier;
6. per-grant offset;
7. aggregate grant offset;
8. calculation evidence; and
9. formula/contract version.

M08D owns no prior-withdrawal, prior-fixation, document-resolution, or professional evidence-sufficiency workflow.

## Narrow M08A Handoff

PKG-012 produces a deterministic M08A handoff containing at least:

- aggregate exempt-grant offset;
- deterministic per-grant breakdown and grant IDs;
- exact input snapshot;
- 15-year evidence and result;
- 32-year ratio evidence;
- CBS evidence/reference where applicable;
- indexed and proportional amounts;
- multiplier and parameter-set identity;
- per-grant final offset; and
- formula/contract version.

M08A continues to own starting exempt capital, M08B annual entitlement parameters, combination with future-grant reservation and actual-capitalization effect, final subtraction, zero floor, remaining exempt capital, and the final fixation result.

M08D must not create a second competing remaining-exempt-capital result.

## M08B Boundary

M08B remains authority for accepted parameter-set identity and annual calculation context, including monthly cap, exemption percentage, capital multiplier, and accepted parameter-set provenance.

For PKG-012, `1.35` is professionally locked but consumed through accepted parameter context. PKG-012 does not broaden M08B.

## Persistence and Migration Boundary

Status: `ADDITIVE_MIGRATION_REQUIRED`.

Existing grant persistence already contains a technical grant ID, employer name, employment start date, employment end date, grant date, and nominal amount.

The corrected contract requires adding and persisting `employer_withholding_file_number` and aligning the new authoritative path so that:

- employer name is required;
- nominal exempt amount is required;
- user-entered indexed amount is not required or accepted as calculated evidence;
- indexed amount is system-derived;
- legacy stored rows are preserved;
- no business fact is inferred or backfilled; and
- an incomplete legacy row remains stored but cannot enter a new authoritative calculation until all six facts are explicitly complete.

The exact additive migration mechanics for a legacy mandatory `indexed_amount` are an implementation-design concern. No destructive migration or reinterpretation is authorized by this definition.

## Backend and API Boundary

A separately authorized implementation may provide only the bounded surfaces needed to:

- list, create, edit, and remove current client-scoped grant records;
- validate the exact six-field contract;
- calculate the per-grant and aggregate offset;
- return the deterministic breakdown and typed failures;
- preserve the immutable saved-run snapshot and evidence; and
- expose the narrow M08A handoff.

The caller supplies business input intent only. It cannot supply authoritative client ownership, final formula results, CBS evidence identity, server calculation timestamp, or canonical snapshot fingerprint.

## Frontend Boundary

Status: `NARROW_FRONTEND_CHANGE_REQUIRED`.

The bounded workflow supports:

- listing current grants;
- add, edit, and remove before calculation;
- the exact six business fields;
- ordinary field validation;
- no user-entered indexed amount;
- per-grant calculation breakdown; and
- aggregate grant-offset display.

The frontend must use the accepted client-context generation pattern. Each asynchronous request captures client ID and a monotonic generation. Stale A-to-B and A-to-B-to-A success, structured error, rejected promise, and `finally` cannot mutate or clear state owned by the newer visit.

No M07 evidence-candidate, client-declaration, source-ranking, prior-withdrawal, or prior-fixation UI is included.

## User-Edit and Saved-Run Lifecycle

Before calculation, grant records are normal client-scoped mutable CRUD records.

After calculation, saved-run snapshots are immutable. Later grant edits affect future calculations only and never rewrite historical inputs, CBS evidence, ratios, offsets, or saved results.

No M07 evidence revision lifecycle is required for this direct-user path.

## Saved-Run Reproducibility Contract

For every grant, a saved calculation preserves:

- grant ID and client ID;
- all six business facts and eligibility date;
- nominal exempt amount;
- calculated 15-year difference and relevance/exclusion result;
- 32-year window start;
- total employment days;
- overlap start, overlap end, and overlap days;
- exact ratio representation;
- CBS request and raw response evidence where applicable;
- rounded indexed and proportional amounts;
- `1.35` and parameter-set identity; and
- final per-grant offset.

The aggregate snapshot preserves a deterministic grant breakdown, aggregate grant offset, formula/contract version, and technical calculation timestamp.

Actual-capitalization snapshot data remains separate.

## Client Isolation and Anti-Leakage

Same-client enforcement is required across grant CRUD, calculation, saved runs, result retrieval, handoff, and CBS evidence associations.

Foreign grant IDs must not disclose existence through status, body, counts, timing classification, or side effects. Missing and foreign references have the same public behavior.

## Validation and Failure Contract

- Missing required fields fail at field level.
- Invalid date order fails.
- A grant receipt date after eligibility fails the affected calculation.
- Negative, non-finite, and malformed amounts fail.
- Explicit monetary zero remains a valid value.
- Required CBS failure fails the affected authoritative calculation.
- Missing or incompatible `grant_impact_multiplier = 1.35` fails closed.
- Technical or malformed input failure is never converted into an authoritative zero-impact result.

## Required Golden Behavior Cases

A separately authorized implementation must prove at least:

1. zero grants produce aggregate offset `0`;
2. one in-range grant;
3. a grant with `years_difference > 15` produces offset `0`;
4. exactly 15 years is included;
5. employment shorter than 32 years;
6. employment exactly 32 years;
7. employment longer than 32 years;
8. partial overlap;
9. employment wholly outside the window;
10. employment end after eligibility excludes post-eligibility days from the numerator;
11. multiple grants are independently processed and aggregated;
12. explicit zero amount;
13. negative amount rejection;
14. required CBS failure;
15. client isolation and foreign-ID anti-leakage;
16. frontend A-to-B stale response rejection; and
17. frontend A-to-B-to-A stale response rejection.

The repository-supported numeric golden case is:

```text
indexed amount = 100000
ratio = 0.5
proportional amount = 50000.00
1.35 offset = 67500.00
```

No unsupported numeric golden result is authorized for the other cases.

## Stop Conditions

Implementation must stop and return the named condition if it would require:

- `PKG_012_SIX_FIELD_CONTRACT_CONFLICT`: changing or expanding the exact six business facts;
- `PKG_012_DIRECT_AUTHORITY_CONFLICT`: adding a second approval, evidence-sufficiency, source-ranking, or reliability decision;
- `PKG_012_15_YEAR_CONTRACT_CONFLICT`: replacing the exact V1-derived difference formula or excluding exactly 15 years;
- `PKG_012_32_YEAR_CONTRACT_CONFLICT`: changing `11,688` days, the overlap numerator, or the full-employment denominator;
- `PKG_012_CBS_AUTHORITY_CONFLICT`: bypassing PKG-002, fabricating evidence, or adding an authoritative fallback;
- `PKG_012_ROUNDING_ORDER_CONFLICT`: changing the locked monetary checkpoint order;
- `PKG_012_MULTIPLIER_CONFLICT`: moving, defaulting, or changing `1.35`;
- `PKG_012_M08A_OWNERSHIP_CONFLICT`: computing a competing remaining-exempt-capital result;
- `PKG_012_LEGACY_MIGRATION_DESTRUCTIVE`: destructive migration, inferred backfill, or reinterpretation of legacy rows;
- `PKG_012_CLIENT_ISOLATION_BLOCKED`: inability to enforce same-client ownership and anti-leakage;
- `PRIOR_WITHDRAWAL_SCOPE_REQUIRED`: introduction of a prior-withdrawal model;
- `PRIOR_FIXATION_SCOPE_REQUIRED`: introduction of prior-fixation workflow;
- `M07_SCOPE_REQUIRED`: introduction of an M07 evidence resolver or approval workflow;
- `M08E_SCOPE_REQUIRED`: formal 161D output is required;
- `M09_M14_SCOPE_REQUIRED`: any M09-M14 behavior is required; or
- `PRIOR_PACKAGE_REGRESSION_BLOCKED`: an accepted predecessor contract would regress.

## AC-012 Catalogue

- **AC-012-001:** Each new authoritative grant has exactly the six required business fields and a server-generated technical `grant_id`.
- **AC-012-002:** Direct professional-user-entered structured values are authoritative without second approval, evidence sufficiency, reliability ranking, or candidate resolution.
- **AC-012-003:** Zero grant records means no exempt grants and produces aggregate offset `0`.
- **AC-012-004:** Employer name and withholding-file number are required and nonblank without invented format rules.
- **AC-012-005:** Dates are exact ISO dates, employment start is strictly before employment end, and no unsupported grant-date/employment-end equality rule exists.
- **AC-012-006:** Grant receipt after eligibility fails the affected authoritative calculation.
- **AC-012-007:** Exempt amount is finite, canonical, and nonnegative; explicit zero is valid and negative or malformed values fail.
- **AC-012-008:** New authoritative records never require or accept user-entered indexed amount as calculated evidence.
- **AC-012-009:** The 15-year calculation uses the exact year/month/day difference formula based on grant receipt date.
- **AC-012-010:** Only `years_difference > 15` excludes a grant; exactly 15 years remains included.
- **AC-012-011:** The 15-year rule is whole-record inclusion/exclusion and never a proportional calculation.
- **AC-012-012:** The 32-year window starts exactly `11,688` days before eligibility.
- **AC-012-013:** Total employment days use full employment duration with no inclusive endpoint day.
- **AC-012-014:** Overlap uses the bounded max/min dates, excludes employment after eligibility, and clamps overlap days at zero.
- **AC-012-015:** Ratio is overlap days divided by full employment days, clamped to `[0,1]`, including for employment longer than 32 years.
- **AC-012-016:** Ratio is retained without rounding before monetary multiplication.
- **AC-012-017:** Normal indexation uses PKG-002 series `120010` with nominal amount, grant receipt date, and eligibility date.
- **AC-012-018:** Server-owned CBS request and raw response evidence are retained separately from rounded indexed amount.
- **AC-012-019:** Required CBS failure produces typed calculation failure and no authoritative successful result or fallback.
- **AC-012-020:** An explicit zero grant may produce deterministic zero without a CBS call and without fabricated CBS evidence.
- **AC-012-021:** Full indexed amount is rounded to `0.01` before proportionality.
- **AC-012-022:** Proportional indexed amount is rounded to two decimals only after multiplying the unrounded ratio.
- **AC-012-023:** `1.35` applies exactly to the rounded proportional indexed per-grant amount, followed by per-grant two-decimal rounding.
- **AC-012-024:** `grant_impact_multiplier = 1.35` is consumed from accepted parameter context with identity and fails closed when absent or incompatible.
- **AC-012-025:** Every grant is independently processed and its final rounded offset is produced before aggregation.
- **AC-012-026:** Multiple grants remain separate records and are not silently consolidated, deduplicated, or merged.
- **AC-012-027:** Actual capitalizations retain separate records, snapshots, and effects and receive none of the grant formula steps.
- **AC-012-028:** M06 output is not a grant, capitalization, historical prior-use fact, or PKG-012 dependency.
- **AC-012-029:** M08C CRUD uses the exact six-field direct-input contract and every valid current grant participates without an accepted-for-use step.
- **AC-012-030:** Removed grants affect only future calculations; historical saved-run snapshots remain immutable.
- **AC-012-031:** Saved runs preserve the complete per-grant and aggregate reproducibility envelope, versions, timestamp, and parameter identity.
- **AC-012-032:** The M08A handoff contains aggregate offset, deterministic per-grant breakdown, complete evidence, and no competing remaining-exempt-capital result.
- **AC-012-033:** Same-client enforcement and foreign/missing anti-leakage cover CRUD, calculation, saved runs, results, handoff, and CBS evidence.
- **AC-012-034:** Caller input cannot forge client ownership, calculation results, CBS evidence identity, timestamp, or snapshot fingerprint.
- **AC-012-035:** Frontend reads and mutations reject stale A-to-B and A-to-B-to-A success, error, rejection, and `finally` effects.
- **AC-012-036:** Additive migration preserves legacy rows without inferred backfill and prevents incomplete legacy rows from entering new authoritative calculations.
- **AC-012-037:** Focused regression evidence proves exact-15 inclusion and rejects the divergent work-days/window-days ratio.
- **AC-012-038:** Golden behavior evidence covers all 17 required cases and the supported `100000 * 0.5 * 1.35 = 67500.00` checkpoint sequence.
- **AC-012-039:** No output claims professional truth certification, tax authority beyond the locked formula, production readiness, or V1/V2 parity.

## NAC-012 Catalogue

- **NAC-012-001:** Prior-withdrawal record, status, formula, or discovery workflow.
- **NAC-012-002:** Prior-fixation status, discovery, evidence resolution, or ambiguity workflow.
- **NAC-012-003:** M07 prior-use manifest, resolver, candidate, or approval lifecycle for direct grant input.
- **NAC-012-004:** Client declaration or evidence-sufficiency machinery for the exact six-field record.
- **NAC-012-005:** Treating zero grant records as unknown, not collected, missing evidence, or unresolved.
- **NAC-012-006:** Source ranking, reliability scoring, or system judgment of professional sufficiency.
- **NAC-012-007:** Automatic Form 161/161D interpretation or document presence treated as a calculation fact.
- **NAC-012-008:** User-entered indexed amount presented as a CBS result.
- **NAC-012-009:** Caller-forged CBS request, response, evidence identity, authority, or currentness.
- **NAC-012-010:** Nominal, cached, estimated, asserted, hard-coded, or manual fallback presented as authoritative CBS indexation.
- **NAC-012-011:** M06 result treated as a grant, capitalization, or historical prior-use fact.
- **NAC-012-012:** A duplicate grant truth source or silent grant/capitalization double counting.
- **NAC-012-013:** Automatic consolidation, deduplication, or merging of grant records by business metadata.
- **NAC-012-014:** Exclusion of a grant at exactly 15 years.
- **NAC-012-015:** Calendar-cutoff replacement for the exact year/month/day 15-year difference formula.
- **NAC-012-016:** `work_days / days_in_32_year_window` replacing overlap/full-employment ratio.
- **NAC-012-017:** Inclusive endpoint day, calendar-year substitution, or a 32-year window other than `11,688` days.
- **NAC-012-018:** Ratio rounding before monetary multiplication.
- **NAC-012-019:** Applying `1.35` before proportionality, directly to nominal/full indexed amount, or to an aggregate.
- **NAC-012-020:** Aggregation before per-grant rounding.
- **NAC-012-021:** Hidden/default multiplier or claim of unsupported annual multiplier variability.
- **NAC-012-022:** M08B authority expansion or replacement of accepted parameter-set provenance.
- **NAC-012-023:** Mutation or redesign of actual-capitalization persistence.
- **NAC-012-024:** Mutation of historical saved-run input, CBS evidence, ratio, offset, or result.
- **NAC-012-025:** Caller-forged client ownership, final result, timestamp, or fingerprint.
- **NAC-012-026:** Foreign-client existence disclosure or cross-client association.
- **NAC-012-027:** M08E or formal 161D output behavior.
- **NAC-012-028:** M09-M14, scenario expansion, recommendation, or report behavior.
- **NAC-012-029:** Production-readiness or full V1/V2 parity claim.
- **NAC-012-030:** Change to frozen `02M`.

## Verification Matrix

| Area | Required evidence |
|---|---|
| Record contract | Field-level API, persistence, and frontend tests for exactly six business facts plus server `grant_id` |
| Empty and amount semantics | Zero collection, explicit zero, negative, malformed, and non-finite tests |
| 15-year rule | Before, exactly-at, and after-boundary tests using the locked difference formula |
| 32-year ratio | Shorter, exact, longer, partial, outside, post-eligibility, leap-date, and no-inclusive-day cases |
| CBS | Exact request mapping, raw/rounded separation, zero bypass, typed failure, anti-forgery, and no fallback |
| Monetary sequence | Checkpoint assertions for indexed, proportional, multiplier, per-grant, and aggregate amounts |
| Multiplier | Accepted parameter identity, exact `1.35`, missing/incompatible fail-closed behavior |
| Multiple grants | Independent processing, no merging, rounded-per-grant aggregation, deterministic order |
| Separation | Actual capitalization and M06 negative-boundary tests |
| Saved runs | Complete immutable snapshot, reproducibility, later-edit isolation, formula/contract version |
| M08A handoff | Exact aggregate and per-grant evidence without a second remaining-capital result |
| Client isolation | Same-client persistence and API tests plus missing/foreign indistinguishability |
| Frontend ownership | Deterministic A-to-B and A-to-B-to-A success/error/rejection/finally tests |
| Migration | Upgrade, downgrade, re-upgrade, legacy preservation, no inferred backfill, one Alembic head |
| Regression | PKG-002 CBS, parameter context, existing fixation saved runs, and actual-capitalization behavior |
| Scope | Changed-file audit, excluded-domain guards, compile/build, and `git diff --check` |

## Deferred and Explicitly Excluded Scope

PKG-012 excludes:

- prior withdrawals and prior fixation;
- an M07 prior-use resolver or document truth-resolution workflow;
- source ranking or separate client-declaration evidence workflow;
- actual-capitalization redesign;
- M06 dependency;
- M08E and formal 161D output;
- M09-M14;
- scenario-engine expansion, recommendations, and reports;
- production-readiness and V1/V2 full-parity claims; and
- any change to `02M`.

Legacy migration mechanics, repository naming choices, exact API paths, physical table names, and detailed UI composition remain bounded implementation-design matters. They may not change the contracts in this definition.

## Authorization Boundary

This document is a final definition candidate only.

- PKG-012 is not accepted by this document.
- PKG-012 implementation is `NOT_AUTHORIZED`.
- Migration creation or execution is `NOT_AUTHORIZED`.
- Production code and implementation tests are `NOT_AUTHORIZED`.
- M08E remains excluded from the first stage.
- M09-M14 remain blocked.
- `02M` remains frozen.
- The next package remains `NOT_AUTHORIZED`.

PKG_012_DEFINITION_PROPOSED_FOR_ACCEPTANCE
