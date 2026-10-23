# RETIRE V2 — Normative Scenario Conversion Contract V1

**Status: DESIGN ONLY / NOT IMPLEMENTATION-AUTHORIZED / INDEPENDENT RE-REVIEW REQUIRED.**
**Authority:** owner decisions O-01…O-08 recorded in `SCENARIO_CONVERSION_OWNER_DECISION_REGISTER_2026-10-23.md`. O-01 is a clear professional product rule, but technical resolver/anomaly acceptance still requires evidence.
**Precedence:** This file is the **sole normative proposed conversion scenario contract** as of this revision. `V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md` §§1–23 and historical handoffs are **non-normative background evidence** when they disagree. Neither this file nor the historical draft authorizes implementation. A later signed, reviewed normative version can supersede this one explicitly.

## A. Approved product policy (not code claims)

- **O-01:** Education funds and investment provident funds have no genuine severance components. Their exception allows capital conversion of genuine contribution balances regardless of which contribution column received the reported amount. A positive severance-coded balance under such a product is `needs_source_reconciliation`; do not allow a conversion or quietly relabel it.
- **O-02:** Pensions derived from employee/employer contributions through 2000 have approved tax classification **exempt**. Existing backend labels `taxable` are a known mismatch; permission-only preview must return `tax_status=not_evaluated` and never claim tax assessed.
- **O-03:** Whole-plan preview displays every component. Only a specifically selected eligible subset may be submitted, after explicit review. No implicit `whole_product` save or silently omitted item.
- **O-04:** One explicit grouped acknowledgment of exclusions is sufficient after full individual reasons are displayed; bind acknowledgment to the exact reviewed preview digest.
- **O-05:** Unallocated money is a calculated residual, never an action or decision.
- **O-06:** Unsettled severance and rights-continuity block the affected component and proven dependent operations, not unrelated contributions.
- **O-07:** Only the owner or expressly delegated professional approves financial rules. Preserve versions, effective dates, approval provenance and historical results; no automatic retroactive rewriting.
- **O-08:** Missing evidence blocks only dependent actions, with specific missing datum, reason, producer/source and affected component/action.

## B. Permission-only preview — narrow proposed contract, no eligibility conclusion

Public request: `POST /scenario-conversions/permission-preview` **PROPOSED NAME ONLY**; it has no existing endpoint.

Input (all strict typed): `client_id` is derived from authenticated route context/authorized server scope, not a trusted body claim; `product_id` identifies the selected server-owned product; `action` is exactly `pension | capital_asset`; `effective_date` is a date, with supported ruleset selected by server. No client-supplied balance, component classification, product type, tax classification, or caller identity is authority. Scenario identity is not needed for this read-only permission check.

Return strict envelope: `schema_version`, `preview_id` (opaque digest, not a stored draft), `product_id`, `product_version`, `client_scope_ref` (non-sensitive), `canonical_product_class`, `action`, `effective_date`, `ruleset_id`, `ruleset_digest`, `source_fingerprint`, `permission_status`, `professional_eligibility_status=not_evaluated`, `tax_status=not_evaluated`, `components` (exactly 11 rows), and `totals` (original classified, permitted, blocked, unresolved, residual/unselected). No pension amount, tax, NPV, 161d determination or financial yield.

For **every one** of the 11 canonical codes, return canonical `component_code`, source `component_id` if a persisted row exists (otherwise `null`), exact decimal balance as **string**, `permission_status=allowed|blocked|needs_source_reconciliation|unknown`, `reason_code`, Hebrew explanation, and `applicable_rule_id`. The row remains visible even when zero, absent, blocked or unknown. Zero is visible but not selectable for an allocation. Never conflate zero with permission. `blocked` may coexist with otherwise valid product status; `unknown` does not default to a general permission matrix.

**Closed action translation:** only `pension -> pension` and `capital_asset -> capital` for server matrix permission lookup. `leave_unallocated` is forbidden as input; residual is output only. Do not call `tax_for` to produce a tax result.

**Closed product resolver required BEFORE approving preview implementation:** product class must be determined from server-held values using an explicitly enumerated mapping table. The current `product_type.lower()` and substring matching are **not accepted** as a resolver. Map exact verified source values/aliases to canonical `pension_fund | insurance_policy | provident_fund | education_fund | investment_provident_fund`; ambiguity/unknown/missing → `unknown_product_type` (no inferred BASE_MATRIX). An exact alias inventory from accepted source data is still missing; no guessed aliases are approved. For education/investment products, a positive row with a severance code → `needs_source_reconciliation` and no capital permission on that row.

### C. Canonical source fingerprint v1 — serialization protocol

Purpose: detect whether factual monetary source and classification changed between previews. It is **not** a persistence authorization or historical evidence signature.

