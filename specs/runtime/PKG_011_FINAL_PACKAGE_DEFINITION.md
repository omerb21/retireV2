# PKG-011 — M06 First-Stage Explicit Pension/Capital Conversion Foundation

## Package Identity

| Field | Value |
|---|---|
| Package | `PKG-011` |
| Title | `M06 First-Stage Explicit Pension/Capital Conversion Foundation` |
| Module | `M06` |
| Definition status | `PROPOSED_FOR_ACCEPTANCE` |
| Product outcome | Explicit, source-linked, immutable first-stage pension/capital conversions for two bounded modes |
| Persistence | `ADDITIVE_MIGRATION_REQUIRED` |
| Implementation | `NOT_AUTHORIZED` |
| Migration creation/execution | `NOT_AUTHORIZED` |
| Authoritative base master | `596b353dbaabae82d0c278dff02d04083f90b94a` |

## Locked Professional Decisions

| Decision | Locked answer | Definition consequence | Remaining ambiguity |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| M06-D01                                                        | Only `pension_fund` and `insurance_policy`; only current M05 `contribution_component`       | Exact fail-closed allowlist; unsupported families, components, mixed/unresolved classification, current-employer-related, and restricted inputs produce no authoritative result | None |
| M06-D02                                                        | Explicit source-linked documentary or planner-declared coefficient only                     | No default, lookup, inference, V1 `200.0`, or caller authority flag; planner declaration always requires review                                                                 | None |
| M06-D03                                                        | Inclusive documented period, or explicit planner applicability declaration with warning     | Future/expired evidence blocks; undocumented applicability cannot silently resolve                                                                                              | None |
| M06-D04                                                        | Decimal-only calculation; raw authority preserved; display uses two-decimal `ROUND_HALF_UP` | JSON coefficient is a canonical decimal string; no float path; exact-result representation avoids fixed-scale loss                                                              | None |
| M06-D05                                                        | Explicit zero is valid                                                                      | Zero produces zero if all other gates pass; missing and negative input block                                                                                                    | None |
| M06-D06                                                        | No first-stage conservation/residual contract                                               | No tolerance, residual formula, conservation warning, or reuse of M05 `0.50 ILS`                                                                                                | None |
| M06-D07                                                        | Monthly input only from same-chain M02 `declared_monthly_pension_amount`                    | M01 known pension is excluded; no synchronization, copying, or inference                                                                                                        | None |

No locked decision contradicts an accepted M01-M05 contract.

## Final predecessor contract

PKG-011 consumes M01-M05 as read-only authority. It must not reproduce, reinterpret, or replace their business logic.

An input is admissible only when all conditions below are true at the authoritative operation and again during downstream-eligibility reads:

1. Client ownership:
   - All references resolve under the route client.
   - Missing and foreign IDs have indistinguishable public behavior.
   - No cross-client provider, account, intake, review, classification, ledger, component, or coefficient evidence may enter the conversion.
2. M01:
   - The case is mutation-eligible under the accepted PKG-010 predicate.
   - Allowed effective states are `draft`, `intake`, `analysis`, `review`, and `delivered`.
   - `archived` is readable but cannot start, resolve, review, correct, or supersede an M06 conversion.
3. M02:
   - The intake is a same-client manual intake.
   - `target_kind = manual_record_review`.
   - `lifecycle_status = accepted_for_review`.
   - Provider identity is exact `declared_provider_name`.
   - Account identity is exact `declared_account_reference`.
   - The relevant statement/source date exists.
   - For monthly-to-capital mode, `declared_monthly_pension_amount` exists in this exact intake.
4. M03:
   - The current controlling revision is `accepted`.
   - Current read-time downstream evidence eligibility is true.
   - The revision, decision, intake, and applicable provenance are internally consistent.
5. M04:
   - The current unique leaf is explicitly accepted and resolved.
   - Current read-time M05 eligibility remains true.
   - Product family is exactly `pension_fund` or `insurance_policy`.
   - Aggregate interpretation is not `mixed` or `unresolved`.
   - `capital_asset`, unsupported family, current-employer-related input, and proven blocked/restricted input are excluded.
   - No V1 heuristic may broaden the classification.
6. M05:
   - Exactly one current authoritative ledger subject and candidate exist.
   - The current revision is `reconciled` or `warning_reviewed`.
   - `eligible_for_m06` is true at read time.
   - ILS confirmation remains valid for the exact source snapshot.
   - Provider, account, statement date, component mappings, source/effective values, warning dispositions, and provenance remain complete.
   - A selected effective `contribution_component` identity exists.
   - The component is current, included, mapped one-to-one, and not superseded.
   - The selected amount is the exact current effective scale-2 Decimal value.
   - No candidate tie, chain inconsistency, invalid mapping, or unresolved mandatory warning exists.
