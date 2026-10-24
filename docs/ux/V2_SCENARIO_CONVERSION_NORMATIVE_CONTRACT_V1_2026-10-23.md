# RETIRE V2 — Normative Scenario Conversion Contract V1

**Status: DESIGN ONLY / TECHNICAL CONTRACT REPAIRED / NOT IMPLEMENTATION-AUTHORIZED / INDEPENDENT RE-REVIEW REQUIRED.**
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

## B. Permission-only preview — closed technical API contract, no eligibility conclusion

The future endpoint is exactly `POST /api/clients/{client_id}/scenario-conversions/permission-preview`. It is a design contract only; the endpoint does not exist and is not authorized for implementation.

The closed request JSON has exactly three keys: `product_id` (nonempty server product identifier string), `action` (`pension | capital_asset`) and `effective_date` (`YYYY-MM-DD`). Extra keys, nulls and caller-supplied `client_id`, actor, balance, component, product-type, tax or ruleset fields are rejected. The path `client_id` is a positive integer. The server selects the ruleset; the browser cannot select or override it.

The successful response is `SCENARIO_PERMISSION_PREVIEW_V1` and has exactly these top-level keys: `schema_version`, `preview_id`, `client_id`, `product_id`, `product_version`, `canonical_product_class`, `action`, `effective_date`, `ruleset_id`, `ruleset_version`, `ruleset_digest`, `source_fingerprint`, `overall_status`, `professional_eligibility_status`, `tax_status`, `components`, `totals`, `reconciliation`. `professional_eligibility_status` and `tax_status` are always `not_evaluated`. No pension amount, tax amount, NPV, 161d determination, yield or scenario-decision residual is returned.

`components` is an array of exactly 11 persisted rows in the canonical `COMPONENT_CODES` order from `backend/app/models/pension_product.py`. Every row has exactly: `component_code` (canonical string), `component_id` (nonempty persisted string), `balance` (nonnegative exact two-decimal string), `permission_status` (`allowed | blocked | needs_source_reconciliation | unknown`), `reason_code` (nonempty stable string), `reason_he` (nonempty Hebrew presentation string) and `applicable_rule_id` (nonempty immutable ruleset rule identifier). Zero rows remain present. Missing, duplicated or noncanonical rows fail the whole envelope with `MISSING_CANONICAL_SOURCE`; no row is synthesized.

The fixed component order is: `פיצויים_מעסיק_נוכחי`, `פיצויים_לאחר_התחשבנות`, `פיצויים_שלא_עברו_התחשבנות`, `פיצויים_ממעסיקים_קודמים_רצף_זכויות`, `פיצויים_ממעסיקים_קודמים_רצף_קצבה`, `תגמולי_עובד_עד_2000`, `תגמולי_עובד_אחרי_2000`, `תגמולי_עובד_אחרי_2008_לא_משלמת`, `תגמולי_מעביד_עד_2000`, `תגמולי_מעביד_אחרי_2000`, `תגמולי_מעביד_אחרי_2008_לא_משלמת`. A future component-set change requires a new schema version; it cannot silently alter V1.

`totals` has exactly: `original_classified_balance`, `allowed_balance`, `blocked_balance`, `needs_source_reconciliation_balance`, `unknown_balance`, all nonnegative exact two-decimal strings. Each total is the exact sum of the visible rows in that status and the four status totals must equal `original_classified_balance`. There is no `residual`, `unallocated` or accepted-decision total in this permission-only endpoint.

`reconciliation` is the unchanged factual output of the existing `reconcile` boundary and has exactly: `rewards_component_sum`, `severance_component_sum`, `product_component_sum` (exact two-decimal strings), plus `rewards_discrepancy`, `severance_discrepancy`, `product_discrepancy` (signed exact two-decimal strings or null when the corresponding reported total is absent). A discrepancy is never allocated, distributed or converted into a scenario residual.

`overall_status` is derived from the 11 rows with this closed precedence: any `needs_source_reconciliation` → `needs_source_reconciliation`; otherwise any `unknown` → `unknown`; otherwise both `allowed` and `blocked` → `mixed`; otherwise any `allowed` → `allowed`; otherwise `blocked`. Balance zero does not remove a row or change its rule status.

`preview_id` is the lowercase SHA-256 of canonical JSON with `schema="scenario-permission-preview-id-v1"`, `client_id`, `product_id`, `source_fingerprint`, `action`, `effective_date`, `ruleset_id`, `ruleset_version` and `ruleset_digest`, using §C serialization. It is deterministic evidence identity only, not a persisted scenario or authorization to save.

