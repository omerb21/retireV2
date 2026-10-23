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

Return strict envelope: `schema_version`, `preview_id` (opaque digest, not a stored draft), `product_id`, `product_version`, `client_scope_ref` (non-sensitive), `canonical_product_class`, `action`, `effective_date`, `ruleset_id`, `ruleset_digest`, `source_fingerprint`, `permission_status`, `professional_eligibility_status=not_evaluated`, `tax_status=not_evaluated`, `components` (exactly 11 rows), and `totals` (original classified, permitted, blocked and unresolved balances; no accepted-allocation residual in this stateless endpoint). No pension amount, tax, NPV, 161d determination or financial yield.

For **every one** of the 11 canonical codes, return canonical `component_code`, source persisted `component_id` (required and non-null in this first slice), exact decimal balance as **string**, `permission_status=allowed|blocked|needs_source_reconciliation|unknown`, `reason_code`, Hebrew explanation, and `applicable_rule_id`. The row remains visible even when its balance is zero, blocked or unknown. Missing canonical persisted rows cause an envelope-level `MISSING_CANONICAL_SOURCE` error rather than a synthetic zero/null component row. Zero is visible but not selectable for an allocation. Never conflate zero with permission. `blocked` may coexist with otherwise valid product status; `unknown` does not default to a general permission matrix.

**Closed action translation:** only `pension -> pension` and `capital_asset -> capital` for server matrix permission lookup. `leave_unallocated` is forbidden as input; residual is output only. Do not call `tax_for` to produce a tax result.

**Closed product resolver required BEFORE approving preview implementation:** product class must be determined from server-held values using an explicitly enumerated mapping table. The current `product_type.lower()` and substring matching are **not accepted** as a resolver. Map exact verified source values/aliases to canonical `pension_fund | insurance_policy | provident_fund | education_fund | investment_provident_fund` only when professional equivalence is established. The importer also provides savings-only insurance labels whose correct class is **unresolved**; neither a sixth class nor a financial permission may be inferred without review. Ambiguity/unknown/missing → `unknown_product_type` (no inferred BASE_MATRIX). An exact alias inventory from accepted source data is still missing; no guessed aliases are approved. For education/investment products, a positive row with a severance code → `needs_source_reconciliation` and no capital permission on that row.

### C. Canonical source fingerprint v1 — serialization protocol

Purpose: detect whether factual monetary source and classification changed between previews. It is **not** a persistence authorization or historical evidence signature.

Preimage is UTF-8 encoded canonical JSON (sorted keys, compact separators, `ensure_ascii=false`, Unicode NFC for strings), schema identifier `scenario-source-fingerprint-v1`. Fields: `schema`, `client_id` (integer), `product_id` (string), `product_version` (integer), `product_type` (literal persisted string), and `components` ordered in the **canonical COMPONENT_CODES sequence**, each object with `component_code`, persisted non-null `component_id` and `balance` as exact two-decimal currency string. Compute lowercase hexadecimal SHA-256 of exact UTF-8 bytes. Reject malformed/non-finite/negative money. This digest has no rule/evidence signature; keep `ruleset_digest` separate.

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

**Acceptance gate:** verify the manual frontend inputs and source dictionaries, specify the treatment of insurance and savings policies, and establish an exact reviewed type mapping including unknown/missing values and positive severance anomalies. Independent Work re-review is still required. No preview implementation, scenario save, ruleset authority change, factual data rewrite, CI, migration or deployment is authorized by this documentation.


## I. Manual-input/UI and unknown import values, verified follow-up (2026-10-23)

**Source cross-check:** `frontend/src/pages/RetirementWorkspaceScreen.tsx` displays persisted products and provides a component balance correction workflow. In `saveCorrection` it copies `product_type: product.product_type` back into the PUT request; it does **not** show a controlled type selector or enumerate aliases in that workflow. `frontend/src/api/pensionProductsApi.ts` declares `product_type: string`, not an enum. These two inspected frontend sources do not establish that no other manual-entry form exists elsewhere; a repository-wide UI input inventory is still unverified.

**Unknown-value source behavior:** `pension_product_import_service._prepare_batch` explicitly assigns `"סוג מוצר לא ממופה"` to unrecognized nonempty `SUG-MUTZAR` and `"סוג מוצר לא נמסר"` when missing. `ProductMetadata.product_type` accepts these nonempty strings; import subsequently builds a product from the resulting metadata. Therefore an unrecognized or missing source product type is **not automatically rejected by type validation**, and must not become eligible in scenario permission preview via fallback to the ordinary base matrix.

**Closed-resolver candidate inventory (source-derived, not professionally accepted):** the five persisted mapped Hebrew labels in §H, plus the two explicit fallback labels as `unknown`. Imported `source_kind` is a discriminator. Manual `product_type` remains free text; no manual alias list may be fabricated. Both missing/unknown fallbacks produce an envelope-level `UNKNOWN_PRODUCT_TYPE` for the narrow preview. Preserve the original imported code through stored source evidence when reclassifying later, without changing factual product records.

**Reviewed-class mapping status:** `קרן פנסיה` is a strong candidate for `pension_fund`; `קופת גמל` is a candidate for `provident_fund` **only**, never evidence of `investment_provident_fund`; the three insurance/savings descriptions need professional subtype review. A sixth class, or a nonconvertible/unsupported status for savings-only products, may be required. No legal/financial permission follows merely from a display label.

