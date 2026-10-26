# RETIRE V2 | Stage 6 single-pension estimate | consolidated independent acceptance packet

**Status:** SUBMITTED FOR INDEPENDENT REVIEW, NOT PASSED. **Branch:** `feature/professional-workspace-ux-first-20261022`. Reviewer **must identify actual HEAD at review time**, not rely on the older Work judgement at 9e42741. READ ONLY. No financial execution, new code/adapter, DB changes, CI, merge, deploy.

## Precise requested verdict

Determine whether the **already existing canonical producers** can be admitted, under the owner's approved coefficient-source policy, to support only `SINGLE_PENSION_DECISION_TARGET_MONTHLY_ESTIMATE`: one saved `pension` allocation, one target date, gross nominal monthly planning estimate, with explicit coefficient provenance. Distinguish:
A. Design contract sufficiently bounded and safe.
B. Evidence/admission and canonical producer path actually supported in code.
C. Permission to implement. **A or B does not grant C.**

The previous Work Stage 6 verdict is BLOCKED. Accept nothing merely because this central conversation wrote it.

## Owner-decided requirements (do not reopen)

- Model a manager-insurance balance from the manager-insurance factor family; model pension fund/provident/education/investment provident funds using the pension-fund convention as a **planning estimate**, not legal entitlement. For pension funds, preserve comprehensive vs general variant whenever official data requires it.
- **Primary objective:** official insurer/fund **policy-and-option-specific** coefficient. The V1 generic tables are a labelled fallback compromise, not the desired product. Never use uncontrolled factor 200.
- **Mandatory planner-editable manual factor** per saved scenario pension decision, especially special spouse-survivor percentage/guarantee plans. Explicit choice and source/notes, scoped to that decision and invalidated on relevant changes. Never silently override product-wide coefficient; never change canonical balance.
- Preserve prior O-02 through O-08 and unresolved O-01 source classification. Do not resurrect SC-06B or M09/M10; no new governance.
- Product-era 1970–1991, 1991–1999, 2000, 2001, 2002–2004 and 2004–2013 are research classification, **not enough on their own** to assign contractual coefficient. Original policy vs later rider vs newly contributed tranche must stay separate.
- Coefficient source may use an exact divisor or pension per 10,000 original currency units; only an independently admitted normalization with matching units/options is permitted.

## Code facts directly inspected by central chat (review independently)

1. `backend/app/services/scenario_draft_service.py`: saved decision identifies scenario, source product/component/code, action, amount, effective date and review fingerprints. Stored draft is non-authoritative and cannot mutate canonical allocations.
2. `backend/app/services/scenario_input_manifest_service.py`: DB-derived inert manifest, with `execution_allowed=false`.
3. `backend/app/services/scenario_calculation_admission_service.py`: checks source versions and balance allocation, but currently always blocks with `PERMISSION_NOT_ADMITTED`, `PROFESSIONAL_ELIGIBILITY_NOT_EVALUATED`, `TAX_NOT_EVALUATED`. It is evidence only.
4. `backend/app/services/scenario_annuity_coefficient_assessment_service.py`: explicitly `BLOCKED` with `COEFFICIENT_LOOKUP_NOT_AUTHORIZED`. Must not be bypassed.
5. `backend/app/services/annuity_coefficient_service.py`: catalog hash/version checked, but uses implicit gender/age/target-year fallback, pension max-id row choice, and unconditional coefficient 200 for no match/error. This does NOT satisfy fail-closed scenario selection.
6. `backend/app/services/pension_monthly_basis_service.py`: `manual()` emits `manual_balance_ratio` as `exact_ratio(numerator=balance, denominator=annuity_factor)` **only for a current factual manual pension source** and ties fingerprints to its factual provenance; `conversion()` covers a persisted factual destination. These are NOT saved hypothetical scenario sources.
7. `backend/app/services/pension_target_date_execution_service.py`: accepts `exact_ratio` when the accepted source kind and five planning/monthly/temporal identities are verified. `execute_from_planning_result` requires one unique admitted `source_id` in a genuinely computed planning result; syntax-shape matching alone is not admission.
8. `backend/app/services/planning_input_service.py`: builds `pension_inputs` from canonical existing pension sources, not saved scenario decisions; potential impedance mismatch must be explicitly resolved.

## Principal unresolved issue: avoid disguised duplicate producer

There is *no demonstrated authoritative route* by which an existing hypothetical saved allocation `decision.amount` + selected policy coefficient becomes a current admitted scenario `monthly_amount_basis` with genuine producer-owned fingerprints, without creating a fake factual `ManualPensionSource` or `PensionDestination`.

Independent reviewer must either:
- exhibit an actual current canonical producer contract, source-by-source and line-by-line, that derives this **hypothetical** base monthly ratio with source authority and the required five identities, or
- rule **BLOCKED/UNSUPPORTED_BY_EXISTING_CONTRACT**, and specify the narrowest extension needed within existing canonical ownership, with an explicit professional/admission gate and no new parallel engine.

Do NOT implement this adapter as part of this review.

## Minimum review artifacts

Provide one table mapping: (a) saved decision field; (b) source producer/DB owner; (c) monthly-basis producer; (d) coefficient source and option; (e) exact timestamp/retirement target and temporal authority; (f) required fingerprint; (g) state/remaining blocker. Identify whether action-dependent blockers can be isolated to one decision instead of global veto.

Test matrix / negative cases to require before any later implementation:
- cross-client and archived/stale decision; substituted source/tranche/code; over-allocation, residual not treated as new decision; unknown product classification and source anomaly;
- catalog duplicated row, missing metadata, wrong age/sex/plan/spouse %, mismatched pension guarantee, nonmatching base-year update, wrong source representation/units; blocked 200 fallback;
- manual factor absent/invalid/negative, changed after prior approval, wrong decision, clone inherited stale approval; original policy versus rider/new-deposit mismatch;
- SC-06A documentary review, manifest and structural compatibility never self-authorize; no engine call if blocked;
- valid exact Decimal inputs but forged fingerprint or hypothetical source masquerading as real manual pension source: block; stale targets invalidate all five identities;
- read-only one PostgreSQL snapshot; no `canonical-conversions` mutation, M09/M10, fixation, tax, capital, gap, NPV, CI or deploy.

## Required review output

Verdict exactly `PASS_DESIGN_ONLY` / `BLOCKED`, with line-grounded evidence for every blocker, class `SOURCE_EVIDENCE` / `PROFESSIONAL_DECISION` / `CALCULATION_CONTRACT` / `TECHNICAL_WIRING`, named producer and smallest allowable next step. Answer separately whether scope-specific, decision-scoped manual factor and provider-specific/generic factor admission is now specifiable. **Do not convert design PASS into permission for Stage 6 code.**

**Flags stay:** `STAGE_6_IMPLEMENTATION=NOT_AUTHORIZED`, `COEFFICIENT_LOOKUP=NOT_AUTHORIZED`, `FINANCIAL_CALCULATION=NOT_AUTHORIZED`, `SCENARIO_CALCULATION_ADAPTER=NOT_AUTHORIZED`, `PRODUCTION_DEPLOYMENT=NOT_AUTHORIZED`.