The only action translation is `pension -> pension` and `capital_asset -> capital`. `leave_unallocated`, `unchanged` and all other values are invalid. Permission rules are read exclusively from the immutable permission ruleset in §O; `BASE_MATRIX`, `destinations()` and `tax_for()` are not fallback authorities for this endpoint.

Product class is resolved only through the exact `source_kind` + persisted `product_type` table in §N. Rows that are not `APPROVED` never receive a canonical class or permissions. Ambiguous values fail with `AMBIGUOUS_PRODUCT_TYPE`; unknown, missing or unsupported values fail with `UNKNOWN_PRODUCT_TYPE`. A positive severance-coded row in an approved education/investment product remains a row-level `needs_source_reconciliation` anomaly and receives no capital permission.

### C. Canonical source fingerprint v1 — serialization protocol

Purpose: detect whether factual monetary source and classification changed between previews. It is **not** a persistence authorization or historical evidence signature.

Preimage is UTF-8 encoded canonical JSON (sorted keys, compact separators, `ensure_ascii=false`, Unicode NFC for strings), schema identifier `scenario-source-fingerprint-v1`. Fields: `schema`, `client_id` (integer), `product_id` (string), `product_version` (integer), `source_kind` (`manual | imported`), `product_type` (literal persisted string), and `components` ordered in the **canonical COMPONENT_CODES sequence**, each object with `component_code`, persisted non-null `component_id` and `balance` as exact two-decimal currency string. Compute lowercase hexadecimal SHA-256 of exact UTF-8 bytes. Reject malformed/non-finite/negative money. This digest has no rule/evidence signature; keep `ruleset_digest` separate.

**Preview review digest v1 (design for later save):** a distinct SHA-256 over the source fingerprint plus exact action/effective date, ruleset ID/digest, evidence digests, all 11 row statuses/reason codes, exact selected component IDs/amount strings (sorted by canonical code), and full excluded component IDs/reasons (sorted by canonical code). Prefix/schema field `scenario-group-review-v1`; use the same canonical JSON serialization. Selection/exclusion/evidence/rule/source changes invalidate grouped acknowledgment. It is not calculated or accepted for save in the narrow preview phase.

### D. Safety, errors and retry contract

- Read-only permission preview must not insert/update/delete/commit any table; it must not invoke factual `canonical_component_conversion_service.preview`, `execute`, or `reverse`, and never POST to `/canonical-conversions`.
- Require the verified single-operator session described in §L before disclosing data. Fetch product and its components with the conjunctive server-side predicate `PensionProduct.client_id == path client_id AND PensionProduct.product_id == request product_id`. A missing client, missing product and wrong-client product are indistinguishable `PREVIEW_SOURCE_NOT_FOUND` responses; do not leak whether the product exists under another client.
- Permission says whether the base **destination** can be considered. `professional_eligibility_status` and `tax_status` always remain `not_evaluated` in this phase; O-06/O-08 professional dependency checks are not falsely claimed to be implemented.
- Permission preview does not save or allocate, produce acknowledgment, mutate factual products, or return an accepted scenario decision. Mixed whole-plan output is **visibility**, not automatic subset execution.
- Use existing `reconcile` for reported-vs-classified discrepancy; show discrepancy as separate field, never distribute it among components or residual.
- Every route-owned failure uses the existing `RTDIR_TRANSPORT_ERROR_V1` shape exactly: `schema_version`, `code`, `message`, `field_paths`, `request_id`. Middleware-owned authentication, Origin and CSRF failures keep that same shape. Retryability is a deterministic property of `(HTTP status, code)`, not a second body schema: security/request/type/source-structure errors are non-retryable without corrected credentials or input; `STALE_SOURCE` is retryable only after a fresh preview; `PREVIEW_DATABASE_UNAVAILABLE` and `PREVIEW_TRANSACTION_CLEANUP_FAILED` are retryable after service recovery.
- Exact route-owned mappings: malformed path/body or unknown action → `422 SCENARIO_PERMISSION_REQUEST_INVALID`; unresolved exact type → `422 UNKNOWN_PRODUCT_TYPE` or `422 AMBIGUOUS_PRODUCT_TYPE`; missing/duplicated/noncanonical source rows → `409 MISSING_CANONICAL_SOURCE`; absent client/product or wrong-client product → `404 PREVIEW_SOURCE_NOT_FOUND`; no unique approved ruleset for the effective date → `409 UNKNOWN_RULESET`; source/version changed during validation → `409 STALE_SOURCE`; unsupported production database or connection/read failure → `503 PREVIEW_DATABASE_UNAVAILABLE`; rollback/invalidation/close uncertainty → `503 PREVIEW_TRANSACTION_CLEANUP_FAILED`. Authentication remains the existing `401 SESSION_MISSING | SESSION_INVALID | SESSION_EXPIRED`; Origin and CSRF remain `403 ORIGIN_FORBIDDEN | CSRF_INVALID`.
- `needs_source_reconciliation` is a successful row anomaly, not an HTTP error. Envelope errors return no component/totals payload. A successful response always returns all 11 real rows.

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

