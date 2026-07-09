# V2 Product Discovery Options

Package: V2-IAP-02G_STRUCTURED_PRODUCT_DISCOVERY_OPTIONS
Status: DISCOVERY_ONLY
Repository HEAD reviewed: d6b5b88b0b0c3cfb9e867905610c9c1dd338ead6

## Current State

- HEAD: `d6b5b88 docs: add V2 execution roadmap`
- 02D status: closed.
- GOV-01 status: closed.
- GOV-01 outcome: `NO_NEXT_MILESTONE_AUTHORIZED`.
- 02F status: closed.
- Next roadmap stage: 02G structured product discovery.
- Implementation authorization: NO.

## Discovery Purpose

This file prepares structured candidate options only. It does not choose one option, does not create a Product Decision, does not authorize implementation, does not reopen V1/V2 mapping, and does not modify existing planning documents.

The options below are derived from the accepted execution roadmap, package sequence register, GOV-01 checkpoint, 02D capability matrix, 02D gap plan, acceptance standard, and current project state. V1 reference evidence remains reference evidence only and is not implementation authority.

## Candidate Options Table

| Option ID | Option name | Candidate package source | Matrix rows addressed | Current V2 evidence | Gap / reason this option exists | Required owner/product/scope decision | Implementation risk | Data/source dependencies | Calculation involvement | Client-facing involvement | Imports/OCR/clearinghouse involvement | Reports/PDF/161D involvement | LLM/recommendations involvement | Expected package chain | Explicit exclusions | Acceptance requirements | Stop conditions | Classification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| OPT-A | Route-level fixation utility parity | V2-PKG-ROUTE-03 | V1-CAP-009; V1-CAP-010 | V2 fixation engine and validate/calculate flows exist; separate grant-effect, caps, eligibility-date, and exemption-summary utility route parity is not evidenced. | V1 had separate utility endpoints, while V2 may intentionally centralize behavior inside fixation workflows. | Decide whether V2 needs separate utility route contracts or should retain centralized fixation behavior only. | MEDIUM | Current route inventory; fixation contracts; engine behavior; accepted professional workflow boundaries. | YES | NO | NO | NO | NO | Product Decision -> Contract Package -> narrow route/API package if authorized -> Validation and Closure. | No generic V1 parity; no broad route additions; no calculation formula changes unless explicitly authorized; no frontend or client-facing output. | Explicit route-contract decision; exact endpoint contracts; targeted API tests; evidence that unexpected routes/fields remain rejected. | Stop if route parity is not explicitly authorized, if centralized behavior is accepted, or if route work requires source code areas outside the later allowed package. | NEEDS_PRODUCT_DECISION |
| OPT-B | Source / verification / document metadata foundation | V2-PKG-SOURCE-04 | V1-CAP-027; V1-CAP-031; V1-CAP-032; V1-CAP-040 | V2 has bounded source/verification fields and clearinghouse/document metadata route inventory; import, OCR, lifecycle expansion, and external integration are not authorized. | Existing metadata foundations may need product rules before any source lifecycle, document, or integration work. | Decide source-of-truth rules, provenance states, metadata-only boundary, and whether any external-source policy is in scope. | MEDIUM | Existing facts APIs; clearinghouse snapshot metadata; document metadata; source/verification fields; external source policy if later authorized. | NO | NO | YES | NO | NO | Product Decision -> Contract Package for metadata/source lifecycle -> narrow metadata/source package if authorized -> Validation and Closure. | No OCR, import, clearinghouse integration, document generation, reports, calculations, or broad lifecycle fields unless explicitly authorized. | Field contract; provenance rules; allowed states; rejection tests for unauthorized fields; audit/failure-mode expectations. | Stop if owner cannot distinguish metadata-only from integration, or if imports/OCR/clearinghouse behavior is requested without explicit authorization. | NEEDS_PRODUCT_DECISION |
| OPT-C | Pension analysis expansion | V2-PKG-PENSION-05 | V1-CAP-030; possibly V1-CAP-033 | V2 has pension holding facts and pension holding analysis record foundation; broader analysis outcomes and recommendations are not authorized. | Current analysis record may be expanded into a bounded internal analysis workflow if product scope authorizes it. | Decide audience, internal-only boundary, whether calculations are allowed, and whether this remains analysis maintenance rather than portfolio review. | MEDIUM | Pension holdings; pension analysis record; planner assumptions if used; advisory missing information; internal review evidence. | NO by default; YES only if later Product Decision authorizes formulas. | NO by default; YES only if later Product Decision authorizes client output. | NO | NO | NO | Product Decision -> Contract Package for selected analysis scope -> narrow internal analysis package -> Validation and Closure. | No full portfolio projection, recommendations, client-facing output, tax, cashflow, scenario modeling, imports, OCR, clearinghouse integration, reports, PDF, 161D, or LLM behavior. | Exact analysis contract; audience decision; allowed fields; UI/API behavior if authorized; targeted tests; explicit exclusions. | Stop if the requested scope implies full portfolio review, calculations, recommendations, or client output without explicit authorization. | NEEDS_PRODUCT_DECISION |
| OPT-D | Full pension portfolio review/projection | V2-PKG-PORTFOLIO-06 | V1-CAP-033 | V2 has facts foundation and internal consolidated review; current project state says V2.0 MRP does not require full pension holdings review. | Full portfolio review/projection is a possible future product direction, but it is not currently authorized. | Decide milestone name, audience, projection scope, calculation authority, source rules, assumptions, and output boundary. | HIGH | Pension holdings; planner assumptions; source/verification rules; possible external indexation/source data if authorized. | YES | Possibly YES if client-facing review is selected; otherwise NO. | Possibly YES only if selected source strategy requires it. | Possibly YES only if selected output includes reports. | NO unless explicitly authorized. | Product Decision -> Contract Package for portfolio review -> calculation/source contract if needed -> narrow implementation slice -> Validation and Closure. | No tax planning, cashflow, scenarios, recommendations, imports/OCR/clearinghouse, reports/PDF/client output, or LLM unless separately authorized. | Product decision; formula/source authority if projections exist; contract tests; golden cases if calculations exist; explicit audience and output boundary. | Stop if calculations, source rules, or client-facing boundaries are unresolved. | NEEDS_PRODUCT_DECISION |
| OPT-E | Tax/cashflow/scenario calculation domains | V2-PKG-CALC-07 | V1-CAP-034; V1-CAP-035; V1-CAP-036; V1-CAP-037; V1-CAP-040 | Current evidence excludes tax planning, cashflow, scenario modeling, and scenario comparison from V2.0 MRP; no implementation authority exists. | These are high-risk V1-adjacent calculation domains that may be reopened only by explicit future authority. | Decide whether any calculation domain is in scope, formula authority, legal/tax assumptions, source data, audit, and user-facing reliance boundaries. | HIGH | Facts; assumptions; fixation results; tax rules; inflation/indexation; external data; scenario inputs if authorized. | YES | Possibly YES depending on output decision. | Possibly YES if external data is used. | Possibly YES if results are output as reports. | NO unless explicitly authorized. | Product Decision -> Calculation Contract Package -> formula/golden evidence package -> narrow calculation implementation -> Validation and Closure. | No hidden formulas; no V1 fallback copying; no client-facing claims; no reports/PDF/161D; no imports/OCR/clearinghouse; no LLM/recommendations unless separately authorized. | Formula spec; source authority; deterministic golden tests; API/UI tests if exposed; exception register; audit/reproducibility evidence. | Stop if formula authority, legal/tax assumptions, data source, or output reliance boundary is unresolved. | EXCLUDED_UNTIL_AUTHORIZED |
| OPT-F | Imports/OCR/clearinghouse integration | V2-PKG-INTEGRATION-08 | V1-CAP-031; V1-CAP-032; V1-CAP-040 | V2 has clearinghouse/document metadata evidence only; imports, OCR, and clearinghouse integration are not authorized. | Metadata foundations may later need ingestion, but integration has privacy, source quality, and operational risk. | Decide whether ingestion is authorized, what source is trusted, whether OCR is allowed, and how failures/audit are handled. | HIGH | External providers; uploaded documents; OCR pipeline; clearinghouse records; source provenance; privacy/security controls. | NO by default; YES only if imported data feeds calculations later. | Possibly YES if imported data appears in client output. | YES | Possibly YES if documents/reports are generated. | NO | Product Decision -> Integration Contract Package -> read-only evidence package -> narrow integration implementation -> Validation and Closure. | No external side effects without explicit integration package; no OCR/import behavior from metadata-only evidence; no calculations; no reports; no recommendations. | Source-of-truth decision; integration contract; failure-mode tests; audit/provenance evidence; privacy/security acceptance boundary. | Stop if source trust, data ownership, OCR accuracy, external dependency behavior, or side-effect controls are unresolved. | EXCLUDED_UNTIL_AUTHORIZED |
| OPT-G | Reports/PDF/161D/client-facing output | V2-PKG-OUTPUT-09 | V1-CAP-039 | V2 has internal review and saved-run explainability; current project state excludes 161D output generation inside V2 and does not authorize client-facing reports. | Client-facing output is a distinct product decision and cannot be inferred from internal review. | Decide output audience, legal/form contract, exact content, approval workflow, and source traceability. | HIGH | Accepted internal data; saved calculations; review context; source evidence; rendering pipeline if authorized. | Possibly YES if output includes calculated values. | YES | NO unless output depends on imported documents. | YES | Possibly YES only if explicitly authorized. | Product Decision -> Output Contract Package -> rendering/source-trace package -> narrow output implementation -> Validation and Closure. | No advice, recommendations, tax/cashflow/scenario output, PDF/report generation, 161D, or client-facing claims without explicit Product Decision. | Output contract; rendering verification; source traceability; approval/audit evidence; regression tests; explicit limitations. | Stop if audience, content contract, legal/form requirements, source traceability, or approval workflow is unresolved. | EXCLUDED_UNTIL_AUTHORIZED |
| OPT-H | LLM/tool/recommendation workflow | V2-PKG-LLM-10 | V1-CAP-038 | Current V2 planning does not authorize LLM tools, recommendations, or client-facing advice expansion. | V1 had LLM/tool-like behavior, but V2 requires separate safety and authority before any such workflow. | Decide whether LLM/tool behavior is allowed, what it may access, whether recommendations are allowed, and how audit/safety are enforced. | HIGH | Prompt/tool contracts; permitted data; audit logs; safety policy; output boundaries. | Possibly YES if tools perform calculations, but not authorized now. | Possibly YES if advice/output is client-facing, but not authorized now. | Possibly YES only if tools access imports. | Possibly YES only if tool output becomes report content. | YES | Product Decision -> LLM/Tool Contract Package -> safety/audit package -> narrow implementation if authorized -> Validation and Closure. | No unreviewed recommendations; no hidden calculations; no broad tool access; no client-facing advice; no reports/PDF/161D without explicit authorization. | Tool contract; prompt evidence; audit logs; safety tests; allowed/forbidden outputs; fallback/exception behavior. | Stop if tool scope, recommendation boundary, safety controls, auditability, or user audience is unresolved. | EXCLUDED_UNTIL_AUTHORIZED |
| OPT-I | Administration/settings evidence investigation | V2-PKG-ADMIN-11 | V1-CAP-041 | Matrix marks administration/settings/table editing as UNKNOWN; current V2 evidence does not show a general admin/settings milestone. | Evidence may be insufficient to determine whether mutable settings/admin controls belong in V2. | Decide whether more evidence is needed, what settings are involved, who can change them, and how reproducibility is preserved. | LOW for evidence investigation; HIGH for implementation. | Source evidence; calculation caps/year data; audit requirements; permission model if later authorized. | Possibly YES if settings affect calculations. | NO | NO | NO | NO | Product Decision or evidence investigation -> Admin/Settings Contract Package only if evidence supports it -> implementation only with explicit authority. | No mutable calculation data, permission model, admin UI, settings edits, or runtime behavior without explicit evidence and authority. | Named missing evidence; evidence register; reproducibility requirements; permission/audit criteria if later advanced. | Stop if evidence remains unknown or mutable state threatens calculation reproducibility. | UNKNOWN_NEEDS_EVIDENCE |

