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

## Second-pass independent Work audit addendum — after owner decisions (2026-10-23)

**Scope:** Re-review the latest branch HEAD (record SHA at start). Compare with the **prior independent Work verdict BLOCKED** (findings SCV-001…SCV-010). This addendum **does not launch Work** and is not a passing verdict. Remain READ-ONLY: no writes, CI, DB, deploy or merge.

**Updated owner approvals (binding business instructions):**
- O-02: pensions derived from pre-2000 employee and employer contributions are **tax-exempt**, as V1 frontend classifies them. The current V1/V2 server `taxable` labels conflict with this professional ruling and must not be treated as authoritative scenario tax outputs.
- O-03: whole-plan review displays **all** components; an expressly reviewed eligible subset can be submitted without silent pruning.
- O-04: **one grouped acknowledgment** after showing the full exclusion list and the individual reason for every excluded component.
- O-05: unallocated balance is **automatically computed residual**, not a separate conversion decision.
- O-06: unresolved severance blocks only affected components/actions and proven dependencies, not unrelated contributions across the whole scenario.
- O-07: rule changes require explicit system owner approval or express delegation to a qualified professional; preserve effective dates, immutable history and prior results.
- O-08: missing evidence blocks only dependent actions; show missing field, reason, evidence source and provenance.
- O-01: owner clarified education funds and investment provident funds **do not have severance components**. Product-specific exception exists to allow capital conversion when balances appear in varying *contribution* columns. A severance-coded row in these products is an anomaly needing resolution, not a genuine legal severance override. Exact closed product resolver and anomaly status require verification.

**Required re-review table:** for each SCV-001…SCV-010, state `RESOLVED_BY_OWNER_POLICY`, `RESOLVED_BY_CONTRACT_ONLY`, `STILL_OPEN`, or `NEW_CONFLICT`, with contract section, source path and evidence. Distinguish accepted policy from implemented/verified control.

**High priority re-review questions:**
1. Have newly appended contract §§15–23 introduced contradictions with old text asserting `O-03`/other owner choices are still pending, or inconsistent `whole_product` semantics? Flag exact outdated sections and proposed redline.
2. Is product-classification policy O-01 correctly reflected, including fail-closed unknown/ambiguous product types and the difference between legitimate contribution columns and impossible severance-coded rows?
3. Does O-02 tax exemption decision eliminate the policy uncertainty **without** hiding the remaining server code mismatch? Demand an isolated implementation/remediation plan rather than premature tax output.
4. Do O-03/O-04 preserve explicit reviewed group consent across any changed preview fingerprint, exclusion reasons, source and rule version?
5. Does O-05 residual calculation account for all accepted decisions across one scenario and avoid double counting/stale source when showing totals?
6. Do O-06/O-08 truly limit blockers by source component/action with authoritative dependency provenance and missing-vs-not-applicable distinction?
7. Does O-07 have a complete rule lifecycle and explicit authority/delegation checks, including historical version replay and non-retroactive results?
8. Is a closed transaction protocol fully specified for a **separate scenario aggregate**: source identity, component_id, fingerprint, locks, CAS, idempotency, rollback, cross-client security and no factual ledger writes?
9. Can a **read-only permission-only** server preview be independently authorized as a narrow first slice without implying tax approval or save authority? Specify exact preconditions, if yes.
10. Which of O-01 anomaly, professional evidence producer mapping and remaining open technical decisions still require owner action rather than Codex engineering judgment?

**Verdict requested:** (a) policy readiness, (b) contract consistency, (c) readiness for *read-only permission preview only*, (d) readiness for authoritative scenario save, separately as PASS/BLOCKED with evidence. Do not give a single blanket PASS and do not state implementation was authorized unless explicitly approved by the owner.

**Inputs for this re-review:** `docs/ux/SCENARIO_CONVERSION_OWNER_DECISION_REGISTER_2026-10-23.md`, `docs/ux/V2_SCENARIO_CONVERSION_ENFORCEMENT_CONTRACT_DRAFT_2026-10-23.md`, `docs/ux/CONVERSION_MATRIX_PARITY_FINDINGS_2026-10-23.md`, `docs/ux/V2_CHAT_HANDOFF_2026-10-22.md` (latest sections), V1 and V2 sources referenced earlier.