7. Required snapshot evidence:
   - M02 intake ID and source-fact identity.
   - M03 current accepted revision ID and relevant provenance digest.
   - M04 current accepted revision ID, classification values, rule/catalogue version, and input snapshot digest.
   - M05 subject ID, current revision ID, candidate ID, selected evidence identity, monetary source snapshot digest, mapping digest, product context, warning snapshot, warning dispositions, currency confirmation, statement date, evaluation date, and stale result.

Predecessor IDs and digests are copied into the immutable M06 manifest as observed snapshots. They remain references to predecessor authority, not M06-authored replacements.

## Final supported conversion matrix

| Mode | Formula | Authoritative amount | Required subject anchor | Output unit |
| ----------------------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------- |
| `balance_to_monthly_pension`                                      | `balance / coefficient`         | Current M05 effective value of the selected eligible `contribution_component` | Exact M05 subject, revision, candidate, component/evidence identity                             | ILS per month          |
| `monthly_pension_to_capital_equivalent`                           | `monthly_pension * coefficient` | Same-chain M02 `declared_monthly_pension_amount`                              | Exact M02 intake plus the same eligible M05 subject and selected contribution-component context | ILS capital equivalent |

Rules:

- These are the only formula modes.
- Mode is part of conversion-subject identity.
- One economic account may therefore have separate immutable conversion chains for the two modes.
- Monthly mode does not read `M01 known_monthly_pension_amount`.
- Monthly mode does not copy its amount into M05.
- Balance mode does not use M02 total balance or monthly pension as a substitute.
- No generic formula expression or caller-selected operator is accepted.

## Subject identity

The server generates one immutable semantic subject identity from:

- `client_id`;
- exact M05 ledger `subject_id`;
- digest of exact provider identity;
- digest of exact account identity;
- accepted M04 product family and product-context identity;
- conversion mode;
- authoritative input identity:
  - M05 selected `contribution_component.evidence_identity` for balance mode;
  - M02 intake ID plus fixed field identity `declared_monthly_pension_amount` for monthly mode.

Revision IDs are not part of the semantic subject identity. They are captured by each immutable conversion revision. This allows later predecessor revalidation or coefficient correction to append history without creating an accidental second subject.

The semantic identity prevents collisions between:

- clients;
- providers;
- accounts;
- components;
- M02 monthly-pension facts;
- product contexts;
- conversion modes.

Only one subject may exist per semantic tuple. Concurrent duplicate starts permit one winner. The loser receives `conversion_subject_conflict` and creates no residue.

## Coefficient evidence contract

### Documentary authority

Required intent and resolved evidence:

- authority class `documentary`;
- coefficient as an exact canonical Decimal string;
- same-client accepted source/provenance reference;
- exact source locator or sufficiently precise source note;
- provider and product applicability context;
- relevant conversion mode and coefficient unit semantics;
- effective-from and effective-to when documented;
- source date, version, and issuer/provider metadata when present;
- age, gender, pension option, guarantee period, survivor option, or other dimensions only when actually used;
- server-resolved actor;
- server timestamp.

A documentary coefficient source must be current and accepted under the applicable M03 evidence contract. A manual technical reference is not documentary evidence.

Documentary evidence may create `resolved` when every gate passes and no mandatory warning exists.

### Planner-declared authority

Required intent and resolved evidence:

- authority class `planner_declared`;
- coefficient as an exact canonical Decimal string;
- explicit `source_note` and reason;
- exact provider/product context;
- conversion mode and coefficient unit semantics;
- explicit applicability declaration for the relevant input date;
- each age, gender, option, guarantee, or survivor dimension used;
- server-resolved actor;
- server timestamp.

It must be labelled `planner_declared`, never externally validated or documentary.

It always creates:

`planner_declared_coefficient_authority`

Where no documentary effective period exists, it also creates:

`coefficient_applicability_not_documented`

It cannot create plain `resolved`.

### Server-owned evidence

The server owns:

- coefficient evidence ID;
- client and subject ownership;
- authority-class validation;
- resolved provenance identity;
- provider/account/product linkage;
- formula/unit identity;
- actor and timestamp;
- applicability evaluation;
- warning classification;
- evidence digest;
- predecessor and successor links.

The caller cannot supply an authoritative boolean, acceptance status, warning classification, provenance digest, actor, timestamp, or trusted wrapper.

No coefficient catalogue, automatic table, provider lookup, or global coefficient resolver is introduced.

## Numeric contract

