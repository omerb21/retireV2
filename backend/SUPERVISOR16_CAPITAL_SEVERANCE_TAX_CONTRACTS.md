# RETIRE V2 | Supervisor 16 | Capital, Severance and Fixation integration decision record

Baseline: `dd3d04b23135a625f814d7738222b1928a560881`. This document is an
implementation proposal, not professional tax policy or authorization to
execute new financial calculations.

## Real engine results and the admitted scenario scope

The approved Package-1 contract identifies `client_id`, `scenario_id`,
`scenario_version`, target/planning dates, canonical source versions and
fingerprints. The Package-2 binding reuses existing Stage 6 P1C/P1D pension
and monthly gross cashflow extensions in the *same* PG16 REPEATABLE READ
READ ONLY snapshot. Synthetic positive proof is added to
`test_stage6_p1d_postgresql.py`: factor admitted through the existing
`append_authenticated_serializable_factor_admission`, expected pension
aggregate 4.00 ILS and monthly gross income 1204.00 ILS (4.00 pension plus
1200.00 independent recurring income), with a changed election route
invalidating the former result.

P1D is explicitly a nonbinding estimate, not an insurer commitment;
`NONBINDING_ESTIMATE` must not be rendered as professional pension approval.
A user-supplied coefficient outside the admitted, version-bound evidence
mechanism must never be read as authority.

## Capital, holdings and withdrawals

**Reusable producer:** `capital_projection_execution_service.read(db,client_id)`
based on `planning_input_service.derive` and
`capital_projection_basis_service.derive`. It produces the contract
`canonical-pre-retirement-capital-projection-execution-v1`, including
planning input, projection basis admission, execution fingerprints, covered
source IDs, result fingerprints, base and target dates. This is currently
**CLIENT-LEVEL**, not scenario-specific. M06 conversion revisions are
ARCHIVE-ONLY; they must not execute hypothetical withdrawals.

**Proposed input:**
`client_id, scenario_id, scenario_version, planning_calculation_input_fingerprint,
source_product_id, component_id, source_fingerprint, product_version,
decision_id, action in {capital_asset,pension}, amount, effective_date,
source_statement_date, planning_base_date, retirement_target_date,
projection_basis_admission_fingerprint, tax_treatment_evidence`.
The decision must bind source component and exact amount under the existing
allocation/CAS rules. For a non-pension financial asset also bind the
canonical capital-asset ID and verification state.

**Proposed output:**
`source_id, decision_id, scenario_id, scenario_version, amount_original,
amount_projected, amount_withdrawal_requested, amount_withdrawable_verified,
remaining_projected_amount, withdrawal_date, source_reference_date,
projection_result_fingerprint, scenario_allocation_fingerprint,
comparison_basis, result_state, blockers`. Missing approved liquidity,
capitalization eligibility, return basis or tax evidence => null, not zero.
No canonical withdrawal or balance mutation occurs.

**Deduplication:** bind all pension and capital decisions to a canonical
`(product_id, component_id)` source ledger and never sum gross source balance
plus the post-allocation asset as two holdings. Allocation across decisions
cannot exceed the original canonical component; a pension allocation and a
capital allocation consume the same capacity. A projection is not cashflow
unless an authorized actual withdrawal event is modeled.

**Current support:** client-level projection of approved capital sources.
**Not authorized yet:** per-scenario withdrawal/commutation, current M06
conversion execution, tax effects, projected balance updates. All remain
`BLOCKED` in the active unified result.

**Professional decisions required:**
1. Define legal/contractual eligibility for capital withdrawal/commutation
   by product/component, and the required documentary evidence.
2. Define projection assumption ownership, base/target date normalization,
   fees, returns, inflation and permitted approximation methods.
3. Define cash availability, payment date, and whether a taxable event
   occurs; distinguish a planned action from an executed transaction.
4. Approve double-count rules when a pension amount and a capital decision
   originate from the same component, including existing settlement history.

## Severance, employment records and retirement grants

**Reusable source and engine:** canonical `EmploymentRecord`, `Grant`
and `ActualCapitalization` models, client grants endpoints and
`fixation_admission_service` with `fixation_engine`. Historical M05/M06
evidence may be read, never treated as a new scenario decision authority.

