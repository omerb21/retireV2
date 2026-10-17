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

Accepted entry keys exactly: `schema_version`, `source_id`, `source_kind`, `source_category`, `admission_state`, `rtisa_reason_codes`, `source_version`, `source_fingerprint`, `amount_authority_fingerprint`, `decision_version`, `decision_fingerprint`, `decision_state`, `income_basis`, `income_basis_provenance`, `price_basis`, `price_reference_date`, `price_basis_provenance`, `blockers`. Source kind is PENSION or RECURRING_INCOME; admission INCLUDED, EXCLUDED or UNRESOLVED. All exact shapes, states, amount/source/version/decision relationships, reason vocabularies and nullability follow the **accepted CRTISBA Definition Section 8.4**; acceptance does not authorize relaxing any Section 8.4 constraint. RTICB validates visible producer consistency independently, without rereading RTISA or reconstructing hidden professional source facts: each entry must obey the exact Section 8.4 decision_state/admission/basis/identity/blockers contract; `collection.blockers == sorted(set(blocker for entry in source_basis_entries for blocker in entry.blockers))`; `basis_readiness_state == ("READY" if not collection.blockers else "NOT_READY")`; `basis_ready is (not collection.blockers)`; and each decision-state partition contains exactly the IDs of entries in that state, with case-preserving snake-case partition names. An empty/all-excluded collection is READY only if its actual union of entry blockers is empty. `NOT_READY` is allowed and classifiable when internally consistent. A mismatched blocker union, READY/NOT_READY, basis_ready or state partition fails at `source_universe` as `RTICB_CRTISBA_COLLECTION_CONSISTENCY_INVALID`, not as an unresolved comparison state. This validation uses only visible fields and the accepted producer constraints; the actual source facts remain owned by CRTISBA.

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

**A: entry**: SHA-256 of `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_ENTRY_JSON_V2","comparison_input_fingerprint":<input fingerprint>,"entry":<complete comparison entry excluding source_comparison_fingerprint>}`. The `entry` object has exactly the 21 non-hash entry keys enumerated above. Duplicate identity within an entry is deliberate provenance binding, not a second upstream decision.

**A: successful result**: SHA-256 of `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_JSON_V2","result":<complete successful result excluding comparison_result_fingerprint>}`. This includes all entry fingerprints, partitions implicit in their ordered state/identity projection, readiness fields and blockers. No independent RTISA collection is introduced.

**A: semantic failure**: `schema_version` is the exact literal `CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_RESULT_V2` (the same result schema literal for success and failure). Its exact fields are `schema_version`, `client_id`, `supplied_planning_calculation_input_fingerprint`, `supplied_retirement_target_date`, `observed_target_planning_calculation_input_fingerprint`, `observed_target_retirement_target_date`, `observed_target_result_fingerprint`, `observed_crtisba_planning_calculation_input_fingerprint`, `observed_crtisba_retirement_target_date`, `observed_crtisba_result_fingerprint`, `observed_crtisba_failure_fingerprint`, `observed_crtisba_failure_stage`, `observed_crtisba_failure_detail_code`, `result_state`, `failure_stage`, `failure_detail_code`, `result_fingerprint`. `result_state` is exactly `block_no_result`; `failure_stage` and `failure_detail_code` use Section 10's closed mapping. No missing or extra keys.

Observed fields are field-local: supplied planning SHA/date and request client are copied only if primitively canonical (positive integer excluding bool; lowercase 64-hex SHA; valid canonical ISO date), otherwise null. On an evaluated target result, target planning/date/result-fingerprint fields are independently copied only when primitively canonical, otherwise null. On an evaluated CRTISBA *collection*, copy its planning/date/result fingerprint only when primitively canonical; all three blocked-result observation fields are null. On a structurally accepted CRTISBA *professional blocked result*, there is no collection result fingerprint, so `observed_crtisba_result_fingerprint=null`; the accepted `failure_fingerprint`, `failure_stage` and `failure_detail_code` are copied verbatim into the three specifically named blocked-result fields. Its `observed_planning_calculation_input_fingerprint` supplies `observed_crtisba_planning_calculation_input_fingerprint` when primitively canonical, and its absent retirement-target-date supplies null. A malformed blocked object must never supply `observed_crtisba_failure_fingerprint` or its stage/code as authoritative: all three are null unless the complete accepted blocked schema and its cryptographic identity validate. Unvisited authorities contribute null observations. No observation is substituted from another authority or from the request.