1. Authoritative arithmetic uses Decimal or exact integer/rational operations derived from Decimals. Binary float is prohibited.
2. API coefficient input:
   - Must be a JSON string, not a JSON number.
   - Must be a plain base-10 decimal representation.
   - Leading or trailing whitespace, commas, exponent notation, booleans, `NaN`, `Infinity`, and `-Infinity` are rejected.
   - The exact accepted string and its Decimal exponent/precision are preserved.
3. Coefficient:
   - Must be present.
   - Must be finite.
   - Must be greater than zero.
   - Must not be truncated or normalized to scale 2.
   - Trailing decimal precision supplied in accepted evidence is retained.
4. Monetary input:
   - Comes only from the authoritative predecessor.
   - Scale and precision are not caller-authored.
   - Explicit zero is valid.
   - Missing and negative input block.
   - Zero must not be detected using truthiness.
5. Raw result:
   - Multiplication is persisted as its exact canonical Decimal result.
   - Division may be non-terminating. Therefore a fixed-scale `Numeric` alone cannot satisfy reproducibility.
   - For division, the authoritative raw result is persisted as an exact ratio containing the canonical Decimal numerator and denominator plus formula identity.
   - Any stored decimal expansion is supporting presentation evidence only and must include its precision and rounding metadata.
   - The exact ratio or exact multiplication result, together with the persisted operands, reproduces the authoritative raw result without hidden truncation.
6. Displayed result:
   - Derived from the exact raw representation.
   - Quantized to `0.01`.
   - Uses `ROUND_HALF_UP`.
   - Is stored separately from the raw result.
   - Is not described as proven V1 behavior.
7. Range and persistence:
   - Accepted coefficient precision must be persistable without loss.
   - No fixed `Numeric(p,s)` may be used if it truncates an accepted coefficient or raw result.
   - A value that cannot be represented under declared storage/resource limits fails before persistence with `numeric_value_out_of_supported_range`.
   - Overflow, database conversion error, or resource-limit rejection must not become HTTP 500, partial persistence, infinity, or fallback.

## Date/applicability contract

| Mode | Relevant input date |
| --------------------------------------- | --------------------------------------------------------------------------------- |
| `balance_to_monthly_pension`            | M05 authoritative source `statement_date` captured by the current ledger revision |
| `monthly_pension_to_capital_equivalent` | Same-chain M02 `declared_statement_date`                                          |

Rules:

- Dates are date-only ISO calendar values.
- No M08 eligibility date is read or inferred.
- Effective-from and effective-to are inclusive.
- Either boundary may be open.
- `effective_from > effective_to` blocks.
- A relevant date before effective-from or after effective-to blocks.
- Missing relevant date blocks.
- Explicitly future or expired coefficient evidence produces no result.
- If no documentary applicability period exists, an exact planner declaration that the coefficient applies to the relevant date is required.
- That path creates `coefficient_applicability_not_documented`.
- Absence of both documentary period and planner declaration blocks.
- M05 `stale_warning` is copied as informational upstream evidence only. It is not converted into coefficient staleness, professional invalidity, or a new lifecycle state.

## Lifecycle matrix

Persisted states are exactly:

- `draft`
- `resolved`
- `warning_reviewed`
- `blocked`
- `superseded`

| Current state | Action | Successor | Conditions |
| -------------------------------------- | --------------------- | ------------------ | ---------------------------------------------------- |
| none                                   | `start`               | `draft`            | Subject and client context safely resolve            |
| `draft`                                | `resolve`             | `resolved`         | All gates pass and mandatory-warning set is empty    |
| `draft`                                | `resolve`             | `draft` successor  | Calculation succeeds but mandatory warnings exist    |
| `draft`                                | `resolve`             | `blocked`          | Stable blocking reasons exist; no raw/display result |
| `draft`                                | `review_warnings`     | `warning_reviewed` | Exact current mandatory-warning set is disposed      |
| `draft`                                | `correct_coefficient` | `draft` successor  | Complete replacement coefficient evidence supplied   |
| `draft`                                | `supersede`           | `superseded`       | Explicit action and reason                           |
| `resolved`                             | `correct_coefficient` | `draft` successor  | Previous result remains immutable                    |
| `resolved`                             | `supersede`           | `superseded`       | Explicit action and reason                           |
| `warning_reviewed`                     | `correct_coefficient` | `draft` successor  | Previous result and disposition remain immutable     |
| `warning_reviewed`                     | `supersede`           | `superseded`       | Explicit action and reason                           |
| `blocked`                              | `correct_coefficient` | `draft` successor  | Correction can address the blocker                   |
| `blocked`                              | `supersede`           | `superseded`       | Explicit action and reason                           |
| `superseded`                           | any mutation          | none               | Prohibited                                           |

