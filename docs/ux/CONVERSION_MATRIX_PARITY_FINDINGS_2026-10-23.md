# V1 ↔ V2 conversion matrix parity — direct code comparison

**Method:** direct in-chat static source inspection, 2026-10-23. **Not** independent Work audit, runtime execution, legal opinion or acceptance of scenario engine.

## Evidence
- V1 `omerb21/retire` `main:app/services/pension_portfolio/conversion_rules.py` `COMPONENT_RULES` / `validate_component_conversion`
- V2 UX branch `backend/app/models/pension_product.py` `COMPONENT_CODES`
- V2 `backend/app/services/canonical_conversion_matrix.py` `BASE_MATRIX` and `destinations`
- V2 `backend/app/services/canonical_component_conversion_service.py` `_preflight`
- V1 `frontend/src/config/conversionRules.ts` editable browser-side matrix.

## 11-code permission parity for ordinary pension/insurance product types

| Canonical component | V1 pension | V1 capital | V2 pension | V2 capital | Result |
| --- | --- | --- | --- | --- | --- |
| פיצויים_מעסיק_נוכחי | N | N | N | N | MATCH |
| פיצויים_לאחר_התחשבנות | Y | Y | Y | Y | MATCH |
| פיצויים_שלא_עברו_התחשבנות | N | N | N | N | MATCH |
| פיצויים_ממעסיקים_קודמים_רצף_זכויות | N | N | N | N | MATCH |
| פיצויים_ממעסיקים_קודמים_רצף_קצבה | Y | N | Y | N | MATCH |
| תגמולי_עובד_עד_2000 | Y | Y | Y | Y | MATCH |
| תגמולי_עובד_אחרי_2000 | Y | N | Y | N | MATCH |
| תגמולי_עובד_אחרי_2008_לא_משלמת | Y | N | Y | N | MATCH |
| תגמולי_מעביד_עד_2000 | Y | Y | Y | Y | MATCH |
| תגמולי_מעביד_אחרי_2000 | Y | N | Y | N | MATCH |
| תגמולי_מעביד_אחרי_2008_לא_משלמת | Y | N | Y | N | MATCH |

This is a *source-level* equivalence of permission booleans in the base matrix; there has been no programmatic cross-repository test or exhaustive review of effective-date legal requirements.

## Tax mapping and override findings

- Ordinary-product V1 **backend** tax labels for the 11 codes appear identical to V2's `BASE_MATRIX` (where destination is allowed), including `תגמולי_עובד_עד_2000` and `תגמולי_מעביד_עד_2000` pension treatment = `taxable`.
- V1 **frontend** `conversionRules.ts` marks those same pre-2000 contributions' pension tax = `exempt`. **CONFIRMED CONFLICT between V1 front-end defaults and both backends**; must not assert either is professionally correct from code inspection alone.
- V1 backend `validate_component_conversion` applies education/investment product-type overrides before component restriction; V2 `destinations` also applies these overrides first. The effective **ordinary vs exempt product-class** matching logic should be tested with exact V2 product type strings; do not broaden the override by guessing product names.
- V1 has a separate aggregate `תגמולים` and `קרן_השתלמות` column; V2's canonical ledger has 11 columns only. These cannot be mapped to new V2 canonical codes without an accepted model change.

## Critical batch semantic divergence

The factual V2 `canonical_component_conversion_service._preflight` branch `whole_product=True` collects disallowed **positive** components as `skipped` while preparing allowed components for conversion; explicit `selections` call `tax_for` and reject invalid destinations. The factual `execute` path must **never** be called as scenario creation. The scenario contract must require an explicit, reviewed list of chosen allowed components and revalidate it atomically. Do not infer that V2's present whole-product mutation behavior is accepted UX for hypothetical scenarios.

## Additional safety findings

- V2 `destinations` calls `product_type.lower()` directly. The database column is required for persisted product rows, but scenario-facing validation still needs to reject missing/invalid product type inputs *explicitly* before this function, rather than treating missing values as valid.
- V2's matrix includes a `MATRIX_VERSION` identifier; that alone does not provide temporal, legal or historical-rule version management for saved scenarios.
- Existing V1 global unresolved-severance block is outside its component rule matrix. Need owner decision on its applicability to an unrelated V2 scenario decision; do not mechanically apply globally.
- Static UI guard added to V2 is a hint only. It is not authoritative tax treatment, source-version verification or security boundary.

## Review conclusions

**Supported:** permission parity for canonical 11 ordinary-product components; V2 already has server-side permission authority for factual conversions.
**Conflict:** pre-2000 pension tax labels in V1 frontend vs V1/V2 backend; whole-product `skip` semantics vs proposed reviewed scenario subset.
**Insufficient evidence:** authoritative tax/legal correctness, complete product override matching, historical settlement applicability, scenario engine compatibility.
**Owner decision required:** eligible-only selection confirmation, outstanding severance scope, rule authority/editing rights, residual handling.
**Not performed:** independent Work review, Codex scenario-domain implementation, runtime backend tests.

Next bounded work is independent read-only Work examination of the evidence pack, then owner/domain gate, then Codex implementation against an accepted scenario-specific backend contract. No production merge on this report.
