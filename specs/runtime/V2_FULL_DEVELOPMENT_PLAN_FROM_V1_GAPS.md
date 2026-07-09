# V2 Full Development Plan From V1 Gaps

Package: V2-IAP-02D_ORIGINAL_DELIVERABLE_COMPLETION
Status: PLANNING_EVIDENCE_ONLY
Repository HEAD reviewed: 569441bbf52a052349c0ac5bac31ce110632edde

## Planning Assumptions

1. This document completes a planning deliverable only. It does not authorize implementation.
2. V1 reference evidence identifies possible capability surface. It is not V2 implementation authority.
3. Current V2 authority is bounded by accepted repository artifacts, package completion reports, tests, and current project-state documentation.
4. IAP-02C records that implementation planning is not authorized for a new feature milestone without an explicit future decision.
5. This plan therefore separates:
   - already accepted V2 baseline capabilities,
   - V1 capabilities that are partially represented in V2 foundations,
   - V1 capabilities that are explicitly excluded from current scope,
   - V1 capabilities needing later authority before implementation planning.

## Evidence Inputs Used

| Artifact | Use |
|---|---|
| specs/reference/v1_discovery_full.md | V1 reference capability surface, entry points, data structures, formulas, business rules, dependencies, and output contracts. |
| specs/reference/v1_usage_rules.md | V1 reference usage boundaries. |
| CURRENT_PROJECT_STATE.md | Current V2 milestone state, closed packages, excluded current-scope capabilities, and future discovery requirement. |
| specs/acceptance/package_acceptance_standard.md | Package acceptance and evidence requirements. |
| specs/runtime/platform_runtime_baseline.md | Current V2 route inventory and baseline runtime status. |
| specs/runtime/IAP_01B_6_completion_report.md | Final validation status after IAP-01B split packages. |
| specs/runtime/IAP_02A_next_target_selection_report.md | Prior next-target selection evidence. |
| specs/runtime/IAP_02A_source_trace_register.md | Source trace supporting next-target analysis. |
| specs/runtime/IAP_02B_next_milestone_discovery_report.md | Candidate milestone discovery and missing authority analysis. |
| specs/runtime/IAP_02B_authority_lock_register.md | Authority conclusion that no approved next milestone existed at that point. |
| specs/runtime/IAP_02B_candidate_scope_matrix.md | Candidate direction scope/risk/exclusion matrix. |
| specs/runtime/IAP_02C_product_decision_report.md | Product decision outcome and implementation planning authorization status. |
| specs/runtime/IAP_02C_next_milestone_scope_register.md | Next-milestone scope boundary evidence. |
| specs/runtime/IAP_02C_decision_question_answers.md | Decision checklist answers and blocked/unanswered scope items. |
| backend/tests and frontend/src test files | V2 implementation evidence for accepted baseline and V2.1 packages. |

## Current V2 Baseline

### Accepted and Implemented

The current V2 baseline includes:

- Client identity/profile foundation.
- Professional facts for Fixation Rights: employment records, grants, and actual capitalizations.
- Fixation input review, validation, source-to-input conversion, calculation, saving, immutable run snapshots, latest/history/detail retrieval, planner-review context, internal planner judgment, and saved input explainability.
- Fixation workflow UI: workspace, input, result, history, run detail, and source fact maintenance screens.
- V2.1 internal retirement-planning facts foundation: pension holdings, capital assets, recurring incomes, recurring expenses, retirement timing/work intentions, planner assumptions, advisory missing information, and consolidated internal review.
- Pension holding analysis record foundation.
- Governance, acceptance, and runtime validation artifacts.

### Partially Represented

The current V2 baseline partially represents these V1-adjacent areas:

- Separate grant-effect, cap, eligibility, and exemption-summary utility route parity.
- Source/verification lifecycle rules beyond currently accepted fields.
- Clearinghouse snapshot metadata without import/OCR/integration authority.
- Document metadata without generation/OCR/client-output authority.
- Pension analysis foundation without authorization for a full pension portfolio review or recommendation workflow.