Preimage is UTF-8 encoded canonical JSON (sorted keys, compact separators, `ensure_ascii=false`, Unicode NFC for strings), schema identifier `scenario-source-fingerprint-v1`. Fields: `schema`, `client_id` (integer), `product_id` (string), `product_version` (integer), `product_type` (literal persisted string), and `components` ordered in the **canonical COMPONENT_CODES sequence**, each object with `component_code`, `component_id` (or null if absent) and `balance` as exact two-decimal currency string. Compute lowercase hexadecimal SHA-256 of exact UTF-8 bytes. Reject malformed/non-finite/negative money. This digest has no rule/evidence signature; keep `ruleset_digest` separate.

**Preview review digest v1 (design for later save):** a distinct SHA-256 over the source fingerprint plus exact action/effective date, ruleset ID/digest, evidence digests, all 11 row statuses/reason codes, exact selected component IDs/amount strings (sorted by canonical code), and full excluded component IDs/reasons (sorted by canonical code). Prefix/schema field `scenario-group-review-v1`; use the same canonical JSON serialization. Selection/exclusion/evidence/rule/source changes invalidate grouped acknowledgment. It is not calculated or accepted for save in the narrow preview phase.

### D. Safety and status contract

- Read-only permission preview must not insert/update/delete/commit any table; it must not invoke factual `canonical_component_conversion_service.preview`, `execute`, or `reverse`, and never POST to `/canonical-conversions`.
- Authorize authenticated client ownership of product before disclosing classification/balances. Unknown scope → deny without leaking product existence. All read queries must use server-side client scope.
- Permission says whether the base **destination** can be considered. `professional_eligibility_status` and `tax_status` always remain `not_evaluated` in this phase; O-06/O-08 professional dependency checks are not falsely claimed to be implemented.
- Permission preview does not save or allocate, produce acknowledgment, mutate factual products, or return an accepted scenario decision. Mixed whole-plan output is **visibility**, not automatic subset execution.
- Use existing `reconcile` for reported-vs-classified discrepancy; show discrepancy as separate field, never distribute it among components or residual.
- A typed error schema (proposed): `error_code`, `reason_he`, `scope`, optional `component_code`, `retryable`. At minimum: `UNAUTHORIZED_CLIENT_SCOPE`, `UNKNOWN_PRODUCT_TYPE`, `AMBIGUOUS_PRODUCT_TYPE`, `UNKNOWN_ACTION`, `UNKNOWN_RULESET`, `MISSING_CANONICAL_SOURCE`, `STALE_SOURCE`, `NEEDS_SOURCE_RECONCILIATION`. Whether errors are envelope-level or per-row must be consistent and is subject to Work review.

### E. Out of scope / future blocked save contract

No new `Scenario`, `ScenarioDecision`, `Allocation` or authority ledger has been approved for implementation. Future save requires append-only revision identity, exact Decimal availability across accepted allocations, isolated transactions, client permissions, product/component locks, CAS, idempotency, full group review digest, source/evidence/ruleset currentness, deterministic rollback and no factual writes. M09 cashflow adjustment models must not be reused as allocation aggregate. A separate evidence-to-rule dependency registry (termination, severance, grants, tax/161d) must be accepted before professional eligibility or save. O-07 owner-authorized immutable ruleset history is policy, not a currently existing server implementation.

### F. Independent re-review acceptance checklist

1. No historical sections can override this normative contract; all O-01…O-08 decisions consistent.
2. Closed product classes plus evidence-backed exact aliases, anomaly row handling, unknown type fail-closed.
3. 11 visible rows including absent/zero, with proper distinction permission/eligibility/tax.
4. Fully deterministic source preimage and digest; group-review preimage is separated and versioned.
5. No factual mutation; source snapshots equal before/after including conversion/pension/capital destination tables.
6. Cross-client and spoofed product-type/balance attempts denied.
7. `capital_asset` correctly maps to `capital`; residual is not an action.
8. V1/V2 basic permissions parity, approved O-02 mismatch explicitly surfaced, no tax claim.
9. Dedicated explicit verdict **permission-only preview design PASS/BLOCKED**, independent of **authoritative save BLOCKED**.
10. No CI, DB recreation, deploy, migration or implementation without separate owner permission.

**Current verdict remains CONTRACT=BLOCKED / PREVIEW=BLOCKED pending re-review / SAVE=BLOCKED / IMPLEMENTATION_NOT_AUTHORIZED.**


## G. Source-verified implementation gap register (2026-10-23; design evidence, not approval)

The following findings were confirmed by direct GitHub source reads on the active branch. They do not represent a new independent Work verdict or permission to implement.