`blocked` is a persisted immutable revision only when the server has safely resolved the same-client subject and authoritative intent. Malformed requests, missing/foreign IDs, or ownership failures before safe subject resolution create no M06 record.

A blocked revision contains validation evidence and reason codes, but no raw result, displayed result, or success audit evidence.

Every successful action appends one complete immutable successor. No row is updated in place.

## Warning catalogue

### Mandatory warnings

| Code | Trigger | Disposition | Downstream consequence |
| -------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------ |
| `planner_declared_coefficient_authority`     | Coefficient authority class is `planner_declared`                                        | Exact-set review required | Draft cannot become authoritative until reviewed |
| `coefficient_applicability_not_documented`   | No documentary applicability period exists and planner applicability declaration is used | Exact-set review required | Draft cannot become authoritative until reviewed |

### Informational inherited warnings

| Code | Trigger | Disposition | Downstream consequence |
| -------------------------------------------- | ------------------------------- | ----------- | ------------------------------------------------------ |
| `stale_warning`                              | Present in current M05 evidence | None in M06 | Preserved as information; does not independently block |
| `newer_ineligible_candidate_exists`          | Present in current M05 evidence | None in M06 | Preserved as information; does not independently block |

No other first-stage M06 warning is authorized. In particular, there is no rounding, mismatch, residual, conservation, source-ranking, or recommendation warning.

## Blocking reason catalogue

| Code | Trigger |
| -------------------------------------- | -------------------------------------------------------------------------- |
| `archived_case`                        | M01 is archived or otherwise mutation-ineligible                           |
| `predecessor_not_current`              | A referenced M02-M05 revision is not current                               |
| `m02_intake_ineligible`                | M02 is not same-chain manual `accepted_for_review`                         |
| `m03_not_accepted`                     | Current M03 revision is not accepted                                       |
| `m03_ineligible`                       | M03 downstream evidence eligibility is false                               |
| `m04_not_accepted`                     | Current M04 leaf is not accepted                                           |
| `m04_not_resolved`                     | Current M04 leaf is unresolved                                             |
| `unsupported_product_family`           | Product family is outside the exact allowlist                              |
| `unsupported_aggregate_interpretation` | Aggregate is `mixed` or `unresolved`                                       |
| `unsupported_component_kind`           | Component is not `contribution_component`                                  |
| `current_employer_related_unsupported` | Input is marked current-employer-related                                   |
| `blocked_or_restricted_context`        | Existing predecessor evidence establishes blocked/restricted context       |
| `m05_not_eligible`                     | Read-time `eligible_for_m06` is false                                      |
| `m05_state_invalid`                    | Current M05 state is not `reconciled` or `warning_reviewed`                |
| `input_identity_invalid`               | Required M02/M05 input identity is missing, duplicate, or inconsistent     |
| `input_amount_missing`                 | Authoritative amount is absent                                             |
| `input_amount_negative`                | Authoritative amount is below zero                                         |
| `coefficient_missing`                  | No coefficient supplied                                                    |
| `coefficient_zero`                     | Coefficient equals zero                                                    |
| `coefficient_negative`                 | Coefficient is below zero                                                  |
| `coefficient_invalid`                  | Coefficient is malformed, non-finite, non-Decimal, or non-canonical        |
| `numeric_value_out_of_supported_range` | Exact value cannot be processed or stored without loss                     |
| `coefficient_provenance_missing`       | Required documentary or planner provenance is incomplete                   |
| `coefficient_context_mismatch`         | Provider, product, mode, unit, or dimension context does not match         |
| `coefficient_applicability_missing`    | Neither documented applicability nor planner declaration exists            |
| `coefficient_date_contradiction`       | Invalid period or relevant date outside the period                         |
| `relevant_source_date_missing`         | Required mode-specific date is absent                                      |
| `reference_unavailable`                | Public missing/foreign reference result                                    |
| `predecessor_provenance_corrupt`       | IDs, digests, source snapshots, mappings, or chain evidence conflict       |
| `warning_disposition_invalid`          | Warning review set, revision, or evidence is invalid                       |
| `conversion_revision_stale`            | Mutation does not target the current leaf                                  |
| `conversion_chain_inconsistent`        | Revision sequence, predecessor, leaf, or subject invariant fails           |
| `conversion_subject_conflict`          | Concurrent or duplicate semantic-subject creation loses                    |
| `formula_contract_invalid`             | Mode, formula, input unit, coefficient semantics, or output unit conflicts |

For anti-leakage, foreign and missing identifiers expose the same public status, code `reference_unavailable`, and message `referenced conversion evidence is unavailable`. A more detailed internal audit reason may be recorded only if it cannot influence the public response or timing branch.