SHA-256: `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_COMPARISON_BASIS_FAILURE_JSON_V2","failure":<all 17 non-result-fingerprint failure fields above>}` under the canonical JSON rules. This **includes** the original CRTISBA blocked failure fingerprint, stage and detail code, so two distinct accepted upstream blocked results cannot silently collapse to the same RTICB failure identity. No raw failed object, traceback, actor/time or technical exception is included. Neither an RTISA fingerprint nor an absent CRTISBA collection result fingerprint is fabricated.
## 9. Fingerprint verification inventory
- **Category A**: all four RTICB V2 identities above, locally computed from complete explicit preimages. A serialization/hash/encoding failure is a technical exception.
- **Category B**: target result and semantic fingerprints, and CRTISBA `result_fingerprint`; recompute from their *accepted complete supplied preimages*, requiring exact schema and hash matching. For CRTISBA result the preimage is `{"contract":"CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_RESULT_JSON_V1","result":<entire CRTISBA collection except result_fingerprint>}`. Use the accepted target authority's canonical result/semantic preimage contracts unchanged.
- **Category C**: CRTISBA entry `decision_fingerprint`, `source_fingerprint`, `source_version`, `amount_authority_fingerprint`, `rtisa_admission_result_fingerprint`, and transitive Portfolio/PTE/Planning identities. Enforce their accepted structural, version and relationship contracts, and preserve them in collection verification; never independently recompute them without complete owned preimage. A changed decision/amount source that changes the CRTISBA result fingerprint necessarily changes RTICB input identity. Entry fingerprints independently bind these preserved identity fields to each compared entry. Never remove either binding or duplicate consumption of the upstream producer.

## 10. Ordered fail-closed contract
First satisfied condition wins. Stages run in this exact order: request_validation; snapshot_admission; target_authority; crtisba_authority; cross_authority_identity; source_universe; classification. A technical exception at any point propagates, with required transaction rollback/invalidation, and never becomes a professional semantic envelope. Result assembly/canonical serialization/UTF-8/SHA-256 exceptions are technical, not an invented failure code. The following is the **complete** V2 stage/code/precedence contract; no rejected draft is incorporated by reference.

| Stage | Ordered `failure_detail_code` | Exact condition |
|---|---|---|
| `request_validation` | `RTICB_REQUEST_SCHEMA_INVALID` | request is not an object with exactly the three keys of Section 4 |
| | `RTICB_CLIENT_ID_INVALID` | client ID is not a positive int excluding bool |
| | `RTICB_EXPECTED_PLANNING_FINGERPRINT_INVALID` | request planning identity is not lowercase SHA-256 |
| | `RTICB_EXPECTED_RETIREMENT_TARGET_DATE_INVALID` | request target date is not canonical ISO date |
| `snapshot_admission` | `RTICB_REQUIRES_FRESH_TRANSACTION` | caller supplied a Session with existing transaction/new/dirty/deleted state; do not mutate that Session |
| | `RTICB_UNSUPPORTED_DATABASE` | dialect is neither PostgreSQL nor accepted SQLite test dialect |
| `target_authority` | `RTICB_TARGET_AUTHORITY_SCHEMA_INVALID` | returned target object fails accepted exact schema, type, enum or nullability |
| | `RTICB_TARGET_AUTHORITY_FINGERPRINT_INVALID` | otherwise structurally valid target has a malformed or non-recomputing result or semantic fingerprint |
| | `RTICB_TARGET_AUTHORITY_UNAVAILABLE` | valid target result expressly reports `authority_state=UNAVAILABLE` |
| | `RTICB_TARGET_AUTHORITY_NOT_READY` | valid non-UNAVAILABLE target is not simultaneously CURRENT, confirmed and ready |
| `crtisba_authority` | `RTICB_CRTISBA_BLOCKED_PLANNING_CONTEXT_UNAVAILABLE` | structurally/cryptographically valid `CRTISBA_BLOCK_NO_RESULT_V1` with `planning_context / CRTISBA_PLANNING_CONTEXT_UNAVAILABLE` |
| | `RTICB_CRTISBA_BLOCKED_RETIREMENT_TARGET_NOT_READY` | same validated blocked schema with `retirement_target / CRTISBA_RETIREMENT_TARGET_NOT_READY` |
| | `RTICB_CRTISBA_BLOCKED_SOURCE_UNIVERSE_INVALID` | same validated blocked schema with `source_universe / CRTISBA_SOURCE_UNIVERSE_INVALID` |
| | `RTICB_CRTISBA_BLOCKED_PENSION_RESULT_INVALID` | same validated blocked schema with `pension_result / CRTISBA_PENSION_RESULT_INVALID` |
| | `RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID` | CRTISBA output is neither a valid blocked result nor a structurally valid collection envelope (including None, absent return, wrong keys/types, malformed or unsupported blocked result); do not invent `COLLECTION_UNAVAILABLE` |
| | `RTICB_CRTISBA_RESULT_FINGERPRINT_MISMATCH` | otherwise canonical collection's `result_fingerprint` fails accepted Category B recomputation |
| `cross_authority_identity` | `RTICB_CLIENT_ID_MISMATCH` | request, validated target and valid CRTISBA collection client IDs disagree |
| | `RTICB_PLANNING_IDENTITY_MISMATCH` | request, validated target and CRTISBA collection planning identities disagree |
| | `RTICB_RETIREMENT_TARGET_DATE_MISMATCH` | request, validated target and CRTISBA collection target dates disagree, including collection null date |
| `source_universe` | `RTICB_CRTISBA_SOURCE_UNIVERSE_MISMATCH` | collection entries have missing/duplicate/noncanonical/out-of-order source IDs, or partitions are not exact, sorted, disjoint complete coverage of decision-state entry IDs |
| | `RTICB_CRTISBA_COLLECTION_CONSISTENCY_INVALID` | entry blocker-to-collection union, collection readiness state or basis_ready fails Section 5's exact visible equality |
| | `RTICB_CRTISBA_ENTRY_AUTHORITY_INVALID` | entry schema/provenance, source/amount/decision version, Category C structure or relation fails the accepted CRTISBA Section 8.4 contract |
| `classification` | `RTICB_CRTISBA_STATE_BASIS_INVALID` | otherwise canonically shaped entry has invalid state/admission/basis/nullability/provenance relationship under Sections 5-7 |