**Proposed input:**
`client_id, scenario_id, scenario_version, employment_record_id, grant_id,
employer_end_date, payment_date, grant_amount, grant_source_fingerprint,
grant_verification_state, decision_kind, eligibility_evidence,
continuity_election_reference, already_paid_or_future, tax_year,
compensation_component_source_ids`.
Historical disbursement and future elected grant must be separate types.
Rollover/continuity decisions require approved evidence and applicable date.

**Proposed output:**
`grant_id, decision_id, event_date, historical_paid_amount,
prospective_grant_amount, cash_payable_verified, preserved_or_deferred_amount,
taxable_grant_amount, exempt_grant_amount, source_fingerprints,
calculation_version, result_state, blockers`.
All professional/tax fields are null until an authoritative engine supplies
them. A historical received grant is not a future cashflow contribution.

**Current support:** client-level employment and grant collection, historical
settlement and fixation grant calculation where admitted.
**Not authorized:** automatic scenario choice of continuity, severance
exemption, or cash payment.

**Professional decisions required:**
1. Which grant/continuity states are supported first, including sequences
   and employer separations and prior severance settlements?
2. Required Form 161/161A or other evidence, source verification and
   historical grant inclusion rules; how to reconcile clearinghouse
   severance components with employer-provided totals?
3. Whether a future grant is recognized as cash, preserved in a pension
   product, or excluded, with payout/eligibility dates and priority rules.

## Fixation, tax and net income

**Reusable producer:** `fixation_service.calculate_fixation_payload`,
`fixation_service.assemble_fixation_input`,
`fixation_admission_service.parse_and_admit_fixation_payload`,
`fixation_engine`, `fixation_m07_service`, and the official parameter
resolver. Prior saved `FixationRun` results do not prove current,
scenario-specific rights or an Israel Tax Authority approval.

**Proposed input:**
`client_id, scenario_id, scenario_version, taxable_year,
eligibility_date_verified, entitlement_basis, approved_official_parameter_set,
qualifying_pension_classification, pension_gross_source_fingerprints,
historical_exempt_grants, proposed_future_grants, actual_capitalizations,
proposed_future_commutations, indexed_amounts_with_method,
tax_status_evidence, fixation_revision_id_if_any`.
Every item must carry paid-versus-proposed distinction, dated preimage and
professional verification state. The tax-year authority must be explicit.

**Proposed output:** three distinct and non-interchangeable states:
`TAX_SIMULATION_NOT_AUTHORITY`,
`FIXATION_CALCULATED_NOT_TAX_AUTHORITY_APPROVED`,
`TAX_AUTHORITY_APPROVAL_VERIFIED`.
Result fields are `eligible_pension_gross, calculated_monthly_exemption,
grants_offset_effect, capitalization_offset_effect, taxable_pension,
tax_year, parameter_set_id, assumptions_and_exclusions, lineage,
result_fingerprint, blockers` as produced by existing admitted engines,
not by the unified wrapper.

A complete **NET** result additionally requires the applicable personal
income-tax engine and full tax base (employment/other taxable income,
credits, withholding/coordination, resident/status rules, inflation/index
conventions, payment frequencies, and dates). There is no approved
scenario-specific full-net engine contract; `net_income` stays BLOCKED.

**Current support:** the existing client-scoped fixation workflows and
separately recorded professional evidence.
**Not authorized:** taking a prior fixation calculation or status and
assigning its exemptions to an alternative, automatic tax bracket selection,
new rate formulas or invented net income.

**Professional decisions required:**
1. Minimum eligibility evidence and explicit authority to treat a pension
   as qualifying under the relevant tax year and law.
2. Whether the first release supports simulated fixation only, already
   approved fixation only, or both with separate visible statuses.
3. Parameter set/version, pension/grant tax classifications, historic
   grants indexation, reserved future grants and capitalization choices.
4. Scope and authoritative source of the complete personal net-tax
   calculation. Until approved, net results remain null.

## Integration dependency and stop condition