**Current verdict: TECHNICAL_CONTRACT_REPAIR=COMPLETE; PRODUCT_MAPPING_APPROVAL=PARTIAL/PENDING (§N); INDEPENDENT_RE-REVIEW=PENDING; PREVIEW_IMPLEMENTATION=NOT_AUTHORIZED; SAVE=BLOCKED.**


## G. Source-verified implementation gap register (2026-10-23; design evidence, not approval)

The following findings were confirmed by direct GitHub source reads on the active branch. They do not represent a new independent Work verdict or permission to implement.

| ID | Verified source fact | Normative consequence / bounded remediation |
| --- | --- | --- |
| NCG-01 | `backend/app/models/pension_product.py` declares `PensionProduct.product_type` as unconstrained `String(255)`. `backend/app/schemas/pension_product.py` accepts it as `ShortText`. | Product class cannot be inferred from a database enum. The evidence-backed inventory and fail-closed result are now binding in §N. Unknown/ambiguous values remain unresolved, without BASE_MATRIX fallback. |
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

- The importer/manual-source inspection is complete for the code-proven values and is recorded in §N. Newly observed values must be added as explicit rows; tokens or substring matches never extend the inventory.
- Professional approval must move an exact §N row to `APPROVED` through a new immutable §O artifact. Unsupported/ambiguous aliases and positive severance anomalies require the specified fail-closed tests. Any additional real product class is reviewed explicitly rather than forced into the five proposed classes.
- Confirm the typed route's authentication/client scope, schema/error structure and existing reconciliation API before any read-only endpoint implementation.
- Independently re-review this normative contract after the above evidence is added. The only candidate first implementation is a **permission-only, read-only** slice, subject to explicit authorization; authoritative scenario save and tax calculation remain blocked.

**Status after SC-PERM-02:** SOURCE INVENTORY=CLOSED FOR CODE-PROVEN VALUES; PROFESSIONAL MAPPING APPROVAL=PENDING; INDEPENDENT_RE-REVIEW=OPEN; PERMISSION-PREVIEW IMPLEMENTATION=NOT_AUTHORIZED; SCENARIO-SAVE=BLOCKED. Documentation-only update, no CI required.


## H. Corrected source-type intake evidence (2026-10-23)

**Correction superseding commits `7c02605` and `39b409b`:** Earlier conclusions that imported numeric `SUG-MUTZAR` codes remain numeric in persisted `PensionProduct.product_type` were **incorrect**. Direct inspection of `backend/app/services/pension_product_import_service.py::_prepare_batch` establishes that the raw parsed value is converted **before** `ProductMetadata` validation and `import_source_batch` persistence:

```python
product_type = metadata.get("product_type")
metadata["product_type"] = PRODUCT_TYPE_LABELS.get(product_type, "סוג מוצר לא ממופה") if product_type else "סוג מוצר לא נמסר"
```

The raw numeric code is parsed by `_product_type` from `SUG-MUTZAR`, recorded in XML source diagnostics when unmapped, and the raw original XML is preserved as source evidence. **The persisted product_type is a Hebrew display label or fallback text**, not the original numeric code. Existing-product updates and new-product creation both use the normalized `metadata.model_dump()`. The canonical product-source fingerprint in §C currently includes the *persisted display string*, not an independently normalized or immutable raw code; future versioned type resolution must therefore preserve/recover raw type evidence when necessary.

