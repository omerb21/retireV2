# CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_AUTHORITY (RTICB) - Corrected Definition

## 1. Identity, status and governance
- Package: `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_AUTHORITY` (`RTICB`), Class A / Complex Class A.
- Governance: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1.1`.
- Canonical correction base: `b83c6f7259fa88fc96e335022608fda526cb3b97`.
- Artifact status: `DEFINITION_CORRECTION_CANDIDATE`; no Definition Acceptance has occurred.
- Owner decision `OWNER-DECISION-RTICB-001`: previously resolved; no new Owner Decision.
- `IMPLEMENTATION=NOT_AUTHORIZED`; `DOWNSTREAM=NOT_AUTHORIZED`; `PRODUCTION_READINESS=NOT_CLAIMED`.
- This document replaces the older RTISA-direct RTICB draft as a proposed Definition. It is not an acceptance manifest, source-code change or authority over upstream behavior.

## 2. Objective, direct authorities and exclusions
RTICB is a read-only, deterministic *basis comparability* authority, not an amount normalizer or total calculator. It consumes **exactly** two current result authorities: (1) confirmed Retirement Monthly Income Target (RIT), and (2) the accepted `CRTISBA_COLLECTION_RESULT_V1` source-basis collection. **RTISA is not a third direct consumer input**: it is invoked transitively by CRTISBA in the same database snapshot. RTICB neither directly reads RTISA nor uses RTISA `native_income_basis` or `native_price_evidence` as comparison authority. CRTISBA `income_basis`, `price_basis`, `price_reference_date` and their provenance are the only source basis evidence.

The complete source universe is the exact, ordered `source_basis_entries` of the current CRTISBA collection. Do not rediscover, insert, drop, deduplicate, or remap source identities. The target authority remains authoritative for target currency, current confirmation, `income_basis`, `price_basis` and `price_reference_date`.

RTICB never performs GROSS/NET conversion, tax calculation, CPI/indexation, nominal/real conversion, source amount recomputation, monthly equivalent computation, income totals, coverage, gap/surplus, funding, withdrawal, optimization, scenario execution, source admission or professional inference. CRTISBA, RTISA, PTE/Portfolio, Planning and RIT accepted semantics remain unmodified. No persistence, migration, public API, UI or write is created in this package.

## 3. Binding owner decision and matching
- `GROSS` matches `GROSS` and `NET` matches `NET` only. Unequal *known* income bases add `RTICB_INCOME_BASIS_MISMATCH`.
- `NOMINAL_AT_RETIREMENT_TARGET_DATE` matches the same literal; `REAL_AT_REFERENCE_DATE` matches the same literal only when both valid authoritative dates match exactly.
- Unequal known price basis adds `RTICB_PRICE_BASIS_MISMATCH`. Two REAL values with unequal valid dates add `RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH`.
- `UNKNOWN` income or price evidence adds the corresponding `RTICB_INCOME_BASIS_UNKNOWN` or `RTICB_PRICE_BASIS_UNKNOWN`; a valid REAL/null reference for a comparison-eligible source adds `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING` only if such null is allowed by CRTISBA's exact state schema.
- Both unresolved and mismatch reasons are retained; unresolved takes state precedence over normalization. No inference or repair.

## 4. Producer and request admission
The public operation `assess(db: Session, request)` accepts exactly `client_id` (positive integer, excluding bool), `expected_planning_calculation_input_fingerprint` (lowercase sha256) and `expected_retirement_target_date` (canonical ISO date). Requests with extra/missing keys, type or date/hash errors fail before touching the session.

A successful target must have accepted exact RIT schema and fingerprints, matching client/planning/target date, confirmed CURRENT lifecycle, ready state, ILS currency and valid target basis (GROSS/NET, NOMINAL with null date or REAL with non-null canonical date). Do not infer target basis.

CRTISBA must return a structurally valid `CRTISBA_COLLECTION_RESULT_V1` with complete source coverage, exact entry schemas, exact partitions and a recomputable collection result fingerprint. A valid collection with `basis_ready=false` or `basis_readiness_state=NOT_READY` **is still eligible for classification**; lack of professional decisions is not producer corruption. A valid `CRTISBA_BLOCK_NO_RESULT_V1` is a whole-authority fail-closed result. Exceptions are never transformed into blocked results.

Exactly match `client_id`, planning fingerprint and non-null retirement target date across request, target and CRTISBA. A CRTISBA collection with valid null retirement target date cannot be paired with a request specifying a target date and fails cross-authority identity, not comparison. Never silently select stale/preexisting collection evidence.

## 5. Closed collection vocabulary and partitions
Accepted CRTISBA collection keys exactly: `schema_version`, `client_id`, `planning_calculation_input_fingerprint`, `retirement_target_date`, `rtisa_admission_result_fingerprint`, `source_basis_entries`, `partitions`, `blockers`, `basis_readiness_state`, `basis_ready`, `result_fingerprint`. `basis_ready` is precisely equivalent to `basis_readiness_state == READY`. Partitions are exactly `current`, `missing`, `unknown`, `stale`, `invalid`, `upstream_unresolved`, `not_applicable_delegated`, `not_applicable_not_admitted`, `delegation_unresolved`, `delegation_stale`; each contains canonical sorted unique source IDs, all disjoint, with union equal to all entry IDs and entry-to-partition equality. Entries are sorted by Python Unicode code point source_id order; no locale or Unicode normalization.

Accepted entry keys exactly: `schema_version`, `source_id`, `source_kind`, `source_category`, `admission_state`, `rtisa_reason_codes`, `source_version`, `source_fingerprint`, `amount_authority_fingerprint`, `decision_version`, `decision_fingerprint`, `decision_state`, `income_basis`, `income_basis_provenance`, `price_basis`, `price_reference_date`, `price_basis_provenance`, `blockers`. Source kind is PENSION or RECURRING_INCOME; admission INCLUDED, EXCLUDED or UNRESOLVED. All exact shapes, states, amount/source/version/decision relationships, reason vocabularies and nullability follow the **accepted CRTISBA Definition Section 8.4**; acceptance does not authorize relaxing any Section 8.4 constraint. Collection readiness/blocker mapping is consumed from its accepted producer contract, not reconstructed by RTICB.

## 6. Exact decision-state routing and nullability
Every accepted CRTISBA entry produces one RTICB comparison entry, even for excluded or unresolved sources. Never demand non-null basis fields where Section 8.4 requires null. All state-specific source/amount/decision identity constraints are validated before classification. The following is a total routing table; `[]` denotes exact no added state reason; ordered reason sets are canonical sorted unique.

| CRTISBA decision_state | Admission | CRTISBA effective tuple allowed | RTICB state | RTICB reasons | Direct readiness |
|---|---|---|---|---|---|
| CURRENT | INCLUDED | Complete current pension OD-1 + derived OD-2, or recurring income + current OD-3; exact Section 8.4 | Compare known fields: DIRECTLY_COMPARABLE, NORMALIZATION_REQUIRED or BASIS_UNRESOLVED | Comparison reasons in Section 7 | Only DIRECTLY_COMPARABLE is ready |
| MISSING | INCLUDED | Pension safe-missing UNKNOWN/MISSING income + valid OD-2; recurring current upstream income + UNKNOWN/null/MISSING price | BASIS_UNRESOLVED | `RTICB_CRTISBA_DECISION_MISSING` plus independently known mismatch reasons only | Blocks |
| UNKNOWN | INCLUDED | Same safe-missing fields as MISSING; valid cleared decision identity | BASIS_UNRESOLVED | `RTICB_CRTISBA_DECISION_UNKNOWN` plus independently known mismatch reasons only | Blocks |
| STALE | INCLUDED | Exact safe-missing fields; no stale choices | BASIS_UNRESOLVED | `RTICB_CRTISBA_DECISION_STALE` only | Blocks |
| INVALID | INCLUDED | Exact safe-missing fields; no invalid decision identity | BASIS_UNRESOLVED | `RTICB_CRTISBA_DECISION_INVALID` only | Blocks |
| UPSTREAM_UNRESOLVED | UNRESOLVED | Frequency-other sole blocker: current recurring income and current OD-3 if validated, otherwise UNKNOWN/null price. All other unresolved: entire basis/provenance/date tuple null | BASIS_UNRESOLVED | `RTICB_CRTISBA_UPSTREAM_UNRESOLVED` only | Blocks |
| NOT_APPLICABLE_DELEGATED | EXCLUDED | All basis/provenance/date null | NOT_ADMITTED | `RTICB_SOURCE_NOT_ADMITTED` only | Neutral |
| DELEGATION_UNRESOLVED | UNRESOLVED | All basis/provenance/date null | BASIS_UNRESOLVED | `RTICB_CRTISBA_DELEGATION_UNRESOLVED` only | Blocks |
| DELEGATION_STALE | UNRESOLVED | All basis/provenance/date null | BASIS_UNRESOLVED | `RTICB_CRTISBA_DELEGATION_STALE` only | Blocks |
| NOT_APPLICABLE_NOT_ADMITTED | EXCLUDED | All basis/provenance/date null | NOT_ADMITTED | `RTICB_SOURCE_NOT_ADMITTED` only | Neutral |

For `UPSTREAM_UNRESOLVED`, the frequency-other special-case is permitted **only** when CRTISBA Section 8.4's sole reason is `RTISA_SOURCE_FREQUENCY_UNSUPPORTED`; any other reason or combination takes the all-null tuple route. No basis comparison is performed for any unresolved admission. Delegation early-return reasons remain RTISA provenance; they do not add ordinary authority/review reasons. `NOT_APPLICABLE_DELEGATED` requires accepted delegation evidence and `NOT_APPLICABLE_NOT_ADMITTED` requires valid exclusion evidence exactly as CRTISBA provides. A valid unresolved admission does **not** invalidate the entire collection; it is represented by the state-specific unresolved route and blocks readiness. A source with admission `INCLUDED` is never reclassified as `NOT_ADMITTED` merely because its basis is UNKNOWN. Invalid state/admission/null/identity combinations fail closed, not normalize.

## 7. Exact comparison algorithm and reason vocabulary
Closed reason codes:
`RTICB_SOURCE_NOT_ADMITTED`, `RTICB_INCOME_BASIS_UNKNOWN`, `RTICB_INCOME_BASIS_MISMATCH`, `RTICB_PRICE_BASIS_UNKNOWN`, `RTICB_PRICE_BASIS_MISMATCH`, `RTICB_REAL_PRICE_REFERENCE_DATE_MISSING`, `RTICB_REAL_PRICE_REFERENCE_DATE_MISMATCH`, `RTICB_CRTISBA_DECISION_MISSING`, `RTICB_CRTISBA_DECISION_UNKNOWN`, `RTICB_CRTISBA_DECISION_STALE`, `RTICB_CRTISBA_DECISION_INVALID`, `RTICB_CRTISBA_UPSTREAM_UNRESOLVED`, `RTICB_CRTISBA_DELEGATION_UNRESOLVED`, `RTICB_CRTISBA_DELEGATION_STALE`.

On CURRENT, compare income and price separately using Section 3. `UNKNOWN` yields unknown reason; unequal known yields mismatch; REAL source date null yields missing only if Section 8.4 permits it in that decision state, otherwise is fatal `RTICB_CRTISBA_STATE_BASIS_INVALID`. On MISSING/UNKNOWN, the state reason always makes BASIS_UNRESOLVED; include only mismatches independently decidable from the safe current non-null basis dimension(s), not unknown reasons for a dimension already explicitly represented by the state reason. On other unresolved states no comparison reasons may be added; excluded states receive exactly one NOT_ADMITTED reason. Known mismatches are retained alongside unresolved evidence only where the state-specific table authorizes comparing known fields. Reasons are sorted with Python Unicode code-point ordering, unique. Amount materiality, including zero, never changes the result.

Classification completion is COMPLETE when both authorities are valid and every source is classified exactly once, regardless of CRTISBA `basis_ready`; it is not itself permission to sum. `classification_complete=true` is equivalent to COMPLETE. `direct_comparison_ready=true`/READY iff completion and **every INCLUDED entry** is DIRECTLY_COMPARABLE and **no UNRESOLVED admission entry exists**. An empty collection or wholly excluded collection can be direct-ready only when the accepted CRTISBA collection is valid and there is no unresolved admission. Readiness blockers are exactly the sorted union of `RTICB_NORMALIZATION_REQUIRED` if any included NORMALIZATION_REQUIRED, `RTICB_BASIS_UNRESOLVED` if any INCLUDED/UNRESOLVED BASIS_UNRESOLVED, with no blocker for excluded entries. No amount total is calculated.

## 8. Output contracts and exact owned fingerprint preimages
RTICB owns four new V2 fingerprint namespaces. Canonical bytes are `json.dumps(object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`; SHA-256 lowercase hex. No V1 fingerprint is accepted as a V2-owned identity.

The successful result has exactly: `schema_version` (literal `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2`), `client_id`, `planning_calculation_input_fingerprint`, `retirement_target_date`, `target_result_fingerprint`, `target_semantic_fingerprint`, `crtisba_result_fingerprint`, `comparison_input_fingerprint`, `source_comparisons`, `classification_state`, `classification_complete`, `direct_comparison_state`, `direct_comparison_ready`, `blockers`, and `comparison_result_fingerprint`. The `source_comparisons` sequence has exactly one entry per CRTISBA source, in the same order.

Every source comparison entry has exactly: `source_id`, `source_kind`, `source_category`, `admission_state`, `rtisa_reason_codes`, `decision_state`, `source_version`, `source_fingerprint`, `amount_authority_fingerprint`, `decision_version`, `decision_fingerprint`, `income_basis`, `income_basis_provenance`, `price_basis`, `price_reference_date`, `price_basis_provenance`, `target_income_basis`, `target_price_basis`, `target_price_reference_date`, `comparison_state`, `reason_codes`, and `source_comparison_fingerprint`. All source fields are verbatim projections of validated CRTISBA authority, including valid nulls; all target fields are verbatim from the accepted target result. No newly inferred value is present. `comparison_state` is exactly one of `DIRECTLY_COMPARABLE`, `NORMALIZATION_REQUIRED`, `BASIS_UNRESOLVED`, `NOT_ADMITTED`.

**A: input**: SHA-256 of the following exact preimage keys: `contract` literal `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_INPUT_JSON_V2`; `client_id`, `planning_calculation_input_fingerprint`, `retirement_target_date` from validated request; `target_result_fingerprint`, `target_semantic_fingerprint` from target; `crtisba_result_fingerprint` from CRTISBA. No RTISA direct fingerprint.

**A: entry**: SHA-256 of `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V2","comparison_input_fingerprint":<input fingerprint>,"entry":<complete comparison entry excluding source_comparison_fingerprint>}`. The `entry` object has exactly the 22 non-hash entry keys enumerated above. Duplicate identity within an entry is deliberate provenance binding, not a second upstream decision.

**A: successful result**: SHA-256 of `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V2","result":<complete successful result excluding comparison_result_fingerprint>}`. This includes all entry fingerprints, partitions implicit in their ordered state/identity projection, readiness fields and blockers. No independent RTISA collection is introduced.

**A: semantic failure**: an exact failure envelope with fields `schema_version` (V2), `client_id`, `supplied_planning_calculation_input_fingerprint`, `supplied_retirement_target_date`, `observed_target_planning_calculation_input_fingerprint`, `observed_target_retirement_target_date`, `observed_target_result_fingerprint`, `observed_crtisba_planning_calculation_input_fingerprint`, `observed_crtisba_retirement_target_date`, `observed_crtisba_result_fingerprint`, `result_state` literal `block_no_result`, `failure_stage`, `failure_detail_code`, and `result_fingerprint`. Observations are exact supplied or observed fields only when type-valid and canonical, else null; they never use a substitute RTISA field. SHA-256 is over `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_FAILURE_JSON_V2","failure":<complete failure envelope excluding result_fingerprint>}`. No raw rejected object, traceback, exception string or nondeterministic actor/time is embedded. Invalid request observations are independently canonicalized, never repaired.

## 9. Fingerprint verification inventory
- **Category A**: all four RTICB V2 identities above, locally computed from complete explicit preimages. A serialization/hash/encoding failure is a technical exception.
- **Category B**: target result and semantic fingerprints, and CRTISBA `result_fingerprint`; recompute from their *accepted complete supplied preimages*, requiring exact schema and hash matching. For CRTISBA result the preimage is `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RESULT_JSON_V1","result":<entire CRTISBA collection except result_fingerprint>}`. Use the accepted target authority's canonical result/semantic preimage contracts unchanged.
- **Category C**: CRTISBA entry `decision_fingerprint`, `source_fingerprint`, `source_version`, `amount_authority_fingerprint`, `rtisa_admission_result_fingerprint`, and transitive Portfolio/PTE/Planning identities. Enforce their accepted structural, version and relationship contracts, and preserve them in collection verification; never independently recompute them without complete owned preimage. A changed decision/amount source that changes the CRTISBA result fingerprint necessarily changes RTICB input identity. Entry fingerprints independently bind these preserved identity fields to each compared entry. Never remove either binding or duplicate consumption of the upstream producer.

## 10. Ordered fail-closed contract
Semantic validation and precedence, from first to last: (1) request schema/identity before DB, (2) target unavailable/schema/fingerprint/readiness, (3) CRTISBA collection unavailable or accepted blocked result/schema/fingerprint, (4) cross-authority identity, coverage/partitions/source relationships, (5) state-specific nullability and classification, (6) successful envelope/fingerprint construction. Technical exceptions from ANY stage propagate and supersede semantic translation; do not synthesize a `CONSTRUCTION_FAILED` code.

Preserve all existing V1 request and target failure meanings under their existing `RTICB_*` codes (as defined in the prior draft Section 13) except that **RTISA-specific input failure codes are replaced** by the following distinct CRTISBA codes:

| Stage | Exact code | Condition |
|---|---|---|
| crtisba_authority | RTICB_CRTISBA_COLLECTION_UNAVAILABLE | no authoritative collection returned, absent as semantic unavailability |
| crtisba_authority | RTICB_CRTISBA_BLOCKED | accepted `CRTISBA_BLOCK_NO_RESULT_V1` professional block |
| crtisba_authority | RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID | malformed envelope, exact-key, entry or partition shape |
| crtisba_authority | RTICB_CRTISBA_RESULT_FINGERPRINT_MISMATCH | otherwise canonical complete collection fails recomputation |
| cross_authority | RTICB_CRTISBA_IDENTITY_MISMATCH | client/planning/date disagreement or valid collection null date |
| cross_authority | RTICB_CRTISBA_SOURCE_UNIVERSE_MISMATCH | missing, duplicate, out-of-order source IDs or partition mismatch |
| cross_authority | RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID | malformed Category C source/amount/decision provenance, version and identity relationship |
| classification | RTICB_CRTISBA_STATE_BASIS_INVALID | state/admission/basis/nullability/provenance pairing contradicts Section 8.4 |

Within a stage, enforce the table order above; before the table, target authority errors use their existing deterministic order and code. Structural validation is separated into top-level envelope/schema checks, source-universe/partition consistency and deep identity/state relationship checks, and each defect has one unique routing code. A syntactically well-formed rehashed but factually tampered CRTISBA collection cannot be independently rediscovered from hidden producer facts: rely on accepted CRTISBA result authority plus the recomputable collection hash and Category C relationships. Technical DB, transaction, SQLAlchemy, upstream execution, rollback, encoding, SHA, JSON, programming, assertion and construction errors never become semantic failure envelopes.

## 11. Transaction and in-snapshot read order
One caller-supplied fresh SQLAlchemy `Session` owns one PostgreSQL REPEATABLE READ READ ONLY transaction. Reject caller-owned existing transaction without commit, rollback or alteration. Execute **target in-snapshot non-owning derivation first, CRTISBA `derive_in_snapshot(db, client_id, operation="READ")` second**, within the exact same session/snapshot. CRTISBA may transitively read RTISA and PTE/Portfolio using its accepted non-owning boundaries; RTICB never calls public RTISA, public CRTISBA GET/READ, or opens a second connection/session. No nested transaction owner, commit, flush, autoflush, write, hidden retry or snapshot reuse. Complete all validation, classification, result/failure fingerprints before exactly one terminal rollback/release. If rollback fails, invalidate as required and propagate a technical exception. The operation never returns a mutable linked ORM object. SQLite tests use the repository's accepted equivalent snapshot behavior. Technical exceptions after transaction acquisition require rollback/invalidation discipline.

## 12. Expected implementation and gate
This is Definition-only. Later implementation, **only if separately authorized after Definition acceptance, manifest, master closure and pre-implementation enumeration**, may adapt the existing pure derived RTICB backend service, focused tests, PostgreSQL snapshot tests, Golden fixtures and narrow non-public target/CRTISBA derivation interfaces. No new model, persistence, migration, API, UI or downstream total/gap engine. Existing RTICB service/tests in master do not imply implementation acceptance or grant authorization. Owner decision is not reopened.

## 13. Acceptance criteria (40)
- `AC-001`: Package identity, governance and unresolved authorization status explicit.
- `AC-002`: Exactly Target and CRTISBA are directly consumed; RTISA only transitive.
- `AC-003`: CRTISBA is exclusive effective source-basis authority.
- `AC-004`: No RTISA native basis is compared.
- `AC-005`: Accepted owner gross/net exact equality.
- `AC-006`: Accepted nominal/real exact equality.
- `AC-007`: Target current/confirmed and ILS validation.
- `AC-008`: Request schema and pre-DB errors.
- `AC-009`: Client/planning/target identity reconciliation.
- `AC-010`: Target Category B semantic and result fingerprints recomputed.
- `AC-011`: CRTISBA complete collection fingerprint recomputed.
- `AC-012`: Valid CRTISBA NOT_READY collection classified, not rejected.
- `AC-013`: CRTISBA professional BLOCK_NO_RESULT whole-authority fails.
- `AC-014`: Source IDs exactly follow CRTISBA ordered universe.
- `AC-015`: Collection partitions exact and disjoint.
- `AC-016`: All entries classified once including EXCLUDED and UNRESOLVED.
- `AC-017`: Pension CURRENT OD-1 and derived OD-2 projected.
- `AC-018`: Recurring CURRENT OD-3 and upstream income projected.
- `AC-019`: MISSING safe-missing and decision nulls.
- `AC-020`: UNKNOWN cleared decision and safe-missing.
- `AC-021`: STALE suppresses stale stored choices.
- `AC-022`: INVALID suppresses malformed decision identity.
- `AC-023`: UPSTREAM_UNRESOLVED frequency-other current decision variant.
- `AC-024`: UPSTREAM_UNRESOLVED frequency-other missing decision variant.
- `AC-025`: UPSTREAM_UNRESOLVED other all-null variant.
- `AC-026`: NOT_APPLICABLE_DELEGATED exact null and not-admitted classification.
- `AC-027`: DELEGATION_UNRESOLVED exact null and blocker.
- `AC-028`: DELEGATION_STALE exact null and blocker.
- `AC-029`: NOT_APPLICABLE_NOT_ADMITTED exact null and not-admitted classification.
- `AC-030`: Decision-state admission and nullability relationship is exact.
- `AC-031`: UNKNOWN/missing and mismatch reasons are deterministically ordered.
- `AC-032`: Known basis and real-date mismatches deterministic.
- `AC-033`: Classification completion separate from readiness.
- `AC-034`: Unresolved admissions block direct readiness.
- `AC-035`: Empty/all-excluded valid universe readiness.
- `AC-036`: V2 input/entry/result/failure preimages exact.
- `AC-037`: Category A/B/C inventory and no unauthorized recomputation.
- `AC-038`: Stage-specific failure precedence and technical exception preservation.
- `AC-039`: One supplied snapshot with Target then CRTISBA and rollback.
- `AC-040`: No conversion, persistence, totals, gap or inference.

## 14. Negative acceptance criteria (25)
- `NAC-001`: Never directly consume RTISA basis.
- `NAC-002`: Never bypass CRTISBA decisions with native UNKNOWN fallback.
- `NAC-003`: Never treat CRTISBA NOT_READY as malformed.
- `NAC-004`: Never reject valid nullable delegated/excluded fields.
- `NAC-005`: Never treat unresolved admission as admitted.
- `NAC-006`: Never drop excluded/unresolved source entries.
- `NAC-007`: Never infer GROSS/NET from labels.
- `NAC-008`: Never infer nominal/real from source origin.
- `NAC-009`: Never invent real reference date.
- `NAC-010`: Never treat UNKNOWN as matching.
- `NAC-011`: Never normalize amounts or dates.
- `NAC-012`: Never compute sums or gap.
- `NAC-013`: Never replace authoritative source identity.
- `NAC-014`: Never compute Category C from missing preimage.
- `NAC-015`: Never omit CRTISBA result fingerprint from input hash.
- `NAC-016`: Never use V1 comparison hash namespaces.
- `NAC-017`: Never accept rehashed but structurally inconsistent collection.
- `NAC-018`: Never ignore amount/decision fingerprint relationships.
- `NAC-019`: Never treat technical failure as semantic block.
- `NAC-020`: Never allow cross-client/planning/date result mixing.
- `NAC-021`: Never duplicate/deduplicate source IDs.
- `NAC-022`: Never wrong ordering/partition reconciliation.
- `NAC-023`: Never open extra session or nested public reader.
- `NAC-024`: Never commit/write/flush/retry.
- `NAC-025`: Never authorize downstream/implementation without governance.

## 15. Stop conditions (8)
- `SC-01`: Cannot consume valid current CRTISBA collection in supplied snapshot; stop for Definition clarification, not workaround.
- `SC-02`: Basis interpretation needed beyond accepted CRTISBA; stop for Definition clarification, not workaround.
- `SC-03`: Unresolved source state cannot be mapped without new professional rule; stop for Definition clarification, not workaround.
- `SC-04`: Category B canonical preimage unavailable to RTICB; stop for Definition clarification, not workaround.
- `SC-05`: Category C must be independently reconstructed to prove correctness; stop for Definition clarification, not workaround.
- `SC-06`: Authority reconciliation needs hidden direct RTISA second read; stop for Definition clarification, not workaround.
- `SC-07`: Correctness requires normalization, tax, totals, gap or persistence; stop for Definition clarification, not workaround.
- `SC-08`: Single transaction/fingerprint/failure determinism cannot be proved; stop for Definition clarification, not workaround.

## 16. Required pre-implementation contract enumeration (after independent Definition acceptance)
Enumerate the full cross-product of accepted CRTISBA ten states, pension vs recurring, exact Section 8.4 subtype/null/version/provenance constraints, included/excluded/unresolved, empty/single/multiple collections, all target income and price bases/dates, known mismatches and unresolved precedence, sorted partitions, validation stages, V2 golden entry/result/failure preimages, Category A/B recomputations and Category C transitive relationship mutations. Require real producer-path controls for CRTISBA `BLOCK_NO_RESULT` and not-ready collection, coherent tampering mutations for omission/change of result fingerprint and decision/amount identity, unchanged-oracle mutation kills for state route, admission, nullability and readiness; verify exact rollback, snapshot, pre-DB and technical-exception behavior. No implementation authorization until independent enumeration acceptance.

## 17. Open governance decisions
`OWNER-DECISION-RTICB-001` remains resolved. No new professional Owner Decision is required. Independent Definition Acceptance is still pending; `DEFINITION_AMENDMENT_REQUIRED=YES` relative to rejected V1 draft. `IMPLEMENTATION=NOT_AUTHORIZED`, `DOWNSTREAM=NOT_AUTHORIZED`, `PRODUCTION_READINESS=NOT_CLAIMED`.