1. Admit source identifiers, amounts and scenario allocations with full
   fingerprints and no double counting.
2. Bind approved per-scenario capital and grant result contracts.
3. Reuse the existing fixation engine with a scenario-to-fixation
   eligibility/evidence adapter, separately distinguish calculated rights
   from actual government approval.
4. Only then approve legally supported net tax + monthly outgoing withdrawals
   and expenses, with target-date consistent price bases.
5. Re-run the synthetic end-to-end and verify no current result survives
   mutation of its dependency preimage.

Do not implement steps 1-4 until the supervisor approves the professional
contract choices above. No package 3 work follows from this analysis.


## Supervisor 19 implemented integration boundary

Added `scenario_financial_evidence_service.collect_scenario_financial_evidence`
to the existing `build_unified_scenario_engine_bindings` read-only snapshot.
The response now has `financial_evidence` (capital, severance,
fixation_tax), separate from `domain_results`. Package 1 base identity,
versioning, pension Stage 6 and gross cashflow execution are unchanged.

Each factual evidence domain includes `client_id`, `scenario_id`,
`scenario_version`, `evidence_fingerprint`, and explicit blockers.
The overall unified envelope hash also includes all newly read facts.

**Capital:** source-component decisions have one source ledger keyed by
`(product_id, component_id)`. Their planned exact amounts and effective
dates are recorded along with source and dependency fingerprints, and
over-allocation raises `CAPITAL_SOURCE_OVERALLOCATED`. Canonical capital
assets are read once, kept separate from scenario allocations, and retain
their reported value and valuation date. The existing client-level Capital
Projection is referenced as a producer contract, but not invoked or
reclassified as an admitted scenario projection. It owns an independent
`begin_read` transaction boundary and cannot safely be called inside the
already active unified snapshot. A future same-snapshot capital adapter must
reuse the engine's validated `planning.derive`, `basis.derive`,
`execute` primitives with their complete source coverage and without
opening another transaction. The current evidence layer has
`available_to_withdraw_ils=None` and never records a cash payment.

The factual capital adapter also reads canonical
`CapitalProjectionBasisDecision` rows when present, including exact
return assumption and its original planning, timing and source
fingerprints. They are explicitly labeled
`CLIENT_LEVEL_BASIS_NOT_SCENARIO_ADMITTED`; the calculation engine is
not silently invoked and no projected capital is added to spendable cash.

**Severance:** historical employment records and grants are joined by
explicit employment IDs and client ownership. Monetary figures are labeled
`reported_nominal_amount_ils` or `reported_indexed_amount_ils`, never
tax-exempt or already paid. Every grant has
`payment_classification=UNKNOWN_NOT_VERIFIED`; historical payment, future
claim and continuity elections cannot be inferred from a dated grant.

**Fixation/tax:** factual records include historical actual capitalization
entries and prior `FixationRun` calculation *references* only.
A historical successful calculation is not a current scenario computation
and is not an official determination. No tax exemption, personal income tax
or net result is generated. Fields `scenario_tax_year`,
`scenario_eligibility_admission`, `scenario_fixation_result` and
`tax_authority_approval` remain null. Positive domain result remains
BLOCKED, with `professional_authority=False`.

All factual amount fields are original client/source records, not predicted
cash amounts. No canonical balance, pension allocation, grant or fixation
record is modified by the integration.

**Acceptance evidence to run locally:** existing real PG16 package-2 fixture
now creates the exact extra source FK tables (canonical conversion batches
and conversions for the asset FK, capital assets, employment records, grants,
actual capitalizations and fixation runs). Tests cover source uniqueness and
over-allocation, scenario and client isolation, grant edits invalidating the
unified fingerprint, and the absence of invented payout or tax authority.
These tests are NOT RUN in the executor environment.

**Still requires separate implementation:** genuinely admitted
scenario-specific Capital Projection results; legally admissible withdrawal
and severance election contracts; scenario-specific fixation calculations
with entitlement evidence and official tax parameters; full personal-net
tax engine; authorized monthly outflow and expenses. No historical M06/M09
execution path is reopened. No decision about tax eligibility is implied.