| Exact import code | Value persisted as `product_type` | Candidate canonical class, **not yet approved** |
| --- | --- | --- |
| `1` | פוליסת ביטוח חיים משולב חיסכון | `insurance_policy` candidate |
| `2` | פוליסת ביטוח חיים | `insurance_policy` candidate, risk-only ambiguity |
| `3` | קופת גמל | `provident_fund` candidate; **not** an investment-provident-fund assertion |
| `4` | קרן פנסיה | `pension_fund` candidate |
| `5` | פוליסת חיסכון טהור | unresolved distinct product semantics |
| Unrecognized nonempty | סוג מוצר לא ממופה | unknown, must fail closed |
| Missing | סוג מוצר לא נמסר | unknown, must fail closed |

`_parse_source` records an `unmapped_product_type` diagnostic for unrecognized raw codes, but `_prepare_batch` collapses multiple distinct unknown source codes into the same persisted fallback text. A secure new resolver **must not** interpret that fallback as a legitimate type or infer permissions from the product name. If distinction among original unknown codes is necessary, consult protected source links/diagnostics rather than guessing. No factual migration is authorized.

**Manual product path:** `backend/app/schemas/pension_product.py::ProductMetadata.product_type` is free text (`ShortText`) and `pension_product_service.create_product` persists the supplied string; there is no proven controlled manual-type vocabulary. Some imported Hebrew labels may overlap with manual labels, but equal text alone is not proof of equal provenance or professional classification. Resolver inputs should include `source_kind`, the persisted `product_type` and controlled, versioned evidence, with exact accepted aliases only.

**O-01 gap:** This importer map does not explicitly recognize an education fund or an investment provident fund as distinct product types. No numeric code may be invented. The existing matrix's substring handling for such fund names does not establish authoritative recognition of imported products. The recognized code `3` is not sufficient to identify investment provident funds.

**Important distinction:** The original matrix's substring matching *can* match some persisted Hebrew strings (unlike the earlier inaccurate all-numeric assertion). It still does not provide closed, deterministic, evidence-backed type classification and still applies product-wide permission overrides to severance-coded anomalies. The gap remains real, but its mechanism is different from the previously reported one.

**Acceptance gate:** the code-proven intake values and their deterministic unresolved/unsupported outcomes are closed in §N. Professional approval is still required for every proposed class, especially insurance/savings and any future education/investment exact value. Independent Work re-review is still required. No preview implementation, scenario save, factual data rewrite, CI, migration or deployment is authorized by this documentation.


## I. Manual-input/UI and unknown import values, verified follow-up (2026-10-23)

**Source cross-check:** `frontend/src/pages/RetirementWorkspaceScreen.tsx` displays persisted products and provides a component balance correction workflow. In `saveCorrection` it copies `product_type: product.product_type` back into the PUT request; it does **not** show a controlled type selector or enumerate aliases in that workflow. `frontend/src/api/pensionProductsApi.ts` declares `product_type: string`, not an enum. These two inspected frontend sources do not establish that no other manual-entry form exists elsewhere; a repository-wide UI input inventory is still unverified.

**Unknown-value source behavior:** `pension_product_import_service._prepare_batch` explicitly assigns `"סוג מוצר לא ממופה"` to unrecognized nonempty `SUG-MUTZAR` and `"סוג מוצר לא נמסר"` when missing. `ProductMetadata.product_type` accepts these nonempty strings; import subsequently builds a product from the resulting metadata. Therefore an unrecognized or missing source product type is **not automatically rejected by type validation**, and must not become eligible in scenario permission preview via fallback to the ordinary base matrix.

**Closed source inventory:** §N is the binding resolver table for the five persisted mapped Hebrew labels, the two explicit fallback labels and manual free text. Imported `source_kind` is a discriminator. Both missing/unknown fallbacks produce envelope-level `UNKNOWN_PRODUCT_TYPE`; manual free text remains ambiguous until an exact professionally approved mapping exists. Preserve original imported evidence when reclassifying later, without changing factual product records.

**Reviewed-class mapping status:** `קרן פנסיה` is a strong candidate for `pension_fund`; `קופת גמל` is a candidate for `provident_fund` **only**, never evidence of `investment_provident_fund`; the three insurance/savings descriptions need professional subtype review. A sixth class, or a nonconvertible/unsupported status for savings-only products, may be required. No legal/financial permission follows merely from a display label.

**Minimal acceptance tests to specify (design only):** all five importer labels, both fallback strings, unknown manually entered strings, type/name spoofing, changing source kind, an education/investment-fund severance-coded nonzero row, all 11 component rows with zeros, and client-isolation check. Verify that updating a balance in the current workspace preserves exact persisted product type. No CI run has established these test results.