## Warning review contract

A warning review request contains only:

- current conversion revision intent;
- exact mandatory-warning IDs shown for that revision;
- bounded reason code;
- explanation;
- explicit confirmation.

The server independently:

- resolves the current leaf;
- recomputes the warning set;
- verifies client and subject ownership;
- verifies predecessor currency and authority;
- verifies coefficient evidence and applicability;
- supplies actor and timestamp.

The submitted set must equal the server-computed current mandatory set exactly. Missing, extra, unknown, informational, stale, or caller-invented warning IDs fail with `warning_disposition_invalid`.

A successful review appends a `warning_reviewed` successor containing the exact reviewed warning snapshot and disposition evidence. It does not mutate the draft.

Review is prohibited for:

- a stale revision;
- a superseded revision;
- an empty mandatory-warning set;
- a changed coefficient;
- a changed predecessor;
- a changed warning set.

## Coefficient correction contract

`correct_coefficient` replaces the complete coefficient evidence envelope. Partial patching is prohibited.

A successful correction:

- targets the current non-superseded leaf;
- appends a complete `draft` successor;
- assigns a new server evidence identity and digest;
- reruns all provenance, context, applicability, numeric, and warning validation;
- clears no prior evidence;
- creates no authoritative result until a new resolve/review sequence succeeds.

It must not change:

- any M01-M05 row or source fact;
- M02 monthly-pension amount;
- M04 classification;
- M05 effective value or component mapping;
- prior M06 revision;
- prior coefficient evidence;
- prior result;
- prior warning disposition.

Raw-result, displayed-result, formula, input-value, or output overrides are prohibited.

## Calculation/provenance manifest

Each resolved, warning-bearing, warning-reviewed, or blocked revision stores a server-owned typed and versioned manifest containing:

- manifest schema version;
- calculation contract version;
- subject ID and revision ID;
- predecessor revision and sequence;
- client ID;
- conversion mode;
- formula ID:
  - `m06.balance_to_monthly_pension.v1`;
  - `m06.monthly_pension_to_capital_equivalent.v1`;
- input identity and evidence identity;
- exact input Decimal text;
- input unit;
- relevant input date;
- coefficient evidence ID;
- exact coefficient Decimal text and precision;
- coefficient authority class;
- coefficient provenance snapshot;
- source locator/note;
- provider/product/account context;
- age/gender/options dimensions actually used;
- effective period or planner applicability declaration;
- M02 intake ID and source-fact identity;
- M03 current accepted revision ID and provenance digest;
- M04 current accepted revision ID, product family, aggregate interpretation, catalogue/rule version, and snapshot digest;
- M05 subject, revision, candidate, selected component/evidence identity, mapping digest, monetary source digest, currency confirmation, evaluation date, and stale evidence;
- exact raw-result representation;
- rounding rule `ROUND_HALF_UP`;
- displayed two-decimal result;
- exact mandatory-warning set;
- inherited informational warnings;
- blocking reasons when applicable;
- actor;
- timestamp;
- manifest fingerprint.

Blocked manifests contain no raw or displayed result.

The manifest fingerprint is deterministic and order-independent for semantically unordered warning/provenance collections. Any material input, coefficient, source, version, mode, formula, warning, or result change changes the fingerprint.

## Read-time predecessor revalidation

Historical M06 revisions remain immutable and readable.

Read-time current eligibility compares the manifest against current authoritative predecessor state:

| Later change | Historical record | Current downstream eligibility |
| ----------------------------------------------------------- | ----------------------------- | ---------------------------------------- |
| M03 controlling revision changes                            | Unchanged and readable        | False                                    |
| M04 current leaf changes                                    | Unchanged and readable        | False                                    |
| M05 current revision changes                                | Unchanged and readable        | False                                    |
| M05 becomes blocked, superseded, or ineligible              | Unchanged and readable        | False                                    |
| Coefficient is corrected in M06                             | Old evidence/result unchanged | False for old leaf; new draft is current |
| Current M06 revision is explicitly superseded               | Unchanged and readable        | False                                    |

Revalidation does not auto-mutate an old state to blocked or superseded. To regain authority, the user must create an allowed new draft successor using current predecessors and then resolve it again.

## Downstream technical eligibility

Technical eligibility is true only when:

- the requested conversion is the unique current leaf;
- state is `resolved` or `warning_reviewed`;
- no mandatory warning remains undisposed;
- subject and revision chain are valid;
- M01 remains mutation-eligible;
- M02 remains current and accepted for review;
- M03 remains current, accepted, and eligible;
- M04 remains current, accepted, resolved, and within the PKG-011 allowlist;
- M05 remains current and `eligible_for_m06`;
- the exact input identity and predecessor digests still match;
- coefficient evidence remains current inside the M06 chain;
- manifest and result fingerprints remain valid.