**Exact blocked validation and order.** A professional blocked producer result must have precisely these keys: `schema_version`, `result_state`, `client_id`, `source_id`, `operation`, `failure_stage`, `failure_detail_code`, `field_paths`, `observed_planning_calculation_input_fingerprint`, `observed_source_version`, `observed_source_fingerprint`, `observed_amount_authority_fingerprint`, `observed_decision_version`, and `failure_fingerprint`. Require literal schema `CRTISBA_BLOCK_NO_RESULT_V1`, `result_state=block_no_result`, `operation=READ`, valid positive client ID, canonical or null source_id, canonical sorted unique JSON-pointer `field_paths`, appropriate canonical nullable SHA/version fields, and the exact accepted stage/code pair. Recompute its `failure_fingerprint` from the exact accepted CRTISBA preimage: canonical SHA-256 of an object with `contract="CANONICAL_RETIREMENT_TARGET_DATE_INCOME_SOURCE_BASIS_FAILURE_JSON_V1"` and **exactly** `client_id`, `source_id`, `operation`, `failure_stage`, `failure_detail_code`, `field_paths`, `observed_planning_calculation_input_fingerprint`, `observed_source_version`, `observed_source_fingerprint`, `observed_amount_authority_fingerprint`, and `observed_decision_version` at top level. The CRTISBA `schema_version`, `result_state`, and `failure_fingerprint` are explicitly excluded from this preimage; there is no nested `failure` object. Do not synthesize a collection identity. Invalid producer blocked objects route to `RTICB_CRTISBA_COLLECTION_SCHEMA_INVALID`; a structurally valid accepted blocked object with a non-recomputing SHA also routes there because it is not a validated professional block. On a valid block, copy the original stage/code/fingerprint to Section 8's failure observations, then map the exact four one-to-one RTICB blocked codes in the above table. There is no fifth professional block, no `CRTISBA_COLLECTION_UNAVAILABLE` semantic state, and no loss of source blocked identity.

**Structural-versus-semantic routing.** Classify top-level object/key/type malformation at `crtisba_authority`; once the collection's top-level shape is canonical, check its full supplied Category B result preimage. Then check cross-identity; entry ordering and partitions; visible blocker/readiness equalities; deep Category C identities and version relationships; state-specific nullability; classification. This fixed order resolves simultaneous faults without guessing hidden RTISA, Planning or PTE facts. Malformed producer objects never become successful comparisons. Valid CRTISBA NOT_READY collections continue to successful per-source classification when their visible structures and blocker/readiness relationships are self-consistent. A collection result whose `result_fingerprint` is recomputed over rehashed but inconsistent visible fields still fails the appropriate relationship stage. No cross-authority or state check changes accepted CRTISBA source decisions.