**Professional gate:** authoritative manual aliases and exact education/investment provident source identification remain pending professional approval. The technical resolver behavior for those cases is no longer ambiguous: fail closed under §N. Do not authorize Preview code or scenario save until the mappings and contract pass independent review.


## J. Verified actual manual pension-product screen (2026-10-23)

Source: `frontend/src/routes/AppRoutes.tsx` routes `/clients/:clientId/pension-products` to `frontend/src/pages/PensionProductsScreen.tsx`, which was inspected directly. `PensionProductsScreen.tsx` defines `emptyMetadata().product_type = "קופת גמל"`, shows `product_type` as an ordinary free-text `<input>` in the metadata form, and applies no closed type enumeration there. It also declares a separate `productTypeLabel` formatter that displays codes `"1"` through `"5"` as Hebrew descriptions; this presentation-only formatter is not a resolver nor proof that such codes are stored in the current import flow.

**Consequences for bounded scenario design:** A manually created product may contain the initial `"קופת גמל"` default or any user-entered nonempty value accepted by backend `ShortText`. Merely retaining a default does not verify the professional subtype. The existence of a free-text input means a complete, observed manual alias *inventory cannot be derived from code alone*. For permission preview, only explicitly accepted exact labels may ever resolve to a canonical class, and any unknown or ambiguous user-entered text must produce an unresolved type, not a guessed fallback; type correction must not silently alter existing factual source records.

**Potential future UX improvement (not implementation-authorized):** supply a controlled professional type selector with an explicit unresolved/other option, and keep the original source description separately for audit and provenance. Changing the existing input or rewriting product records requires a distinct migration/compatibility and ownership review; do not implement as a side effect of the read-only preview.

**Review status:** Exact education/investment source mappings remain professionally unapproved; no professional rule has been invented. The technical result is deterministically `AMBIGUOUS_PRODUCT_TYPE` or `UNKNOWN_PRODUCT_TYPE` under §N. Independent review remains outstanding. No CI, domain changes or deployment.


## K. Authentication and strictly read-only source access evidence (2026-10-23)

Directly inspected `backend/app/main.py`, `backend/app/security/middleware.py`, `backend/app/security/config.py`, `backend/app/db/session.py`, `backend/app/api/pension_product_routes.py`, `backend/app/services/canonical_pension_source_reader.py`, and `backend/app/services/pension_product_service.py`.

- Production installs `RTDIRSecurityMiddleware` globally. For nonpublic routes it invokes `validate_session`; unsafe methods additionally undergo origin and CSRF validation. Development/test intentionally bypass this middleware branch, and therefore integration tests must explicitly exercise production-like authenticated behavior. The underlying `validate_session` implementation and complete public-path predicates remain to be independently inspected.
- The inspected `AuthConfig` exposes one configured `actor_id`, username and password hash, rather than an evidenced per-client role/membership registry. **No principal-to-client authorization mapping was established in these sources**. Do not assert that a route `client_id` is authorized merely because `get_product` filters on that number. A professional single-operator deployment model may be deliberate, but must be named and accepted; a hypothetical future multi-tenant model must not be fabricated.
- The existing `detail` route and `current_products` invoke `lock_client`. On SQLite this issues an `UPDATE Client` writer reservation; on PostgreSQL it takes an advisory lock plus `FOR UPDATE`. A permission-only preview must not reuse these operations if its zero-write/no-writer-lock guarantee is to hold.
- Proposed narrow snapshot access: authenticate using existing production middleware, verify product belongs to requested client through the same server-side predicate as `get_product`; establish the actual deployment's authorized client scope independently, select source metadata and its eleven components within an appropriately consistent read transaction, and perform zero ORM mutations, `commit`, insert/update/delete or factual conversion calls. An uncommitted read transaction alone is not proof of a consistent snapshot on every isolation level: require a specified isolation/snapshot strategy and concurrent-update negative tests.
- Security acceptance cases: no session, forged route client ID, foreign product/client pair, developer/test auth bypass, changed component between reads, no record, malformed/partial eleven-row source, zero-write SQL statement capture, and stale product version/fingerprint. Return no product-existence information before authorization is resolved.

**Classification:** authentication middleware EXISTS; per-client authorization MODEL NOT PROVEN; safe strictly read-only transactional reader NOT IMPLEMENTED. This is a documented engineering/review gate, **not** approval to implement. Neither a broad RBAC system nor a new account architecture is prescribed without a demonstrated requirement.