### Explicitly Excluded or Not Authorized

Current evidence excludes or withholds authority for:

- Full pension holdings review as a client-facing or recommendation workflow.
- Tax planning.
- Retirement cashflow calculation.
- Retirement scenario modeling and scenario comparison.
- Broad capital-asset planning.
- Recommendation recording, execution follow-up, and periodic review.
- Client-facing 161D output.
- LLM/chat/tool-driven calculations and recommendations.
- OCR/import/clearinghouse integration.
- Report/PDF/client-facing output generation.

## Gap Groups

### Gap Group A: V2 Baseline Maintenance

Capabilities:

- V1-CAP-001 through V1-CAP-008.
- V1-CAP-011 through V1-CAP-021.
- V1-CAP-022 through V1-CAP-026.
- V1-CAP-028 through V1-CAP-029.
- V1-CAP-042.

Classification:

- EXISTS.

Development plan:

- No new implementation package should be created from this group.
- Future work should be maintenance-only unless a later package explicitly changes the accepted contract.
- Regression evidence must continue to include backend tests, frontend tests, frontend build, governance status, and package acceptance evidence.

### Gap Group B: Route-Level Parity Decisions

Capabilities:

- V1-CAP-009 Grant effect endpoint.
- V1-CAP-010 Caps, eligibility date, and exemption summary utility endpoints.

Classification:

- PARTIAL.

Development plan:

- Do not implement route parity automatically.
- First determine whether current V2 contract intentionally centralizes these behaviors inside fixation validate/calculate/save flows.
- If a future package authorizes explicit utility routes, define one clear route contract per route, then add targeted API and acceptance evidence.

Required evidence before work:

- Current route inventory.
- Existing engine/contract behavior.
- Explicit route authority.
- Targeted tests proving the route contract and failure behavior.

### Gap Group C: Source, Verification, Document, and Clearinghouse Foundations

Capabilities:

- V1-CAP-027 Source and verification status.
- V1-CAP-031 Clearinghouse snapshots.
- V1-CAP-032 Retirement planning document metadata.

Classification:

- PARTIAL.

Development plan:

- Preserve existing bounded metadata/fact contracts.
- Do not implement imports, OCR, external clearinghouse integration, source lifecycle expansion, or document generation without a later authority package.
- A future source-authority package must define source-of-truth rules, allowed data provenance states, failure modes, and audit requirements.

Required evidence before work:

- Scope register defining metadata-only versus integration behavior.
- Explicit exclusions for OCR/import/report generation when not authorized.
- API tests that still reject unauthorized fields/routes.

### Gap Group D: Pension Analysis and Portfolio Review

Capabilities:

- V1-CAP-030 Pension holding analysis record.
- V1-CAP-033 Full pension portfolio review and projection.

Classification:

- PARTIAL for the analysis-record foundation.
- NEEDS_DECISION for full pension portfolio review/projection.

Development plan:

- Keep the current pension holding analysis record as a foundation only.
- Do not infer full portfolio review, projection, recommendation, or client-facing output authority from the existence of pension facts or analysis records.
- A future package must first choose a product direction and decide whether the audience is internal planner-only or client-facing.

Required evidence before work:

- Decision on intended user/audience.
- Decision on whether calculations are authorized.
- Decision on whether recommendations or client-facing output are authorized.
- Acceptance tests for the exact selected contract.

### Gap Group E: Calculation Engines Beyond Approved Fixation Scope

Capabilities:

- V1-CAP-034 Tax calculation and tax planning.
- V1-CAP-035 Retirement cashflow calculation.
- V1-CAP-036 Scenario execution and comparison.
- V1-CAP-037 Scenario commutation exemption allocation.
- V1-CAP-040 External CPI/CBS/indexation integration.

Classification:

- EXCLUDED or NEEDS_DECISION.

Development plan:

- Do not implement calculations in this group from the current plan.
- Before any calculation work, define formulas, assumptions, data dependencies, audit behavior, error handling, and acceptance evidence.
- Treat legal/tax and client-reliance implications as high risk.