**Failure observation routing.** `request_validation` and `snapshot_admission` have only valid request observations, all authority observations null. At `target_authority`, only field-local target observations may be non-null; CRTISBA observations null. At `crtisba_authority`, preserve the validated target observations and whichever CRTISBA fields are separately canonical; for a fully valid blocked result, preserve exact CRTISBA failure identity, otherwise only field-local collection observations. At later stages, preserve validated target and CRTISBA collection observations, with blocked-result observation fields null. The RTICB failure envelope is built and hashed exactly as in Section 8. Stage-specific non-visited/null rules are part of the canonical fingerprint identity. No direct RTISA observations are included.

## 11. Transaction and in-snapshot read order
One caller-supplied fresh SQLAlchemy `Session` owns one PostgreSQL REPEATABLE READ READ ONLY transaction. Reject caller-owned existing transaction without commit, rollback or alteration. Execute **target in-snapshot non-owning derivation first, CRTISBA `derive_in_snapshot(db, client_id, operation="READ")` second**, within the exact same session/snapshot. CRTISBA may transitively read RTISA and PTE/Portfolio using its accepted non-owning boundaries; RTICB never calls public RTISA, public CRTISBA GET/READ, or opens a second connection/session. No nested transaction owner, commit, flush, autoflush, write, hidden retry or snapshot reuse. Complete all validation, classification, result/failure fingerprints before exactly one terminal rollback/release. If rollback fails, invalidate as required and propagate a technical exception. The operation never returns a mutable linked ORM object. SQLite tests use the repository's accepted equivalent snapshot behavior. Technical exceptions after transaction acquisition require rollback/invalidation discipline.

## 12. Expected implementation and gate
This is Definition-only. Later implementation, **only if separately authorized after Definition acceptance, manifest, master closure and pre-implementation enumeration**, may adapt the existing pure derived RTICB backend service, focused tests, PostgreSQL snapshot tests, Golden fixtures and narrow non-public target/CRTISBA derivation interfaces. No new model, persistence, migration, API, UI or downstream total/gap engine. Existing RTICB service/tests in master do not imply implementation acceptance or grant authorization. Owner decision is not reopened.

## 13. Acceptance criteria (40)
- `AC-01`: Package identity, governance and unresolved authorization status explicit.
- `AC-02`: Exactly Target and CRTISBA are directly consumed; RTISA only transitive.
- `AC-03`: CRTISBA is exclusive effective source-basis authority.
- `AC-04`: No RTISA native basis is compared.
- `AC-05`: Accepted owner gross/net exact equality.
- `AC-06`: Accepted nominal/real exact equality.
- `AC-07`: Target current/confirmed and ILS validation.
- `AC-08`: Request schema and pre-DB errors.
- `AC-09`: Client/planning/target identity reconciliation.
- `AC-10`: Target Category B semantic and result fingerprints recomputed.
- `AC-11`: CRTISBA complete collection fingerprint recomputed.
- `AC-12`: Valid CRTISBA NOT_READY collection classified, not rejected; collection blockers are the exact sorted entry-blocker union, and READY/basis_ready are bound to emptiness of that union.
- `AC-13`: Full accepted CRTISBA BLOCK_NO_RESULT schema and failure hash independently validated; four exact stage/code pairs map one-to-one without dropping blocked failure identity.
- `AC-14`: Source IDs exactly follow CRTISBA ordered universe.
- `AC-15`: Collection partitions exact and disjoint, entry-to-partition equal, and coherent rehashed blocker/readiness tampering fails closed.
- `AC-16`: All entries classified once including EXCLUDED and UNRESOLVED.
- `AC-17`: Pension CURRENT OD-1 and derived OD-2 projected.
- `AC-18`: Recurring CURRENT OD-3 and upstream income projected.
- `AC-19`: MISSING safe-missing and decision nulls.
- `AC-20`: UNKNOWN cleared decision and safe-missing.
- `AC-21`: STALE suppresses stale stored choices.
- `AC-22`: INVALID suppresses malformed decision identity.
- `AC-23`: UPSTREAM_UNRESOLVED frequency-other current decision variant.
- `AC-24`: UPSTREAM_UNRESOLVED frequency-other missing decision variant.
- `AC-25`: UPSTREAM_UNRESOLVED other all-null variant.
- `AC-26`: NOT_APPLICABLE_DELEGATED exact null and not-admitted classification.
- `AC-27`: DELEGATION_UNRESOLVED exact null and blocker.
- `AC-28`: DELEGATION_STALE exact null and blocker.
- `AC-29`: NOT_APPLICABLE_NOT_ADMITTED exact null and not-admitted classification.
- `AC-30`: Decision-state admission and nullability relationship is exact.
- `AC-31`: UNKNOWN/missing and mismatch reasons are deterministically ordered.
- `AC-32`: Known basis and real-date mismatches deterministic.
- `AC-33`: Classification completion separate from readiness.
- `AC-34`: Unresolved admissions block direct readiness.
- `AC-35`: Empty/all-excluded valid universe readiness.
- `AC-36`: V2 input/21-non-hash-entry/result/failure preimages exact, including validated CRTISBA blocked fingerprint/stage/code in failure identity and exact V2 schema literal.
- `AC-37`: Category A/B/C inventory and no unauthorized recomputation.
- `AC-38`: Exhaustive self-contained stage-specific failure codes, blocked one-to-one precedence, malformed None return routing, and technical exception preservation.
- `AC-39`: One supplied snapshot with Target then CRTISBA and rollback.
- `AC-40`: No conversion, persistence, totals, gap or inference.