## L. Verified production session identity and bounded preview access model (2026-10-23)

Direct source evidence from `backend/app/security/transport.py::validate_session`, `backend/app/security/session.py::issue/verify`, `backend/app/security/config.py::AuthConfig`, and `backend/app/api/auth_routes.py`: production session validation verifies the session token and stores `request.state.auth_session` and `request.state.trusted_professional_actor = payload["actor_id"]`. The session actor identity is bound to the single configured `AUTH_ACTOR_ID`. Inspected code does **not** implement independent planner-to-client memberships or per-client ACL roles.

**Closed security boundary for this design:** production authentication is the existing configured single-operator model. The middleware-verified session actor must equal configured `AUTH_ACTOR_ID`; that actor represents the one professional workspace and may read that workspace's client records. There is no RBAC, planner role, tenant membership or principal-to-client membership contract in the current implementation, and this document does not invent one. Product disclosure is nevertheless scoped by the conjunctive path-client/product predicate in §D, so a product belonging to a different or nonexistent client is never returned.

The preview API must not accept an actor identity from the request body, must not reimplement or bypass session validation, and must never authorize based solely on product name/type or a browser body claim. Because the endpoint is `POST`, existing production middleware must validate exact Origin and CSRF after session validation. Production-like tests must exercise missing/invalid/expired session, wrong Origin, invalid CSRF, valid configured session with nonexistent or wrong-client product ID, and spoofed identity fields. Development bypass behavior is not production authorization evidence.

This is intentionally limited to the current single-operator deployment. A future multi-operator deployment must fail closed until a separate independently accepted access model exists. This security closure does not authorize implementation or claim multi-user isolation.


## M. Binding zero-write snapshot contract (2026-10-24; NOT IMPLEMENTED)

Source evidence: `backend/app/db/session.py` configures SQLAlchemy `Session(autocommit=False, autoflush=False)` via `sessionmaker`; `pension_product_service.lock_client` is a deliberate *write-coordination* boundary and **must remain unchanged** for factual mutations. Production configuration requires a PostgreSQL URL. A new preview must not use `current_products`, existing `detail` route, or `lock_client` because they may acquire writer locks and, on SQLite, issue UPDATE.

**PostgreSQL protocol:** each preview owns a new dedicated SQLAlchemy `Connection` and a new `Session` bound only to that connection; it must not receive or reuse the request's ordinary dependency Session. Before the first SQL statement, apply SQLAlchemy connection execution options `isolation_level="REPEATABLE READ"` and `postgresql_readonly=True`, then explicitly begin one transaction. Within it, execute the conjunctive client/product read and the ordered 11-component read, ruleset selection and fingerprint construction. No `SELECT FOR UPDATE`, advisory lock, ORM mutation, flush, commit, source audit or conversion-service call is permitted. The database read-only mode is mandatory enforcement, not merely an application convention.

**Transaction termination:** on every success, professional block or technical failure after transaction ownership begins, call rollback exactly once. Then close the Session and Connection. A pre-connection failure has no owned transaction and therefore no rollback. A failure after connection acquisition but before/while begin must inspect actual transaction state and roll back if SQLAlchemy/PostgreSQL created one. Never return a preview until rollback and close completed successfully.

**Cleanup failure:** retain the actually acquired Connection. If rollback fails, attempt `Connection.invalidate()` on that retained object, close the Session and connection, and return `503 PREVIEW_TRANSACTION_CLEANUP_FAILED`; this cleanup failure takes precedence over a tentative success, row block or earlier technical exception because transaction outcome is no longer trusted. Invalidation or close failure keeps the same public code, is logged against `request_id`, and permanently prevents reuse of that Session/Connection. If rollback succeeds, preserve the original route failure mapping. No automatic retry occurs inside the route.

**SQLite test protocol (not production equivalence):** use a separate dedicated connection and Session, issue an explicit read `BEGIN` before the first SELECT, perform every source read through that connection, rollback and close. Capture SQL and reject UPDATE/INSERT/DELETE/DDL, `BEGIN IMMEDIATE`, `BEGIN EXCLUSIVE` and writer-reservation helpers. A two-connection test must prove that one preview cannot combine product/version from one state with components from another; if the configured SQLite mode cannot demonstrate that invariant, mark the SQLite concurrency case unsupported rather than weakening PostgreSQL requirements. SQLite evidence cannot satisfy PostgreSQL isolation/read-only acceptance.