Required evidence before work:

- Formula/source authority.
- Golden cases.
- Deterministic engine tests.
- API tests.
- UI tests if exposed.
- Documentation of assumptions and limitations.

### Gap Group F: Advice, LLM, Reports, and Client-Facing Output

Capabilities:

- V1-CAP-038 LLM/chat/tool-driven calculations and recommendations.
- V1-CAP-039 PDF/report/161D/client-facing output.

Classification:

- EXCLUDED.

Development plan:

- Do not implement this group unless later explicitly authorized.
- Internal planner review evidence is not client-output authority.
- If reopened, require output contract, source traceability, auditability, rendering verification, and clear user/audience decision.

Required evidence before work:

- Output contract.
- Review/approval workflow.
- Rendering evidence for PDFs/reports if applicable.
- Safety and audit evidence for LLM/tool behavior if applicable.

### Gap Group G: Unknown Administration/Settings Surface

Capabilities:

- V1-CAP-041 Administration/settings/table editing.

Classification:

- UNKNOWN.

Development plan:

- Do not implement without locating stronger V1/V2 evidence.
- If future evidence shows this is required, decide whether mutable settings are allowed, who can edit them, and how calculation reproducibility is preserved.

Required evidence before work:

- Source evidence.
- Scope authority.
- Audit and permission requirements.
- Regression tests proving reproducibility.

## Required Work By Domain

| Domain | Current plan |
|---|---|
| Governance and acceptance | Maintain package acceptance standard, coverage matrix, sequence register, and completion reports. |
| Fixation Rights baseline | Maintain current implementation; no new feature work from this plan. |
| V2.1 facts foundation | Maintain current facts, assumptions, missing information, and internal review boundaries. |
| Pension analysis foundation | Keep current foundation; future expansion requires explicit milestone authority. |
| Source/document metadata | Preserve metadata-only boundaries until source/integration/output authority is decided. |
| Calculations beyond fixation | Excluded or decision-gated; no implementation without formula authority and golden evidence. |
| Imports/OCR/clearinghouse | Not authorized; future work requires source-of-truth and integration decisions. |
| Client-facing output | Not authorized; future work requires output contract and acceptance evidence. |
| LLM/recommendations | Not authorized; future work requires tool/prompt/safety/audit authority. |

## Validation Strategy

For any future authorized implementation package:

1. Start with git status and HEAD capture.
2. Cite source evidence and authority separately.
3. Define exact allowed files and forbidden areas.
4. Add targeted tests before or with behavior changes when changing contracts.
5. Run the smallest targeted test set first.
6. Run the package-required backend/frontend/build/governance commands.
7. Record command outputs and final git status.
8. Stop if unexpected source-code areas are required.

## Acceptance Strategy

Every future package should provide:

- Files changed.
- Exact change summary.
- Source evidence.
- Authority evidence.
- Commands run and results.
- Known exceptions.
- Final git status.
- Recommendation whether the package may be accepted.

Acceptance must distinguish:

- implementation evidence,
- runtime evidence,
- planning evidence,
- V1 reference evidence,
- product/scope authorization.

## Must Not Be Implemented Without Later Explicit Authorization

- Full pension portfolio review/projection.
- Tax planning.
- Retirement cashflow calculation.
- Scenario execution or comparison.
- Scenario commutation optimization.
- OCR/import/clearinghouse integration.
- Report/PDF/161D/client-facing output generation.
- LLM/chat/tool-driven recommendations or calculations.
- Broad source lifecycle expansion.
- Admin/settings editing that can alter calculation results.
- Any feature selected solely because it existed in V1.

## Development Plan Conclusion

The current V2 development plan is governance-first and authority-gated:

1. Maintain accepted Fixation Rights and V2.1 internal facts/review baseline.
2. Use the full capability matrix to identify future candidates.
3. Require an explicit future scope authority step before any new implementation package.
4. Derive each future package from accepted V2 authority and package acceptance standards, not from V1 parity alone.