| ID | Verified source fact | Normative consequence / bounded remediation |
| --- | --- | --- |
| NCG-01 | `backend/app/models/pension_product.py` declares `PensionProduct.product_type` as unconstrained `String(255)`. `backend/app/schemas/pension_product.py` accepts it as `ShortText`. | Product class cannot be inferred from a database enum. Establish an evidence-backed inventory of *actually persisted and imported* values before publishing exact aliases. Unknown/ambiguous values remain unresolved, without BASE_MATRIX fallback. |
| NCG-02 | `backend/app/services/canonical_conversion_matrix.py` lowercases `product_type` and applies substring detection of Hebrew and English education/investment fund tokens, otherwise returning the base matrix. It applies product-wide overrides without checking severance-coded rows. | New permission-only preview must not call this function unguarded for unknown classes, or treat an anomalous severance-coded balance as allowed. Define an independent closed type resolver and row-level anomaly treatment, reusing the canonical base **permissions** only where safe. |
| NCG-03 | `backend/app/services/pension_product_service.py::product_response` currently publishes `conversion_components[].allowed_destinations` by calling `destinations`; the latter's values are tax classification labels as well as permission markers. | The existing factual product response must not be relabelled as scenario eligibility/tax authority. In the new preview return permission as a separate status with tax and professional eligibility always `not_evaluated`. Existing factual API remediation and O-02 tax-label correction require an isolated impact assessment. |
| NCG-04 | `backend/app/services/pension_product_service.py::create_product` creates all 11 canonical component rows; `component_balances` rejects records missing any of the 11 or containing noncanonical codes. Each component has a persisted `component_id`. | A persisted product missing a canonical row is a source-integrity error, not a fabricated zero row or a `null` component ID. Keep all 11 positions in a structured error/diagnostic only when doing so cannot conceal data corruption; the normal successful preview has 11 real rows, including zero balances. |
| NCG-05 | `backend/app/services/canonical_component_conversion_service.py::_preflight` currently uses `whole_product` to silently collect eligible positive-balance components while recording disallowed components as `skipped`. | This factual conversion path does **not** satisfy O-03/O-04 grouped explicit review and must not be reused by the scenario preview/save pathway. No change to its factual behavior is authorized here. |
| NCG-06 | `frontend/src/pages/mockConversionEligibility.ts` independently uses substring product-type overrides and has a mock-only `unchanged` action. | This client helper is neither the closed server resolver nor the authority for preview. `unchanged` must not be translated into an accepted financial decision or exposed as an allowed API action. |

### G1. Explicit clarification of preview response and errors

1. For a valid, fully canonical stored product, return **exactly 11 persisted rows** with real component IDs, regardless of zero balances. The `component_id=null` case in section B is reserved for a future explicitly specified *nonpersisted* input mode, which is **outside the first preview slice**. Do not silently synthesize missing source rows.
2. Product-level unknown or ambiguous type produces an **envelope-level failure** `UNKNOWN_PRODUCT_TYPE` or `AMBIGUOUS_PRODUCT_TYPE`, without fallback permission statuses. A source-integrity failure (`MISSING_CANONICAL_SOURCE`) is likewise envelope-level. Authorized clients may receive a non-sensitive structured diagnostic; never disclose an unauthorized product.
3. For a *resolved* education or investment provident fund with a positive severance-coded row, keep the complete 11-row response; that row receives `needs_source_reconciliation`, no permitted destination, and a specific diagnostic. Other contribution rows may retain base destination permission independent of the anomaly, subject to their own rule status.
4. `permission_status` at the envelope level must be derived deterministically from row statuses rather than implying a completed eligibility decision. No overall `allowed` label may imply that all 11 components are convertible or that their legal/tax prerequisites were validated.
5. The `totals.residual/unselected` field in section B cannot mean the O-05 accepted-decision residual in a **stateless permission-only preview**. It must either be omitted from this endpoint or explicitly named `not_allocated_in_this_preview`, equal to classified balance because **no allocation was requested or committed**. Accepted-decision residual belongs to a later versioned scenario service. Reconciliation variance remains a distinct field.

### G2. Evidence gate before a Codex implementation brief

- Inspect actual approved importer/normalization code and collect an alias inventory from **accepted source values**, including manually entered types. Do not infer that tokens found in code prove the full set of source labels.
- Record an exact, enumerated alias-to-class mapping with unsupported aliases and ambiguity tests, including positive severance anomalies in education/investment products. Decide the handling of any additional real product class found in the source rather than forcing it into the five proposed classes.
- Confirm the typed route's authentication/client scope, schema/error structure and existing reconciliation API before any read-only endpoint implementation.
- Independently re-review this normative contract after the above evidence is added. The only candidate first implementation is a **permission-only, read-only** slice, subject to explicit authorization; authoritative scenario save and tax calculation remain blocked.

**Status after this evidence update:** SOURCE-GAPS DOCUMENTED; CLOSED-ALIAS-INVENTORY=OPEN; INDEPENDENT_RE-REVIEW=OPEN; PERMISSION-PREVIEW IMPLEMENTATION=NOT_AUTHORIZED; SCENARIO-SAVE=BLOCKED. Documentation-only update, no CI required.