## 14. Negative acceptance criteria (25)
- `NAC-01`: Never directly consume RTISA basis.
- `NAC-02`: Never bypass CRTISBA decisions with native UNKNOWN fallback.
- `NAC-03`: Never treat CRTISBA NOT_READY as malformed.
- `NAC-04`: Never reject valid nullable delegated/excluded fields.
- `NAC-05`: Never treat unresolved admission as admitted.
- `NAC-06`: Never drop excluded/unresolved source entries.
- `NAC-07`: Never infer GROSS/NET from labels.
- `NAC-08`: Never infer nominal/real from source origin.
- `NAC-09`: Never invent real reference date.
- `NAC-10`: Never treat UNKNOWN as matching.
- `NAC-11`: Never normalize amounts or dates.
- `NAC-12`: Never compute sums or gap.
- `NAC-13`: Never replace authoritative source identity.
- `NAC-14`: Never compute Category C from missing preimage.
- `NAC-15`: Never omit CRTISBA result fingerprint from input hash.
- `NAC-16`: Never use V1 comparison hash namespaces.
- `NAC-17`: Never accept a coherently rehashed collection with false READY/basis_ready, missing/extra aggregate blocker or incorrect partition.
- `NAC-18`: Never ignore amount/decision fingerprint relationships.
- `NAC-19`: Never treat technical failure as semantic block, invent semantic unavailability for absent/None CRTISBA output, or collapse distinct accepted CRTISBA blocked-result identities.
- `NAC-20`: Never allow cross-client/planning/date result mixing.
- `NAC-21`: Never duplicate/deduplicate source IDs.
- `NAC-22`: Never wrong ordering/partition reconciliation.
- `NAC-23`: Never open extra session or nested public reader.
- `NAC-24`: Never commit/write/flush/retry.
- `NAC-25`: Never authorize downstream/implementation without governance.

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
Enumerate the full cross-product of accepted CRTISBA ten states, pension vs recurring, exact Section 8.4 subtype/null/version/provenance constraints, included/excluded/unresolved, empty/single/multiple collections, all target income and price bases/dates, known mismatches and unresolved precedence, sorted partitions, validation stages, V2 golden entry/result/failure preimages, Category A/B recomputations and Category C transitive relationship mutations. Require separate real producer-path controls for all four accepted CRTISBA `BLOCK_NO_RESULT` stage/code pairs, malformed/None return, blocked fingerprint tampering, distinct blocked identities and not-ready collection, coherent tampering mutations for omission/change of result fingerprint and decision/amount identity, unchanged-oracle mutation kills for state route, admission, nullability, readiness, blocker-union equality, partition mapping, blocked failure-identity preservation and one-to-one stage/code mapping; verify exact rollback, snapshot, pre-DB and technical-exception behavior. No implementation authorization until independent enumeration acceptance.

## 17. Open governance decisions
`OWNER-DECISION-RTICB-001` remains resolved. No new professional Owner Decision is required. Independent Definition Acceptance is still pending; `DEFINITION_AMENDMENT_REQUIRED=YES` relative to rejected V1 draft. `IMPLEMENTATION=NOT_AUTHORIZED`, `DOWNSTREAM=NOT_AUTHORIZED`, `PRODUCTION_READINESS=NOT_CLAIMED`.