Stable false-reason vocabulary:

- `conversion_not_current`;
- `conversion_draft`;
- `conversion_blocked`;
- `conversion_superseded`;
- `warning_not_reviewed`;
- `m01_case_ineligible`;
- `m02_predecessor_changed`;
- `m03_predecessor_changed`;
- `m03_predecessor_ineligible`;
- `m04_predecessor_changed`;
- `m04_predecessor_ineligible`;
- `m05_predecessor_changed`;
- `m05_predecessor_ineligible`;
- `coefficient_evidence_replaced`;
- `manifest_integrity_invalid`;
- `conversion_chain_inconsistent`;
- `provenance_invalid`.

This eligibility means only that the immutable M06 conversion satisfies PKG-011's technical contract. It does not authorize M07, M08, M09, tax, fixation, withdrawal, recommendations, or reports.

## API business surface

All operations are client-scoped:

- list currently eligible M06 input candidates;
- list conversion subjects;
- get current conversion detail;
- get immutable conversion history;
- start a conversion;
- validate and resolve current draft;
- review the exact warning set;
- correct/replace coefficient evidence;
- explicitly supersede current conversion;
- get derived downstream technical eligibility.

Strict mutation schemas accept intent only. They reject fields such as:

- client ownership in body;
- predecessor state or eligibility;
- input amount;
- provider/account/product snapshots;
- actor or timestamp;
- authority flags;
- warning classification;
- calculation result;
- displayed result;
- fingerprint;
- revision sequence;
- current-leaf pointer.

Missing and foreign IDs return indistinguishable status, body, and practical code path. No list, detail, history, validation, error, or timing response may reveal a foreign record.

## Frontend workflow boundary

The first-stage planner journey is:

1. Open M06 for one route client.
2. View only server-returned eligible inputs.
3. Select a supported subject and one of the two modes.
4. Review the authoritative source amount and provenance.
5. Enter a coefficient as a decimal string.
6. Attach documentary provenance or make a planner declaration.
7. Review date and applicability evidence.
8. See the exact formula and units before resolution.
9. Resolve.
10. Dispose the exact mandatory-warning set where required.
11. Inspect raw result, displayed result, coefficient authority, and provenance.
12. Inspect immutable history and technical eligibility.

The UI must not provide:

- coefficient lookup or recommendation;
- default `200.0`;
- generic formula editor;
- raw/display result editor;
- source-value editor;
- scenario controls;
- tax/fixation controls.

Every read and mutation captures:

- route `clientId`;
- monotonic route-context generation;
- subject ID where applicable;
- current revision intent.

Success, rejection, structured error, refresh, and `finally` state updates require all captured ownership values to remain current. Deterministic A->B and A->B->A deferred-promise tests are required.

## Persistence concepts

An additive Alembic migration is required.

Minimum persistence concepts:

1. M06 conversion subject.
2. Immutable conversion revision.
3. Immutable coefficient evidence snapshot.
4. Immutable calculation/provenance manifest.
5. Immutable warning disposition.
6. Explicit predecessor/successor and supersession evidence.

Required invariants:

- stable server-generated IDs;
- explicit client ownership;
- unique semantic subject identity;
- unique revision sequence per subject;
- one child per predecessor;
- deterministic unique current leaf;
- same-client composite integrity;
- coefficient evidence owned by one revision;
- one manifest per revision where applicable;
- exact warning-disposition ownership;
- append-only rows;
- no update or delete of accepted history;
- no M01-M05 mutation or backfill.

No historical M01-M05 conversion record is inferred or backfilled.

## Concurrency contract

| Race | Required behavior |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Two starts for same semantic subject/mode | One subject and draft winner; loser gets `conversion_subject_conflict`; no orphan rows          |
| Two resolves from same draft              | One successor winner; loser gets `conversion_revision_stale`; no partial manifest               |
| Warning review vs coefficient correction  | One child wins; loser is stale; reviewed and corrected evidence cannot coexist in one successor |
| Coefficient correction vs supersede       | One child wins; loser creates no row                                                            |
| Duplicate revision sequence               | Database uniqueness failure handled as domain conflict, never last-write-wins                   |
| Two children for one predecessor          | Database/service invariant allows one winner only                                               |
| Failure during child persistence          | Entire successor, coefficient snapshot, manifest, and disposition roll back atomically          |

## AC-011 catalogue