**Validation:** Capture executed SQL and assert zero DML/DDL or write-capable lock statements; concurrent factual product update cannot yield product/version from one revision and components from another; follow-up stale fingerprint is detectable. A permission preview never allocates or persists results; its response is informational.

**API method security:** the binding endpoint is `POST`, so production `RTDIRSecurityMiddleware` requires both exact Origin and CSRF token despite the endpoint having zero database writes. Do not bypass origin/CSRF. There is no GET alternative in this contract version.

**Review gate:** This is the selected contract, not evidence that it has been implemented or database-tested. Future authorization must test connection options before first SQL, database-enforced read-only behavior, concurrent snapshots, all termination paths, cleanup precedence and permanent non-reuse. No CI or database run is authorized by this documentation task.


## N. Binding product resolver inventory

Resolver key is the exact pair `(source_kind, persisted product_type)` after Unicode NFC normalization only. No trimming, lowercasing, substring matching, product-name inference or alias expansion is permitted. `source_kind` outside `manual | imported` is invalid source structure. The table below is exhaustive for source values proven by the inspected code; `proposed_class` is not an approval.

| `source_kind` | Exact persisted `product_type` | Proven source | `proposed_class` | Approval status / resolver result |
| --- | --- | --- | --- | --- |
| `imported` | `קרן פנסיה` | importer code `4` | `pension_fund` | `PENDING_PROFESSIONAL_APPROVAL` → `AMBIGUOUS_PRODUCT_TYPE` |
| `imported` | `קופת גמל` | importer code `3` | `provident_fund` only | `PENDING_PROFESSIONAL_APPROVAL` → `AMBIGUOUS_PRODUCT_TYPE`; never infer investment provident |
| `imported` | `פוליסת ביטוח חיים משולב חיסכון` | importer code `1` | `insurance_policy` candidate | `PENDING_PROFESSIONAL_APPROVAL` → `AMBIGUOUS_PRODUCT_TYPE` |
| `imported` | `פוליסת ביטוח חיים` | importer code `2` | ambiguous insurance/risk product | `AMBIGUOUS` → `AMBIGUOUS_PRODUCT_TYPE` |
| `imported` | `פוליסת חיסכון טהור` | importer code `5` | unsupported until class is decided | `UNSUPPORTED` → `UNKNOWN_PRODUCT_TYPE` |
| `imported` | `סוג מוצר לא ממופה` | explicit importer fallback | none | `UNSUPPORTED` → `UNKNOWN_PRODUCT_TYPE` |
| `imported` | `סוג מוצר לא נמסר` | explicit importer fallback | none | `UNSUPPORTED` → `UNKNOWN_PRODUCT_TYPE` |
| `manual` | `קופת גמל` | current manual-form default; still free text | `provident_fund` candidate | `PENDING_PROFESSIONAL_APPROVAL` → `AMBIGUOUS_PRODUCT_TYPE` |

Every other manually entered string is outside the proven exact-value table and returns `AMBIGUOUS_PRODUCT_TYPE`; textual equality with an imported label does not transfer imported provenance. There are currently **no source-proven exact labels for `education_fund` or `investment_provident_fund` and no professionally approved resolver row**. O-01 remains intact: once an exact label/provenance pair is professionally approved, contribution rows may use its permission rule while positive severance rows remain `needs_source_reconciliation`. Adding an approved mapping requires a new immutable ruleset version and independent review; it never edits this table in place or falls through to `BASE_MATRIX`.


## O. Binding immutable permission-ruleset artifact

The future server loads an immutable, append-only artifact with `schema="scenario-permission-ruleset-v1"`. The artifact has exactly: `schema`, `ruleset_id` (stable nonempty string), `ruleset_version` (positive integer), `status` (`approved` only for selection), `effective_from` (`YYYY-MM-DD`), `effective_until` (exclusive date or null), `approved_by_actor_id`, `approval_record_id`, `predecessor_digest` (64 lowercase hex or null for first version), `product_mappings`, and `component_rules`.

`product_mappings` contains only §N rows whose status has become `APPROVED`, ordered by UTF-8 bytes of `source_kind` then exact `product_type`; each has exactly `source_kind`, `product_type`, `canonical_product_class` and `mapping_rule_id`. `component_rules` contains exactly 11 entries in canonical component order. Each entry has exactly `rule_id`, `component_code`, `applicable_product_classes`, and `actions`; `actions` has exactly `pension` and `capital_asset`, each with `permission_status=allowed|blocked` and a stable `reason_code`. Professional-evidence dependencies may only be recorded as `not_evaluated` metadata in a later accepted schema; this permission artifact cannot claim eligibility.