**Minimal acceptance tests to specify (design only):** all five importer labels, both fallback strings, unknown manually entered strings, type/name spoofing, changing source kind, an education/investment-fund severance-coded nonzero row, all 11 component rows with zeros, and client-isolation check. Verify that updating a balance in the current workspace preserves exact persisted product type. No CI run has established these test results.

**Open gate:** authoritative manual type aliases and education/investment provident product identification are unresolved. Do not authorize Preview code or scenario save until an independently reviewed resolver policy is accepted.


## J. Verified actual manual pension-product screen (2026-10-23)

Source: `frontend/src/routes/AppRoutes.tsx` routes `/clients/:clientId/pension-products` to `frontend/src/pages/PensionProductsScreen.tsx`, which was inspected directly. `PensionProductsScreen.tsx` defines `emptyMetadata().product_type = "קופת גמל"`, shows `product_type` as an ordinary free-text `<input>` in the metadata form, and applies no closed type enumeration there. It also declares a separate `productTypeLabel` formatter that displays codes `"1"` through `"5"` as Hebrew descriptions; this presentation-only formatter is not a resolver nor proof that such codes are stored in the current import flow.

**Consequences for bounded scenario design:** A manually created product may contain the initial `"קופת גמל"` default or any user-entered nonempty value accepted by backend `ShortText`. Merely retaining a default does not verify the professional subtype. The existence of a free-text input means a complete, observed manual alias *inventory cannot be derived from code alone*. For permission preview, only explicitly accepted exact labels may ever resolve to a canonical class, and any unknown or ambiguous user-entered text must produce an unresolved type, not a guessed fallback; type correction must not silently alter existing factual source records.

**Potential future UX improvement (not implementation-authorized):** supply a controlled professional type selector with an explicit unresolved/other option, and keep the original source description separately for audit and provenance. Changing the existing input or rewriting product records requires a distinct migration/compatibility and ownership review; do not implement as a side effect of the read-only preview.

**Review status:** Closed mapping for education funds and investment provident funds is still unavailable from this source; no professional rule has been invented. Independent review of the updated contract remains outstanding. No CI, domain changes or deployment.


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

**Narrow acceptance boundary for read-only permission preview:** Authenticate via existing production middleware and require a verified session actor; scope product reads by both selected client ID and server-owned product ID. In the **existing single-operator deployment only**, a valid configured professional session may access that operator's client records, conditional on owner acceptance of that operational security model. Do not claim user-specific client membership exists. In future multi-operator deployments, fail closed until a dedicated client access authorization rule has been specified and independently approved.

The preview API must not accept an actor identity from the request body, must not reimplement or bypass session validation, and must never authorize based solely on product name/type or `client_id` asserted by a browser. Production-like tests must exercise missing/invalid session, valid configured session with nonexistent or wrong-client product ID, and spoofed identity fields. Development bypass behavior is not production authorization evidence.

This does not remove the separate source-snapshot read consistency and zero-write design gate (§K), or product-type resolver gate (§H/J), nor does it authorize an implementation. **Preview review remains BLOCKED pending independent assessment.**


## M. Concrete zero-write snapshot design candidate (2026-10-23; NOT IMPLEMENTED)

Source evidence: `backend/app/db/session.py` configures SQLAlchemy `Session(autocommit=False, autoflush=False)` via `sessionmaker`; `pension_product_service.lock_client` is a deliberate *write-coordination* boundary and **must remain unchanged** for factual mutations. Production configuration requires a PostgreSQL URL. A new preview must not use `current_products`, existing `detail` route, or `lock_client` because they may acquire writer locks and, on SQLite, issue UPDATE.

**Candidate PostgreSQL read protocol for later independent review:** use a dedicated short-lived transaction with `REPEATABLE READ READ ONLY` established **before its first SQL statement**, read client/product/component data under the same snapshot with server-side client scoping, and close it without committing a mutation. No `SELECT FOR UPDATE`, advisory transaction lock, ORM flush, source audit, or call to conversion APIs. Treat source absence, structural defects and wrong-client product as errors; include component IDs and product version in fingerprint. Use documented SQLAlchemy transaction/isolation configuration rather than issuing `SET TRANSACTION` after a prior implicit transaction has started.

**SQLite test protocol:** ensure a single consistent read snapshot with a read transaction selected according to SQLite's actual transaction initiation/isolation semantics; do not assume that `autoflush=False` or SQLAlchemy session creation alone guarantees a database snapshot. No writer reservation and no UPDATE allowed. Validate with concurrent writer tests. SQLite is a test/development capability, not an excuse to weaken production consistency.

**Validation:** Capture executed SQL and assert zero DML/DDL or write-capable lock statements; concurrent factual product update cannot yield product/version from one revision and components from another; follow-up stale fingerprint is detectable. A permission preview never allocates or persists results; its response is informational.

**API method security:** proposed `POST` endpoint is an unsafe method, so production `RTDIRSecurityMiddleware` will require both exact Origin and CSRF token despite the endpoint having zero database writes. Do not bypass origin/CSRF to make the read-only operation easier. Consider GET only as a separately versioned API design decision if the input/response shape supports it.

**Review gate:** This is a bounded implementation design candidate, not evidence of tested transaction behavior and not permission to code or run CI. The independent review must choose the exact safe SQLAlchemy pattern and verify its behavior on PostgreSQL and SQLite.