- **AC-011-001:** Every candidate and authoritative operation revalidates same-client M01-M05 ownership and current authority.
- **AC-011-002:** M01 eligibility matches the accepted non-archived PKG-010 predicate.
- **AC-011-003:** Only M02 manual `accepted_for_review` intake with exact provider/account identity enters PKG-011.
- **AC-011-004:** Current accepted M03 and current accepted/resolved M04 authority are required and captured.
- **AC-011-005:** Current M05 revision must be `reconciled` or `warning_reviewed` and `eligible_for_m06`.
- **AC-011-006:** Product family allowlist is exactly `pension_fund` and `insurance_policy`.
- **AC-011-007:** The selected M05 monetary component is exactly the current effective `contribution_component`.
- **AC-011-008:** Mixed, unresolved, current-employer-related, blocked/restricted, and unsupported contexts fail closed.
- **AC-011-009:** Conversion modes are exactly the two specified formula IDs.
- **AC-011-010:** Balance mode consumes only the selected M05 effective contribution value.
- **AC-011-011:** Monthly mode consumes only same-chain M02 `declared_monthly_pension_amount`.
- **AC-011-012:** Mode and exact input identity form part of the immutable semantic subject identity.
- **AC-011-013:** Documentary coefficient evidence requires complete accepted provenance, locator, context, applicability, actor, and timestamp.
- **AC-011-014:** Planner-declared coefficient evidence requires complete declaration context and creates its mandatory authority warning.
- **AC-011-015:** No coefficient fallback, lookup, inference, substitution, or caller authority flag exists.
- **AC-011-016:** Coefficient API input is an exact canonical Decimal string and all authoritative arithmetic avoids float.
- **AC-011-017:** Positive finite nonzero coefficient precision is retained without scale-2 truncation.
- **AC-011-018:** Explicit monetary zero resolves to exact zero when all other gates pass.
- **AC-011-019:** Missing and negative amounts and zero/negative/invalid coefficients produce stable blocking reasons.
- **AC-011-020:** Division and multiplication produce reproducible exact raw-result representations.
- **AC-011-021:** Display result is separately derived to two decimals using `ROUND_HALF_UP`.
- **AC-011-022:** Relevant dates, inclusive effective ranges, open boundaries, and contradictions follow the exact date contract.
- **AC-011-023:** Undocumented applicability requires planner declaration and mandatory warning review.
- **AC-011-024:** M05 stale evidence remains inherited informational evidence only.
- **AC-011-025:** Lifecycle transitions create complete append-only immutable successors with no update-in-place.
- **AC-011-026:** Blocking after safe subject resolution creates a blocked revision with no calculation result.
- **AC-011-027:** Warning review is bound to the exact current revision and exact recomputed mandatory-warning set.
- **AC-011-028:** Coefficient correction appends a draft successor and leaves all prior evidence and results unchanged.
- **AC-011-029:** Each calculation manifest contains all input, coefficient, predecessor, formula, result, warning, actor, version, and digest evidence required for reproduction.
- **AC-011-030:** Material manifest changes alter its fingerprint; unordered evidence ordering alone does not.
- **AC-011-031:** Read-time revalidation removes current downstream eligibility when M03, M04, M05, or coefficient authority changes.
- **AC-011-032:** Historical results remain readable and immutable after predecessor changes or supersession.
- **AC-011-033:** Only current `resolved` and fully `warning_reviewed` revisions can be technically eligible.
- **AC-011-034:** Missing and foreign IDs have indistinguishable public behavior and produce no cross-client persistence.
- **AC-011-035:** Frontend state and every asynchronous action are guarded by client, generation, subject, and revision ownership.
- **AC-011-036:** Deterministic concurrency tests prove one winner, clean loser, one child per predecessor, and no residue.
- **AC-011-037:** The additive migration creates only M06 persistence, one Alembic head, no backfill, and no M01-M05 mutation.
- **AC-011-038:** SQLite and PostgreSQL-compatible migration evidence proves constraints, upgrade, downgrade, and failure atomicity.
- **AC-011-039:** Focused and full regression evidence proves PKG-010 reconciliation, source/effective separation, M04 authority, and M02/M03 provenance remain unchanged.
- **AC-011-040:** Tests prove exact evidence completeness for documentary, planner-declared, zero, blocked, warning-reviewed, corrected, superseded, and predecessor-invalidated cases.
- **AC-011-041:** No M06 conservation/residual formula, tolerance, or warning exists.
- **AC-011-042:** No package output or eligibility response claims professional truth, tax authority, downstream execution authority, production readiness, or V1/V2 parity.

## NAC-011 catalogue

