# V2-IAP-02B Authority Lock Register

Package: `V2-IAP-02B`

Scope: next milestone discovery and authority lock only.

## Authority Inputs

| Authority ID | Artifact | Authority status | Finding |
|---|---|---|---|
| `IAP02B-AUTH-001` | `specs/runtime/IAP_02A_next_target_selection_report.md` | Accepted prior package evidence | IAP-02A selected a missing-evidence/product-discovery authority package, not a business implementation target. |
| `IAP02B-AUTH-002` | `specs/runtime/IAP_02A_source_trace_register.md` | Accepted prior package evidence | IAP-02A found no approved Package F and no source trace authorizing expansion beyond V2.1 Package E and existing pension analysis record foundation. |
| `IAP02B-AUTH-003` | `CURRENT_PROJECT_STATE.md` | Current local state evidence | V2.1 Milestone 1 is complete; Packages A-E are closed; no approved Package F exists; no Codex instruction is open; future work requires separate Product Discovery and Product Decision before a new milestone or package is defined. |
| `IAP02B-AUTH-004` | `specs/bootstraps/BOOTSTRAP_INSTRUCTOR_V2_1.md` | V2.1 planning evidence | V2.1 Milestone 1 was internal planner-facing facts foundation only, with an approved Package A-E sequence. |
| `IAP02B-AUTH-005` | `specs/bootstraps/BOOTSTRAP_SUPERVISOR_V2_1.md` | V2.1 scope authority | The Supervisor bootstrap forbids calculations, scoring, readiness, eligibility, recommendations, approvals, client output, imports, documents, OCR, evidence repositories, external integrations, generic fact tables, full versioning, and changes to completed Fixation Rights behavior. |
| `IAP02B-AUTH-006` | `specs/bootstraps/ARCHITECT_BOOTSTRAP_V2_1.md` | V2.1 architecture/product boundary | V2.1 Milestone 1 may establish planner-maintained facts, separate assumptions/status/missing information, current/superseded lifecycle, and read-only consolidated internal review; it excludes calculations, scenarios, client-facing outputs, document/OCR/import/integration work, automated verification, and Fixation Rights changes. |
| `IAP02B-AUTH-007` | `specs/acceptance/package_acceptance_standard.md` | Acceptance standard | Future packages cannot claim coverage from documentation alone and must account for source, runtime, UI, entity, service/engine, tests, exceptions, and unmapped items. |
| `IAP02B-AUTH-008` | `specs/reference/v1_usage_rules.md` | V1 reference boundary | V1 may be inspected only as read-only reference; it must not be copied or treated as authority over approved V2 specs. |
| `IAP02B-AUTH-009` | `specs/reference/v1_discovery_full.md` | V1 reference evidence only | V1 discovery contains fixation, document/PDF, scenario, LLM, tax, and cashflow evidence, but it is not V2 authorization. |
| `IAP02B-AUTH-010` | `specs/master/v2_build_management_manual.md` | Global build governance | Build only from approved V2 specs; if required behavior is not specified, stop and raise an open question; V1 evidence is reference only. |

## Authority-Lock Classifications

| Lock ID | Direction | Classification | Authority conclusion |
|---|---|---|---|
| `IAP02B-LOCK-001` | Approved next milestone exists | `NOT_FOUND` | No artifact read in this package approves a next milestone after V2.1 Milestone 1. |
| `IAP02B-LOCK-002` | V2.1 Package F | `NOT_AUTHORIZED` | `CURRENT_PROJECT_STATE.md` explicitly states no approved Package F exists. |
| `IAP02B-LOCK-003` | V2.2 / Milestone 2 | `PRODUCT_DECISION_REQUIRED` | Broader product concepts exist in master artifacts, but no milestone decision or package authority was found. |
| `IAP02B-LOCK-004` | Pension portfolio/review/analysis expansion | `PRODUCT_DECISION_REQUIRED` | Existing facts and analysis-record foundation do not define the next product behavior. |
| `IAP02B-LOCK-005` | Clearinghouse/import/OCR/document evidence | `EXPLICITLY_EXCLUDED_UNTIL_DECIDED` | V2.1 bootstraps explicitly exclude these areas. |
| `IAP02B-LOCK-006` | Pension/tax/cashflow/scenario/client-facing output | `EXPLICITLY_EXCLUDED_UNTIL_DECIDED` | V2.1 bootstraps explicitly exclude these areas; master/V1 references do not override the exclusion. |
| `IAP02B-LOCK-007` | Fixation Rights changes | `CLOSED_SCOPE_PROTECTED` | Existing state and bootstraps protect completed V2.0/Fixation Rights behavior unless a concrete contradiction or regression is separately authorized. |
| `IAP02B-LOCK-008` | Capability coverage matrix / evidence consolidation | `GOVERNANCE_ONLY_POSSIBLE` | IAP-02A found missing consolidated coverage evidence; this could be a governance package, not implementation. |

## Authority-Lock Conclusion

```text
NO_APPROVED_NEXT_IMPLEMENTATION_MILESTONE_EXISTS
```

No approved next implementation milestone was found in the repository evidence read for V2-IAP-02B. A Product Decision package is required before any implementation IAP may be created.

## Missing Product Decision Questions

The next Product Decision package must answer these questions before implementation planning:

1. What is the exact next milestone name and version label, if any, after V2.1 Milestone 1?
2. Is the next work a continuation of V2.1, a new V2.2/Milestone 2, or a governance-only evidence consolidation package?
3. Which capability IDs are included, and are new capability IDs required?
4. Which candidate domain is selected: pension portfolio/review, pension analysis records, imports/documents/OCR/clearinghouse, pension/tax/cashflow/scenario engines, client-facing output, Fixation Rights remediation, or another explicitly named direction?
5. What is explicitly in scope at the product level?
6. What is explicitly out of scope, including calculations, recommendations, readiness, eligibility, client-facing output, imports/OCR/clearinghouse integration, document storage, and Fixation Rights changes?
7. What user role and audience is the milestone for: internal planner only, client-facing, admin, or another role?
8. What is the source-of-truth rule for every new datum, status, output, and decision?
9. Are source status, verification state, planner assumptions, advisory missing information, and analysis records still separate, and what relationships are allowed?
10. Are any calculations authorized? If yes, which engine owns them, what formulas/golden evidence are approved, and what UI/API calculation prohibitions apply?
11. Are imports, OCR, parsing, document storage, clearinghouse integration, or external integrations authorized? If yes, what security, privacy, validation, and source-authority boundaries apply?
12. Are client-facing outputs authorized? If yes, what output types, disclaimers, approval workflow, and traceability are required?
13. Are completed V2.0/Fixation Rights flows allowed to change? If yes, what exact defect or approved product change justifies reopening them?
14. What package sequence is approved for the selected milestone?
15. What acceptance evidence is required for each package under `specs/acceptance/package_acceptance_standard.md`?
16. Must a consolidated V1-to-V2 capability coverage matrix be created before implementation?
17. What files or directories are allowed and forbidden for the first execution package?
18. What stop conditions require escalation rather than implementation?

## Recommended Next Package

```text
V2-IAP-02C_PRODUCT_DECISION_FOR_NEXT_MILESTONE
```

Package nature: product decision / authority lock only.

No implementation IAP should be created before the Product Decision questions above are answered and accepted.
