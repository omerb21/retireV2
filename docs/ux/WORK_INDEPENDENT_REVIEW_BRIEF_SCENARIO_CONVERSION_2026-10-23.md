# Work — independent audit brief: V2 scenario conversion contract

**Review mode:** INDEPENDENT, READ-ONLY. **DO NOT change code, commit, merge, deploy, migrate DB or run CI.** This document is a request package, not evidence that Work has been invoked.
**Repository:** `omerb21/retireV2`, branch `feature/professional-workspace-ux-first-20261022`.
**V1 evidence:** `omerb21/retire` on main.

## Purpose

Identify whether the proposed V2 scenario-only conversion rule contract correctly reuses V2's existing factual permission matrix without conflating factual conversions, mock UX, retrospective M06/M09 data and new scenario decisions. Assess completeness of legal/business gates and whether an eligible-only *explicit reviewed subset* can safely be selected for an otherwise mixed whole-plan preview.

## Read these sources first

- `docs/ux/V2_DEVELOPMENT_MANAGEMENT_PLAYBOOK.md`
- `docs/ux/V1_TO_V2_CONVERSION_RULES_GATE_2026-10-23.md`
- `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md`
- `docs/ux/SCENARIO_ENGINE_INTEGRATION_GATE.md`
- `backend/app/services/canonical_conversion_matrix.py`
- `backend/app/services/canonical_component_conversion_service.py`
- `backend/app/models/pension_product.py`
- `backend/app/services/m06_conversion_service.py`
- `backend/app/services/m09_scenario_subject_service.py`
- `frontend/src/pages/mockConversionEligibility.ts`
- V1: `app/services/pension_portfolio/conversion_rules.py`, `frontend/src/config/conversionRules.ts`, `frontend/src/pages/PensionPortfolio/hooks/usePensionConversion.ts`

## Audit questions (supply evidence paths/lines)

1. Produce 11 canonical-code × 2 destination **permission diff**: V1 backend vs V2 server, plus product-type overrides and unknown-type handling. Classify true discrepancies vs intended V2 improvements.
2. Distinguish permission, professional eligibility, tax treatment and financial calculation. Explicitly compare V1 frontend configurable tax classifications with V1 backend and V2 matrix; **do not infer tax law**.
3. Inspect existing factual whole-product conversion: does it skip restricted positive components, and does the preview accurately reveal excluded amounts? What could cause an owner misunderstanding?
4. Review proposed safe batch behavior: unreviewed mixed whole-plan request fails closed; explicit reviewed eligible subset may proceed only as enumerated component decisions with versioned authority. Identify TOCTOU/staleness, rounding, concurrency and duplicated-allocation risks.
5. Is the existing `M09ScenarioSubject` domain structurally compatible with pension product allocations, or should there be a separate versioned scenario decision aggregate? Do not assume matching terminology implies matching semantics.
6. Identify required severance-history, employment termination, settlement, product type, dates, exemptions, 161d, coefficient prerequisites and the proper scope of V1's global unsettled-severance blocker.
7. Test design: cross-client access, stale version, unknown source code/product, mixed-rule whole plan, unauthorized endpoint bypass, source immutability, rollback of a rejected batch, changed rule versions and stale results.
8. Specify the narrowest viable implementation slices and identify where owner professional decisions, existing governance acceptance or later official tax inputs are required.

## Expected output

- Verdict per domain: `SUPPORTED`, `CONFLICT`, `INSUFFICIENT_EVIDENCE`, `OWNER_DECISION_REQUIRED`.
- Table of critical blockers with citations (file paths/line ranges), impact, and minimal safe remediation.
- Corrections needed in the proposed contract; separate **confirmed source facts** from reviewer assumptions.
- A bounded Codex implementation plan only after contract approval, preserving source-data immutability.
- Clear explicit declaration that this is **independent Work review** and whether any tools/actions changed repository state. No invented test results.

**Do not treat these as previously approved:** assistant-proposed eligible-subset behavior, tax mapping, persistence policy, automatic rejection of unrelated planning on unsettled severance, or UI mock permissions as authoritative.