- **NAC-011-001:** Use of V1 fallback coefficient `200.0`.
- **NAC-011-002:** Automatic coefficient inference, lookup, default, substitution, ranking, or recommendation.
- **NAC-011-003:** Conversion of any product family outside `pension_fund` and `insurance_policy`.
- **NAC-011-004:** Conversion of severance, unknown, capital-asset, unsupported, or unmapped components.
- **NAC-011-005:** Current-employer-related or proven blocked/restricted conversion.
- **NAC-011-006:** Conversion of `mixed` or unresolved aggregate classification.
- **NAC-011-007:** V1 heuristic, name matching, subtype heuristic, or `is_pension_fund()` widening the allowlist.
- **NAC-011-008:** Mutation of any M01-M05 source, lifecycle, classification, review, ledger, mapping, or provenance record.
- **NAC-011-009:** Mutation of the M05 effective value.
- **NAC-011-010:** M06 reclassification of M04 evidence.
- **NAC-011-011:** Mutation, copying, or synchronization of M02 monthly pension.
- **NAC-011-012:** Use of M01 known monthly pension as M06 authority.
- **NAC-011-013:** Generic formula, caller-selected operator, or free-form formula execution.
- **NAC-011-014:** Direct raw-result or displayed-result override.
- **NAC-011-015:** Output editing or treating displayed rounding as source evidence.
- **NAC-011-016:** Anonymous coefficient or coefficient without complete provenance.
- **NAC-011-017:** Caller-authored authority, acceptance, actor, timestamp, provenance digest, warning class, or trusted flag.
- **NAC-011-018:** Caller-forged warning set or warning review against a stale revision.
- **NAC-011-019:** Binary float in parsing, calculation, persistence, comparison, or display derivation.
- **NAC-011-020:** Silent coefficient precision loss or fixed-scale raw-result truncation.
- **NAC-011-021:** Negative monetary input producing a conversion.
- **NAC-011-022:** Treating exact zero as missing, falsey, no-op, or blocked.
- **NAC-011-023:** Silently accepting absent or undocumented applicability.
- **NAC-011-024:** Using an expired or future coefficient to produce a result.
- **NAC-011-025:** Reinterpreting M05 stale evidence as professional invalidity or a coefficient period.
- **NAC-011-026:** Conservation/residual formula, M05 `0.50 ILS` reuse, reverse tolerance, or conservation warning.
- **NAC-011-027:** Cross-client read, write, reference, count, provenance, value, or timing disclosure.
- **NAC-011-028:** A stale predecessor silently remaining downstream-authoritative.
- **NAC-011-029:** Update-in-place, deletion, last-write-wins, divergent children, or mutable history.
- **NAC-011-030:** Partial successor, orphan coefficient evidence, orphan manifest, or partial warning disposition after failure.
- **NAC-011-031:** Tax, fixation, exemption, 161D, commutation-tax, or taxable/exempt allocation behavior.
- **NAC-011-032:** Withdrawal, liquidity, pension-commencement, or historical-capitalization generation.
- **NAC-011-033:** Scenario, recommendation, comparison, report, or planner-advice behavior.
- **NAC-011-034:** M07, M08, M09-M14 implementation or mutation.
- **NAC-011-035:** Change to `02M`.
- **NAC-011-036:** System-maintained coefficient catalogue or external automatic coefficient resolver.
- **NAC-011-037:** Automatic background revalidation that mutates an existing result.
- **NAC-011-038:** Production-readiness, full-M06, legal sufficiency, or V1/V2 parity claim.

## Explicit exclusions

Out of scope:

- All products and components outside D01.
- Any broad old/new pension subtype mapping.
- Automatic coefficient catalogue, lookup, selection, or recommendation.
- M05 reconciliation or correction.
- M04 classification work.
- M03 evidence-review changes.
- M02 source-fact correction.
- M01 pension synchronization.
- Conservation, residual, reverse-conversion tolerance, or mismatch warnings.
- Historical actual capitalizations as generated M06 results.
- Tax, exemption, fixation, formal 161D, taxable/exempt commutation.
- Withdrawal and liquidity decisions.
- Pension commencement decisions.
- Scenarios, comparisons, recommendations, and reports.
- M07, M08, M09-M14 implementation.
- `02M`.
- Authentication or multi-owner approval expansion.
- Production-readiness and V1/V2 parity claims.

The first-stage conservation status is exactly:

`NOT_IMPLEMENTED_NO_AUTHORITATIVE_FIRST_STAGE_CONTRACT`

Excluded products are outside PKG-011's evidence-backed allowlist only. The exclusion is not a general professional finding that they cannot be converted.

PKG_011_DEFINITION_PROPOSED_FOR_ACCEPTANCE