## Option Grouping

### Low-risk internal/governance candidates

- OPT-I Administration/settings evidence investigation: low risk only if limited to evidence discovery; implementation risk remains high if mutable settings affect calculations.

### Medium-risk internal product candidates

- OPT-A Route-level fixation utility parity.
- OPT-B Source / verification / document metadata foundation.
- OPT-C Pension analysis expansion.

These candidates may remain internal and bounded, but each needs a later Product Decision before any contract or implementation package can open.

### High-risk calculation/integration/output candidates

- OPT-D Full pension portfolio review/projection.
- OPT-E Tax/cashflow/scenario calculation domains.
- OPT-F Imports/OCR/clearinghouse integration.
- OPT-G Reports/PDF/161D/client-facing output.
- OPT-H LLM/tool/recommendation workflow.

These candidates involve calculation, integration, output, legal/client reliance, or safety risk. They remain excluded or unauthorized until explicit owner/product/scope authority exists.

### Evidence-blocked candidates

- OPT-I Administration/settings evidence investigation.

This candidate cannot become an implementation package unless missing evidence is named, found, and accepted.

## Product Decision Preparation

A later Product Decision package must answer:

1. Which option, if any, is selected?
2. Who is the user/audience?
3. What is explicitly in scope?
4. What is explicitly out of scope?
5. Are calculations authorized?
6. Are imports/OCR/clearinghouse authorized?
7. Are reports/PDF/161D/client-facing outputs authorized?
8. Are LLM/recommendations authorized?
9. What is the first contract package?
10. What are the allowed areas?
11. What are the forbidden areas?
12. What evidence is required?
13. What stop conditions apply?

The Product Decision package may choose only from these discovery options or choose NO-GO. It must not implement.

## Explicit Next Step

The next roadmap step after 02G is:

`V2-IAP-02H_PRODUCT_DECISION_FOR_NEXT_MILESTONE`

02H may only choose from the discovery options or choose NO-GO.

02H must not implement.

## Anti-loop Controls

1. 02G does not authorize implementation.
2. 02G does not choose a product direction.
3. 02G does not reopen V1/V2 mapping.
4. 02G only prepares options.
5. If Product Decision cannot choose, the next state is NO-GO or named missing evidence, not another broad mapping cycle.
6. No candidate option may be treated as implementation-authorized by this discovery file.
7. No implementation may start before an accepted Product Decision and accepted Contract Package.
8. Documentation alone remains planning evidence and is not positive implementation evidence.

## Implementation Authorization Status

Implementation authorized by 02G: NO.

Product direction chosen by 02G: NO.

Product Decision created by 02G: NO.

V1/V2 mapping reopened by 02G: NO.
