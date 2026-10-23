# V1 → V2 mandatory component conversion rules gate

**Date:** 2026-10-23 · **Status:** V1 evidence checked; V2 UX-MOCK preview guard implemented; **authoritative V2 server validation NOT IMPLEMENTED/NOT ACCEPTED**.

## Source inspection

Read in `omerb21/retire` (`main`):
- `app/services/pension_portfolio/conversion_rules.py` (backend component permissions, pension/capital tax category and product-type overrides)
- `frontend/src/config/conversionRules.ts` (modifiable browser-side default matrix and validation)
- `frontend/src/components/system-settings/ConversionSettings.tsx` (editable permissions/taxes/messages)
- `frontend/src/pages/PensionPortfolio/hooks/usePensionConversion.ts` (conversion entry point with additional unresolved severance block).

**Crucial:** V1's frontend uses localStorage and may be edited through settings; certain frontend tax labels differ from the current backend matrix (e.g. `תגמולי עובד עד 2000` pension tax). The in-browser matrix must NOT silently be treated as the single legal authority. The server-side rules and approved professional overrides require an explicit reconciliation gate before V2 business implementation.

## V1 backend permission matrix for 11 classified V2 source columns

| Classification | Pension conversion | Capital conversion | Main gating reason |
| --- | --- | --- | --- |
| פיצויים מעסיק נוכחי | NO | NO | employment termination process prerequisite |
| פיצויים לאחר התחשבנות | YES | YES | taxed according to separately defined treatment |
| פיצויים שלא עברו התחשבנות | NO | NO | settlement required |
| פיצויים מעסיקים קודמים רצף זכויות | NO | NO | external settlement prerequisite |
| פיצויים מעסיקים קודמים רצף קצבה | YES | NO | capital prohibited |
| תגמולי עובד עד 2000 | YES | YES | subject to classification and tax |
| תגמולי מעביד עד 2000 | YES | YES | subject to classification and tax |
| תגמולי עובד אחרי 2000 | YES | NO | capital prohibited |
| תגמולי מעביד אחרי 2000 | YES | NO | capital prohibited |
| תגמולי עובד אחרי 2008 לא משלמת | YES | NO | capital prohibited |
| תגמולי מעביד אחרי 2008 לא משלמת | YES | NO | capital prohibited |

**Exception:** The V1 backend applies product-type overrides to education funds / investment provident funds before the field table, and handles aggregate `תגמולים` separately based on product type. V1 also has a special `קרן_השתלמות` classification not included among the current 11 V2 source columns. These overrides must be investigated and professionally accepted; don't assume every apparent exemption always applies to every source component.

## Essential architecture for authoritative V2 scenarios

1. Define accepted central server-side immutable/versioned rules for `(classification, product_type, action, scenario effective date)`, including preconditions such as employment settlement and reconciliation. Tax treatment is a separate output requiring independent acceptance.
2. The scenario-only decision must never call V2 `POST /canonical-conversions` to mutate factual balances. Keep factual ledger untouched.
3. The authoritative scenario mutation/evaluation API must reject illegal choices **server-side**, even when the frontend is bypassed. Error should identify the source, attempted action and relevant rule, avoiding unsupported claims about legal tax eligibility.
4. For whole-plan conversions, expand into component-specific evaluations first; any forbidden component must be excluded with explicit informed choice **or** block the bulk operation per approved design. Never silently convert all mixed categories as though identical.
5. Unknown classifications/products, invalid rule version, missing settlement documentation or irreconcilable grant facts must **fail closed**. No fabricated tax/pension/NPV.
6. Tests: one matrix test for each of 11 columns × 2 actions, product override cases, whole-plan mixed-eligibility cases, negative/over-allocation, bypass of client, client isolation, source-version race and scenario independence. Contract and accepted tax outcomes require Work review before merge.

## Limited change introduced on isolated UX branch

Added `frontend/src/pages/mockConversionEligibility.ts` and focused tests for **UX-MOCK rejection only**, mirroring the *V1 backend permissions* for 11 columns plus its investment/education product overrides. The mock UI now shows an explicit blocking error before recording a disallowed demo action. The `unchanged` choice remains an unconverted illustration, not a legally authorized conversion.

This **is not authoritative V2 server enforcement** and must not be used as proof of legal suitability or production readiness. Independent Work audit and Codex-managed real-domain implementation remain pending. This stage does not write the DB or enact any pension conversion.