The V1 permission rows are fixed below. `standard` means `pension_fund | insurance_policy | provident_fund`. `special capital` applies only to genuine contribution rows for an approved `education_fund | investment_provident_fund`. `A` means `allowed`, `B` means `blocked`.

| Canonical component | Standard `pension` | Standard `capital_asset` | Special `pension` | Special `capital_asset` |
| --- | --- | --- | --- | --- |
| `פיצויים_מעסיק_נוכחי` | B | B | positive balance → reconciliation | positive balance → reconciliation |
| `פיצויים_לאחר_התחשבנות` | A | A | positive balance → reconciliation | positive balance → reconciliation |
| `פיצויים_שלא_עברו_התחשבנות` | B | B | positive balance → reconciliation | positive balance → reconciliation |
| `פיצויים_ממעסיקים_קודמים_רצף_זכויות` | B | B | positive balance → reconciliation | positive balance → reconciliation |
| `פיצויים_ממעסיקים_קודמים_רצף_קצבה` | A | B | positive balance → reconciliation | positive balance → reconciliation |
| `תגמולי_עובד_עד_2000` | A | A | A | A |
| `תגמולי_עובד_אחרי_2000` | A | B | A | A |
| `תגמולי_עובד_אחרי_2008_לא_משלמת` | A | B | A | A |
| `תגמולי_מעביד_עד_2000` | A | A | A | A |
| `תגמולי_מעביד_אחרי_2000` | A | B | A | A |
| `תגמולי_מעביד_אחרי_2008_לא_משלמת` | A | B | A | A |

The stable V1 reasons are `BASE_PERMISSION_ALLOWED` for standard A, `BASE_PERMISSION_BLOCKED` for standard B, `PRODUCT_CONTRIBUTION_CAPITAL_ALLOWED` for the special capital A, and `SOURCE_SEVERANCE_PRODUCT_MISMATCH` for every positive special-product severance row. A zero special-product severance row uses its standard A/B rule but remains nonselectable because its amount is zero. No row uses or serializes `exempt`, `taxable` or `capital_gains` as a permission result.

Tax labels and `tax_for()` results are forbidden in the artifact and cannot determine permission. The approved O-02 tax decision remains recorded but is not emitted or evaluated by Permission Preview.

Ruleset selection is server-only: select the unique immutable `approved` version whose half-open interval contains request `effective_date`. Zero or multiple matches fail `UNKNOWN_RULESET`; no newest-version, current-date or `BASE_MATRIX` fallback is allowed. Historical previews retain their exact ruleset ID/version/digest and are not silently reevaluated.

`ruleset_digest` is lowercase SHA-256 over UTF-8 canonical JSON of the whole artifact except no digest field is present in its own preimage: Unicode NFC strings, sorted object keys, compact separators, `ensure_ascii=false`, no floats, arrays in the orders fixed above. Approval is bound to this digest. Any content change creates a new version, approval record and digest; approved artifacts are never mutated.


## P. SC-PERM-02 closure register

| Finding | Contract status | Binding location | Remaining boundary |
| --- | --- | --- | --- |
| `SC-PERM-01-001` product resolver | `CLOSED` technically | §§B, N | Exact professional mapping approvals remain pending; unresolved rows fail closed. |
| `SC-PERM-01-002` immutable ruleset | `CLOSED` | §§B, O | Artifact implementation and independent acceptance are not authorized. |
| `SC-PERM-01-003` zero-write snapshot | `CLOSED` | §M | PostgreSQL/SQLite execution evidence is future implementation acceptance, not part of this docs-only repair. |
| `SC-PERM-01-004` API envelope | `CLOSED` | §§B, D | Endpoint does not exist and remains unauthorized. |
| Single-operator security boundary | `CLOSED` for current deployment | §§D, L | Multi-operator RBAC/client membership is absent and not claimed. |

Technical closure means the contract no longer offers competing implementation choices. It does not mean Preview exists, passed GPT Work review or is authorized. Permission Preview remains blocked specifically by professional approval of resolver mappings, independent contract acceptance and explicit implementation authorization. Authoritative scenario decisions/save remain a separate blocked package.
