# Retire V2 Master Build Sequence: Full System

Package: `V2-MASTER-01_FULL_SYSTEM_BUILD_SEQUENCE`

Repository baseline reviewed: `42d2f15bba864231d6506c7c1afb7df3fb61f466`

Document status: `READY_FOR_REVIEW_ONLY`

Implementation authorization: `NO`

## 1. Current Truth Statement

There is no accepted full-system, execution-ready build plan before this file. Existing 02K and 02L are milestone-level artifacts for the Internal Pension Analysis Workspace only; they are not the full Retire V2 build plan. 02M is ready at contract level but frozen until this Master Sequence is reviewed. This file is intended to become the master ordering document for the complete system after review and acceptance; it is not an implementation package and does not authorize code, tests, schema, integration, calculation, output, or deployment work.

Current implementation evidence is uneven and must remain explicit: client context, V2.1 retirement facts, pension analysis records, planner assumptions, advisory missing information, consolidated internal review, Fixation Rights calculation, immutable fixation runs, and fixation audit/explainability exist in bounded forms. Clearinghouse snapshot metadata is partial. Clearinghouse file intake/parsing, normalized balance ledger, conversion engines, broader tax engines, external index services, scenarios, recommendation workflows, client output, and production-wide validation are not implemented merely because they appear in planning documents.

## 2. Full System Target

The complete intended Retire V2 system is an internal-planner-led, deterministic, auditable retirement-planning platform that starts with a client-scoped internal workspace; accepts clearinghouse and approved manual source data while preserving raw evidence; parses and normalizes holdings into a source-traceable balance ledger; supports classification and audited manual correction; converts pension and capital positions through explicit engines; applies versioned annual tax parameters and approved external CBS/index data where required; executes tax, pension, cashflow, and scenario calculations; compares immutable scenario results; records planner judgment and approved recommendations; produces source-backed client output, reports, PDFs, and 161D/Fixation artifacts; preserves complete audit/history/explainability; and passes end-to-end security, data, calculation, operational, and production validation.

## 3. Mandatory Milestone Chain

1. **M01 Internal Pension Analysis Workspace** - assemble the existing internal pension facts and analysis foundation into a usable planner workspace.
2. **M02 Clearinghouse Intake and Raw Source Preservation** - accept files safely and preserve immutable source bytes and intake metadata before parsing.
3. **M03 Clearinghouse Parser and Normalized Import Model** - parse supported source formats into versioned staging records without mutating planner facts.
4. **M04 Pension Balance Ledger** - establish the canonical source-traceable ledger of imported and manual pension balances.
5. **M05 Balance Classification and Manual Correction Layer** - classify products and provide audited corrections without rewriting source evidence.
6. **M06 Pension/Capital Asset Conversion Foundation** - convert classified ledger positions into deterministic pension/capital inputs and model explicit lump-sum elections.
7. **M07 Tax Input Model and Annual Parameter Tables** - define versioned tax inputs and annual parameters before broader tax calculation.
8. **M08 External Data/API Layer, including CBS/LMAS and index data if required** - acquire and snapshot approved external values with deterministic failure policy.
9. **M09 Tax Calculation Engines** - calculate approved exemption, severance, pension, capitalization, spreading, marginal-tax, and relevant insurance effects.
10. **M10 Scenario Engine** - execute immutable scenarios over locked source, conversion, tax, pension, and cashflow inputs.
11. **M11 Scenario Comparison and Planner Review** - compare persisted results without recalculation or mutation.
12. **M12 Planner Judgment / Recommendation Layer** - attach auditable professional judgment and approved recommendation records to reviewed scenarios.
13. **M13 Client Output Model** - freeze the approved, source-backed data contract for client presentation.
14. **M14 Reports, PDF, Export, and 161D/Fixation Outputs** - render approved outputs from immutable result snapshots only.
15. **M15 Audit Trail, Run History, and Explainability** - unify cross-domain source-to-output trace and immutable run history.
16. **M16 End-to-End Validation and Production Hardening** - prove the full workflow and production controls under realistic failure and recovery conditions.

The order is mandatory. M07 precedes M08 because external values must enter an already versioned parameter/input contract. M15 follows functional output milestones because it must unify their accepted event and trace contracts, while each earlier milestone must still implement local audit evidence needed for its own acceptance.

## 4. For Each Milestone

### M01 Internal Pension Analysis Workspace

- **Purpose:** Deliver one internal client-scoped workspace for pension holdings, per-holding analysis records, planner assumptions, advisory missing information, and consolidated review.
- **Why needed:** It gives planners a usable source-review surface before ingestion, ledger, and calculation expansion.
- **Dependencies:** Existing client, pension holding, analysis-record, planner-assumption, missing-item, and consolidated-review contracts; accepted 02K/02L; reviewed Master Sequence.
- **Main data objects/tables expected:** Existing `client`, `pension_holding`, `pension_analysis_record`, `planner_assumption`, and `missing_data_item`; no new table in the first slice.
- **Expected backend work:** None for 02M unless a later concrete gap is proven; reuse existing client-scoped APIs.
- **Expected frontend work:** Compose the contracted workspace once in `ClientDetailScreen`, retaining distinct source, assumption, analysis, and missing-information sections.
- **Expected tests:** Targeted workspace and client-detail tests; existing section regressions; full frontend tests and build.
- **Explicit exclusions:** Calculations, projections, recommendations, imports, clearinghouse integration, client output, reports, and admin/settings.
- **Output:** Accepted internal workspace and M01 completion evidence.
- **Next milestone unlocked:** M02.
- **Known unknowns:** Whether later M01 slices need a dedicated internal summary beyond existing consolidated review.
- **Stop conditions:** Any backend/schema requirement for 02M, duplicate component/API composition, forbidden behavior, or required test/build failure.

### M02 Clearinghouse Intake and Raw Source Preservation

- **Purpose:** Accept authorized clearinghouse files and preserve exact raw source bytes plus immutable intake metadata.
- **Why needed:** Parsing and balances cannot be reproducible without the original source, checksum, provider, received time, client ownership, and processing state.
- **Dependencies:** M01 complete; approved file types, size limits, retention, privacy, malware scanning, and storage policy.
- **Main data objects/tables expected:** `source_file`, `source_file_blob` or object-store reference, `source_intake_event`, checksum, MIME type, original filename, provider, client ID, received timestamp, uploader, and immutable status history; existing `clearinghouse_snapshot` metadata must be reconciled rather than silently repurposed.
- **Expected backend work:** Multipart intake endpoint, client ownership checks, content validation, checksum/deduplication policy, immutable storage adapter, status API, and failure-safe transaction boundaries.
- **Expected frontend work:** Internal upload/intake screen with progress, accepted-format guidance, receipt, failure state, and raw-file metadata view.
- **Expected tests:** File-type/size/content mismatch, checksum, duplicate policy, client isolation, malware/storage failure, rollback, immutable readback, authorization, and API/UI states.
- **Explicit exclusions:** Parsing into balances, OCR, calculations, ledger mutation, and external clearinghouse network calls unless separately contracted inside M02.
- **Output:** One immutable raw-source record per accepted upload with verifiable bytes and intake history.
- **Next milestone unlocked:** M03.
- **Known unknowns:** Supported clearinghouse formats, maximum size, storage backend, encryption/retention rules, and whether direct provider fetch is ever allowed.
- **Stop conditions:** No named file contract, no approved storage/privacy/security policy, inability to verify byte-for-byte preservation, or external side effects outside exact package scope.

### M03 Clearinghouse Parser and Normalized Import Model

- **Purpose:** Parse supported XML and any approved Excel/CSV/manual import format into versioned staging records.
- **Why needed:** The ledger requires normalized, validated values while raw evidence remains immutable and separate.
- **Dependencies:** M02 raw-source identity and storage; format/version specifications; encoding, locale, decimal, date, and error contracts.
- **Main data objects/tables expected:** `import_run`, `import_record`, `import_field_value`, `import_validation_error`, parser version, source-file ID, record ordinal, raw locator/XPath/row/column, normalized candidate payload, and status.
- **Expected backend work:** Parser interfaces by format/version, schema validation, deterministic normalization, quarantine/error reporting, idempotent reparse, and no direct write to facts or ledger.
- **Expected frontend work:** Import-run detail showing parsed rows, warnings/errors, source locators, retry/reparse eligibility, and blocked records.
- **Expected tests:** Golden XML fixtures, malformed/truncated/unknown-version files, encoding and locale cases, Excel/CSV formulas/headers if applicable, idempotency, parser-version snapshots, and source-locator trace.
- **Explicit exclusions:** Balance acceptance, product classification decisions, calculations, manual source overwrite, and OCR unless explicitly added by a separate approved parser contract.
- **Output:** Validated normalized staging records linked field-by-field to immutable raw sources.
- **Next milestone unlocked:** M04.
- **Known unknowns:** Exact clearinghouse schemas/versions and whether Excel/CSV/manual import belongs in this milestone.
- **Stop conditions:** Missing authoritative format specification, nondeterministic parse, untraceable normalized field, or parser writing directly to authoritative balances.

### M04 Pension Balance Ledger

- **Purpose:** Create the canonical, client-scoped ledger for pension balances and pension-income observations from imported and approved manual sources.
- **Why needed:** Conversion, tax, and scenarios need a stable balance authority rather than mutable UI records or parser output.
- **Dependencies:** M03 normalized staging model; source precedence, duplicate, effective-date, currency, and supersession rules.
- **Main data objects/tables expected:** `pension_balance_ledger_entry`, `balance_observation`, source-file/import-record links, holding link, amount, currency, balance date, pension amount/date, entry type, source priority, accepted/superseded status, and ledger version/snapshot.
- **Expected backend work:** Promotion service from staging to ledger, manual-entry command, exact duplicate/conflict validation, immutable entry plus supersession model, current-balance query, and source trace API.
- **Expected frontend work:** Ledger view by client/holding/date/source with conflicts, source links, current/previous observations, and no calculations.
- **Expected tests:** Decimal/date invariants, client isolation, duplicate/conflict behavior, promotion atomicity, supersession without deletion, source trace, current-value selection, and exact table boundaries.
- **Explicit exclusions:** Product classification decisions, correction overwrite, conversion, projection, tax, scenario, and recommendation behavior.
- **Output:** Authoritative versioned pension balance ledger with reproducible source lineage.
- **Next milestone unlocked:** M05.
- **Known unknowns:** Multiple observations on one date, currency conversion policy, provider identifier mapping, and current-value precedence.
- **Stop conditions:** Source precedence unresolved, ledger entries mutable in place, amounts cannot be traced to source/staging, or parser output is treated as authority without acceptance.

### M05 Balance Classification and Manual Correction Layer

- **Purpose:** Classify ledger positions and record planner corrections as separate audited overlays.
- **Why needed:** Engines require explicit product and tax treatment categories, while source evidence must remain unchanged.
- **Dependencies:** M04 ledger; controlled classification taxonomy; correction reason, approval, supersession, and permission rules.
- **Main data objects/tables expected:** `balance_classification`, `classification_taxonomy_version`, `balance_correction`, `correction_reason`, reviewer, effective time, supersedes ID, and before/after values.
- **Expected backend work:** Classification commands/queries, deterministic rule suggestions if approved, manual correction API, optimistic concurrency, immutable correction history, and resolved-view service.
- **Expected frontend work:** Classification queue and correction form showing original, suggested, corrected, source, reason, reviewer, and history.
- **Expected tests:** Categories for pension/capital/severance/compensation/savings and old/new pension fund, managers insurance, gemel, and hishtalmut; invalid combinations; permissions; concurrency; immutable history; unresolved ambiguity.
- **Explicit exclusions:** Hidden automatic acceptance, deletion or rewrite of raw/ledger data, conversion calculations, recommendation, and client output.
- **Output:** A resolved, versioned classification/correction view suitable for conversion inputs.
- **Next milestone unlocked:** M06.
- **Known unknowns:** Final bilingual taxonomy, rule confidence thresholds, reviewer roles, and multi-category products.
- **Stop conditions:** Taxonomy not locked, correction lacks reason/actor/history, or classification mutates source/ledger records.

### M06 Pension/Capital Asset Conversion Foundation

- **Purpose:** Convert classified balances into explicit pension-income and capital-asset positions and model approved lump-sum/commutation elections without mutating source facts.
- **Why needed:** Tax and scenario engines need normalized economic positions and explicit conversion choices.
- **Dependencies:** M05 resolved classifications; actuarial/conversion formula authority, dates, factors, rounding, eligibility, and source snapshot rules.
- **Main data objects/tables expected:** `conversion_input_snapshot`, `conversion_run`, `conversion_result`, `pension_income_position`, `capital_position`, `lump_sum_election`, conversion factor/version, and audit rows.
- **Expected backend work:** Pure pension and capital conversion engines, validation contracts, run persistence, source snapshot references, preview versus execute separation, and no source mutation.
- **Expected frontend work:** Internal conversion input review, validation errors, preview/result, factor/version display, and source trace.
- **Expected tests:** Golden conversion cases, boundaries, rounding, amount-over-balance rejection, repeatability, source immutability, pension/capital conservation, and run persistence.
- **Explicit exclusions:** Tax calculation, scenario comparison, advice, client output, and actual transaction execution.
- **Output:** Immutable conversion results consumable by tax/scenario inputs.
- **Next milestone unlocked:** M07.
- **Known unknowns:** Actuarial factors, product-specific conversion rules, treatment of mixed products, and whether actual execution is ever in V2.
- **Stop conditions:** Formula/factor authority missing, conversion mutates ledger/source, conservation invariant fails, or hidden fallback is required.

### M07 Tax Input Model and Annual Parameter Tables

- **Purpose:** Define deterministic tax input contracts and versioned annual parameter datasets before broader tax engines.
- **Why needed:** Tax results cannot be reproduced if caps, brackets, exemption percentages, credits, or dates are hidden constants or mutable settings.
- **Dependencies:** M06 conversion outputs; accepted legal/tax source authority and effective-year/version policy; existing Fixation Rights contracts reconciled.
- **Main data objects/tables expected:** `tax_input_snapshot`, `tax_parameter_set`, `tax_bracket`, `exemption_parameter`, `credit_parameter`, `national_insurance_parameter` if relevant, publication source, effective dates, version, checksum, and approval metadata.
- **Expected backend work:** Read-only parameter repository, explicit version selection, tax input schema/validation, publication/import command separated from runtime calculation, and snapshot linkage.
- **Expected frontend work:** Internal parameter/version visibility and tax-input review; no general admin/settings editor.
- **Expected tests:** Exact annual tables, overlap/gap rejection, year selection, immutable versions, decimal/rounding, source metadata, snapshot reproducibility, and unauthorized mutation rejection.
- **Explicit exclusions:** Tax calculation, generic mutable settings UI, silent latest-year fallback, and unapproved external fetch.
- **Output:** Locked tax input and annual parameter contracts for engine consumption.
- **Next milestone unlocked:** M08.
- **Known unknowns:** Authoritative publishers, update cadence, correction/version policy, National Insurance scope, and historical coverage years.
- **Stop conditions:** Parameter authority absent, tables mutable in place, effective periods ambiguous, or calculation would depend on an unsnapshotted latest value.

### M08 External Data/API Layer, including CBS/LMAS and index data if required

- **Purpose:** Acquire approved CBS/LMAS CPI/index or other external values and convert them into versioned internal observations.
- **Why needed:** Indexation or projection must be deterministic, source-backed, and resilient to external unavailability.
- **Dependencies:** M07 parameter/input contract; explicit decision that external data is required; endpoint, license, authentication, cache, retry, and fallback policies.
- **Main data objects/tables expected:** `external_dataset`, `external_observation`, `external_fetch_run`, provider, series ID, period, value, source timestamp, retrieved timestamp, raw response checksum, status, and supersession/version.
- **Expected backend work:** Provider adapter, timeout/retry/circuit breaker, schema validation, raw response preservation, idempotent ingestion, approved manual backfill path, and snapshot query.
- **Expected frontend work:** Internal data freshness/status screen, observation/source detail, failed-fetch visibility, and no silent correction.
- **Expected tests:** Provider contract fixtures, timeout/429/5xx/malformed/stale data, idempotency, no-network deterministic engine tests, version selection, fallback rejection, and source trace.
- **Explicit exclusions:** Live API calls inside deterministic engines, nominal fallback, hidden latest-value selection, unrelated external integrations, and admin editing.
- **Output:** Versioned external observations usable as explicit calculation inputs.
- **Next milestone unlocked:** M09.
- **Known unknowns:** Whether CBS/LMAS is needed, exact series/endpoints, licensing, revision behavior, and outage policy.
- **Stop conditions:** No authoritative provider contract, terms prohibit storage, raw response cannot be preserved, or engine would call the provider directly.

### M09 Tax Calculation Engines

- **Purpose:** Implement deterministic tax engines for the approved retirement-planning scope while integrating existing Fixation Rights outputs safely.
- **Why needed:** Scenarios require authoritative tax effects rather than frontend formulas or planner estimates.
- **Dependencies:** M06 conversion results, M07 tax inputs/parameters, M08 external observations where required, and accepted formula/golden-case contracts.
- **Main data objects/tables expected:** `tax_run`, `tax_result`, `tax_audit_row`, `tax_validation_error`, input/result snapshots, linked fixation run, and component results for severance/grant exemption, pension exemption, capitalization, spreading, marginal tax, and National Insurance if relevant.
- **Expected backend work:** Pure engines by tax component, orchestration service, validation, immutable persistence, existing Fixation Rights reuse by explicit run reference, and no mutation of saved fixation.
- **Expected frontend work:** Tax input review, blocking validation, result breakdown, annual rows, source/parameter versions, and audit display.
- **Expected tests:** Formula-level golden cases, boundary years/brackets/caps, prisa periods, rounding, invalid inputs, cross-engine consistency, existing fixation regression, immutable runs, and no external calls.
- **Explicit exclusions:** Scenario choice, recommendation, client report rendering, hidden legal assumptions, and mutation of source/conversion/fixation records.
- **Output:** Versioned authoritative tax results with complete input and parameter trace.
- **Next milestone unlocked:** M10.
- **Known unknowns:** Final tax-domain list, prisa rules, marginal-tax interactions, National Insurance relevance, legal review, and handling of law changes.
- **Stop conditions:** Any formula or authority unresolved, golden cases unavailable, conflicting tax components, or result not reproducible from snapshots.

### M10 Scenario Engine

- **Purpose:** Define and execute immutable retirement scenarios over locked source, conversion, pension, tax, and cashflow inputs.
- **Why needed:** Planners need alternatives without mutating actual facts or accepted calculation runs.
- **Dependencies:** M09 tax engines; approved pension/cashflow projection formulas; source snapshot contract; scenario lifecycle and stale-data policy.
- **Main data objects/tables expected:** `scenario`, `scenario_version`, `scenario_input_snapshot`, `scenario_run`, `pension_projection_result`, `tax_result_ref`, `cashflow_result`, annual result rows, one-time flows, net annual result, net cumulative result, and run audit.
- **Expected backend work:** Scenario CRUD/versioning, pure orchestration, pension/cashflow engines, immutable run persistence, stale-source detection, and rerun-as-new-run behavior.
- **Expected frontend work:** Scenario definition/editor, source snapshot review, validation, run action, annual/cumulative result view, and stale warning.
- **Expected tests:** Golden end-to-end scenarios, duplicate/version behavior, actual-versus-assumption separation, commutation bounds, annual/cumulative arithmetic, repeatability, stale source, rollback, and no source mutation.
- **Explicit exclusions:** Cross-scenario recommendation, client-facing report, editing results, and automatic final-scenario selection.
- **Output:** One or more immutable scenario runs with authoritative engine outputs.
- **Next milestone unlocked:** M11.
- **Known unknowns:** Time horizon/granularity, inflation assumptions, longevity handling, cashflow scope, scenario editing semantics, and rerun policy.
- **Stop conditions:** Projection/cashflow formula authority absent, source snapshot incomplete, actual facts would be mutated, or net results cannot reconcile to component outputs.

### M11 Scenario Comparison and Planner Review

- **Purpose:** Compare persisted scenario results and support internal review without recalculation.
- **Why needed:** Decision quality requires transparent differences and stable comparison baselines.
- **Dependencies:** M10 immutable scenario runs with compatible contract/version metadata.
- **Main data objects/tables expected:** `scenario_comparison`, selected run references, comparison snapshot, comparison metrics, planner review status, and optional selected-final-scenario marker.
- **Expected backend work:** Compatibility validation, comparison service over saved outputs, delta calculations, comparison persistence, and selection/archive commands with audit.
- **Expected frontend work:** Side-by-side scenario table, annual/cumulative deltas, pension/tax/cashflow breakdowns, assumptions/source/version differences, stale/invalid warnings, and internal selection controls.
- **Expected tests:** Compatible/incompatible runs, deterministic deltas, ordering, missing metrics, stale runs, selection concurrency, no result mutation, and UI accessibility.
- **Explicit exclusions:** Re-running engines during comparison, automatic ranking, recommendation language, and client output.
- **Output:** Immutable, explainable comparison and internal planner review state.
- **Next milestone unlocked:** M12.
- **Known unknowns:** Required comparison metrics, materiality thresholds, selection/archive lifecycle, and whether more than two scenarios are compared.
- **Stop conditions:** Comparison requires recalculation, incompatible contracts are silently mixed, or planner selection rewrites scenario results.

### M12 Planner Judgment / Recommendation Layer

- **Purpose:** Record professional judgment and, only under an accepted contract, structured recommendations linked to reviewed scenario evidence.
- **Why needed:** Engine output alone is not professional advice; planner rationale and approval must be distinct and auditable.
- **Dependencies:** M11 comparison; recommendation taxonomy, permissions, review/approval, disclaimer, supersession, and client-visibility rules.
- **Main data objects/tables expected:** Existing `internal_planner_judgment` as a bounded anchor; future `scenario_judgment`, `recommendation`, `recommendation_rationale`, evidence references, status history, author/reviewer, and supersession links.
- **Expected backend work:** Create/read/supersede contracts, evidence-link validation, permission checks, immutable history, approval workflow if authorized, and no engine mutation.
- **Expected frontend work:** Internal judgment and recommendation editor, evidence links, rationale, status/reviewer display, history, and clear separation from calculated facts.
- **Expected tests:** Required rationale/evidence, permissions, allowed statuses, supersession, concurrent review, no unsupported advice, no automatic recommendation, and immutable history.
- **Explicit exclusions:** LLM-generated advice unless separately contracted, hidden ranking, direct client publication, calculation changes, and deletion of history.
- **Output:** Auditable planner decision record connected to specific comparison/run evidence.
- **Next milestone unlocked:** M13.
- **Known unknowns:** Recommendation taxonomy, legal/compliance approval, dual review, LLM prohibition or scope, and client disclosure rules.
- **Stop conditions:** Recommendation authority or approval model missing, evidence links optional, automated advice introduced, or judgment can alter calculation results.

### M13 Client Output Model

- **Purpose:** Define the immutable data contract that may be presented to a client.
- **Why needed:** Internal screens and engine payloads cannot safely serve as client output without content, approval, limitation, and source rules.
- **Dependencies:** M12 approved planner judgment/recommendation; selected scenario; output audience/content/legal approval; localization and accessibility rules.
- **Main data objects/tables expected:** `client_output_snapshot`, `output_section`, selected scenario/comparison/judgment references, disclosure/limitation set, approval record, locale, template contract version, and source manifest.
- **Expected backend work:** Output assembler from immutable accepted records, validation for completeness/approval, snapshot persistence, redaction rules, and no recalculation.
- **Expected frontend work:** Internal preview and approval screen, section inclusion controls only where contracted, source manifest, limitations, and client-safe rendering preview.
- **Expected tests:** Exact field allowlist, prohibited internal fields, source completeness, approval requirement, localization/RTL, accessibility, redaction, snapshot immutability, and no recalculation.
- **Explicit exclusions:** PDF rendering, 161D form generation, live calculations, unapproved recommendations, and direct delivery to clients.
- **Output:** Approved client-output snapshot ready for renderers.
- **Next milestone unlocked:** M14.
- **Known unknowns:** Mandatory sections, wording/legal disclaimers, languages, branding, approval roles, and delivery channels.
- **Stop conditions:** Audience/content contract incomplete, internal-only data leaks, output numbers are recomputed, or source manifest/approval is missing.

### M14 Reports, PDF, Export, and 161D/Fixation Outputs

- **Purpose:** Render approved snapshots into reports, PDFs, exports, and authorized 161D/Fixation artifacts.
- **Why needed:** Final deliverables require stable formatting and legal/form correctness without calculation leakage.
- **Dependencies:** M13 client-output snapshots; official form/template authority; rendering/storage/versioning/signature/delivery contracts; existing Fixation result anchors.
- **Main data objects/tables expected:** `render_job`, `rendered_artifact`, template/form version, source-output snapshot ID, checksum, MIME type, generation status, approval/delivery metadata, and artifact audit events.
- **Expected backend work:** Deterministic render service, template registry, artifact storage, PDF/export generation, official-field mapping for 161D/Fixation outputs, checksum, and retry without content mutation.
- **Expected frontend work:** Preview, generate, status, download/view, version/source display, approval, and failure handling.
- **Expected tests:** Golden rendered content, pixel/layout/RTL checks, PDF text/field readback, official form mapping, checksum/repeatability, prohibited-field absence, renderer failure/retry, and browser download flow.
- **Explicit exclusions:** Renderer calculations, editing source results in reports, unapproved electronic filing, and automatic client delivery.
- **Output:** Versioned artifacts traceable to one approved output snapshot.
- **Next milestone unlocked:** M15.
- **Known unknowns:** Exact report set, 161D/form versions, fillable versus flattened output, electronic filing, signatures, storage retention, and delivery.
- **Stop conditions:** Template/form authority missing, renderer changes numbers, artifact cannot be traced/reproduced, or legal/layout verification fails.

### M15 Audit Trail, Run History, and Explainability

- **Purpose:** Provide one cross-domain trace from source files and corrections through parameters, engines, scenarios, judgments, outputs, and artifacts.
- **Why needed:** Professional, tax, and client-reliance workflows require complete reproducibility and investigation capability.
- **Dependencies:** Accepted local audit/event contracts from M02-M14; stable IDs, actor model, retention, privacy, and access rules.
- **Main data objects/tables expected:** Existing fixation runs/input snapshots/results/audit rows as anchors; unified `audit_event`, `run_manifest`, source/parameter/input/output/artifact references, actor, timestamp, contract/engine versions, correlation ID, and retention status.
- **Expected backend work:** Append-only audit event API/service, cross-domain run manifest, trace queries, integrity checks, export for internal audit, retention/legal-hold behavior, and access controls.
- **Expected frontend work:** Client timeline, run history, source-to-output trace, version and actor display, explainability drill-down, and neutral missing-legacy states.
- **Expected tests:** Append-only behavior, referential integrity, complete trace for each workflow, actor/client isolation, tamper detection, legacy gaps, retention, performance, and existing fixation history regressions.
- **Explicit exclusions:** Editing business data from audit screens, using audit rows as source data, silent backfill fabrication, and exposing internal audit to clients without contract.
- **Output:** Complete immutable run history and explainability graph for every accepted output.
- **Next milestone unlocked:** M16.
- **Known unknowns:** Authentication/role integration, retention periods, tamper-evidence mechanism, legal hold, legacy backfill, and audit export format.
- **Stop conditions:** Any output lacks source/input/parameter/run linkage, audit is mutable, actor/client access is unbounded, or fabricated history is required.

### M16 End-to-End Validation and Production Hardening

- **Purpose:** Validate the complete system and make deployment, operations, security, recovery, and performance production-ready.
- **Why needed:** Package-level tests do not prove the full planner-to-client workflow or production resilience.
- **Dependencies:** M01-M15 accepted; production architecture, environments, security/privacy standards, service-level objectives, and operational ownership.
- **Main data objects/tables expected:** No new business objects by default; validation datasets, deployment manifests, backup/restore evidence, observability events, security findings, and release evidence.
- **Expected backend work:** Security hardening, auth/authorization enforcement, migration rehearsal, backup/restore, observability, rate/size limits, performance tuning, failure recovery, and deployment configuration.
- **Expected frontend work:** Full workflow/browser validation, accessibility/RTL/responsiveness, error recovery, production configuration, and performance hardening.
- **Expected tests:** Full backend/frontend suites, builds, migration up/down/rehearsal, E2E golden journeys, browser verification, security/privacy tests, load/concurrency, external outage, backup/restore, artifact rendering, audit completeness, and governance/status checks.
- **Explicit exclusions:** New business capability, formula change, new integration, or output expansion during closure.
- **Output:** Release candidate, exception register, production-readiness report, rollback plan, and final acceptance decision.
- **Next milestone unlocked:** Production release and controlled maintenance only.
- **Known unknowns:** Hosting topology, identity provider, secrets management, SLOs, expected load, monitoring stack, support model, and disaster-recovery targets.
- **Stop conditions:** Any critical validation failure, unresolved security/privacy issue, unrehearsed migration/rollback, unverified backup restore, incomplete audit trace, or unexpected worktree artifact.

## 5. Mandatory Coverage Check

| Required capability | Covered by milestone | Status | Notes |
|---|---|---|---|
| Internal planner workspace | M01 | partial | Existing sections and 02L contract exist; 02M implementation is frozen. |
| Client context | M01 | existing | Client create/list/detail/profile and client-scoped routes exist. |
| Pension holdings | M01, M04 | existing | Fact persistence/API/UI exists; canonical imported ledger is planned in M04. |
| Pension analysis records | M01 | existing | Per-holding create/get/update foundation exists. |
| Planner assumptions | M01 | existing | Client-scoped maintenance exists; not calculation authority. |
| Advisory missing information | M01 | existing | Internal advisory maintenance exists. |
| Consolidated internal review | M01 | existing | Seven-group read-only review exists. |
| Clearinghouse file upload/intake | M02 | partial | Snapshot metadata routes exist; file-byte intake does not. |
| Raw clearinghouse file preservation | M02 | missing | Planned immutable storage and checksum contract. |
| XML parsing | M03 | missing | Planned parser by authoritative format/version. |
| Excel/CSV/manual import if applicable | M03 | planned | Included only if M03 contract names approved formats; otherwise explicitly excluded. |
| Normalized pension balance ledger | M04 | missing | Existing holdings are not the planned imported balance ledger. |
| Balance source traceability | M02-M04 | partial | Existing source metadata is bounded; field-to-raw ledger trace is planned. |
| Balance validation | M03-M05 | partial | Fact validation exists; import/ledger/classification validation is planned. |
| Manual correction layer | M05 | missing | Planned as immutable overlay, not source rewrite. |
| Classification into pension/capital/severance/compensation/savings products | M05 | partial | Some product types exist; full locked taxonomy/classification workflow is planned. |
| Classification for old pension funds/new pension funds/manager insurance/gemel/hishtalmut | M05 | missing | Planned explicit taxonomy and tests. |
| Pension conversion layer | M06 | missing | Planned deterministic engine and snapshots. |
| Capital asset conversion layer | M06 | missing | Capital facts exist; conversion engine is planned. |
| Lump-sum withdrawal modeling | M06, M10 | missing | Planned explicit election in M06 and scenario use in M10. |
| Tax input model | M07 | partial | Fixation input contracts exist; broader tax input model is planned. |
| Fixation rights/kibua integration | M09, M14 | existing | Fixation engine/runs/audit exist; scenario/output integration remains planned. |
| Severance/grant exemption logic | M09 | existing | Bounded Fixation Rights grant logic exists; broader tax orchestration remains planned. |
| Pension exemption logic | M09 | partial | Fixation result includes pension exemption outputs; broader annual tax treatment is planned. |
| Capitalization/hivun logic | M06, M09 | partial | Actual capitalization impact exists in fixation; prospective conversion/tax treatment is planned. |
| Tax spreading/prisa logic | M09 | missing | Planned only after formula and legal authority. |
| Marginal tax logic | M09 | missing | Planned deterministic component engine. |
| National Insurance if relevant | M07, M09 | planned | Scope must be decided in M07; implement only if relevant. |
| Annual tax parameters | M07 | partial | Explicit fixation inputs/constants exist; versioned annual repository is planned. |
| CBS/LMAS or index data API/update layer | M08 | missing | V1 reference is not implementation; approved deterministic ingestion is planned if required. |
| Scenario definition | M10 | missing | Planned immutable versioned scenario contract. |
| Scenario execution | M10 | missing | Planned engine orchestration. |
| Scenario comparison | M11 | missing | Planned comparison over saved outputs only. |
| Net annual result | M10 | missing | Planned annual result rows. |
| Net cumulative result | M10, M11 | missing | Planned run result and comparison metric. |
| Planner judgment layer | M12 | partial | Bounded fixation-run internal judgment exists; scenario judgment is planned. |
| Recommendation layer | M12 | missing | Planned only with explicit professional/legal contract. |
| Client-facing report model | M13 | missing | Planned immutable approved output snapshot. |
| PDF/export | M14 | missing | Planned renderer from approved snapshots. |
| 161D/fixation outputs | M14 | partial | Fixation results exist; formal 161D/output artifacts do not. |
| Audit trail | M15 | partial | Fixation audit exists; cross-domain audit is planned. |
| Immutable run history | M15 | partial | Fixation history exists; conversion/tax/scenario/output run history is planned. |
| Explainability/source trace | M15 | partial | Saved fixation input explainability exists; full source-to-output trace is planned. |
| Full validation | M16 | partial | Package suites exist; full-system E2E validation is planned. |
| Production hardening | M16 | missing | Planned security, operations, recovery, performance, and release validation. |

All required capabilities are assigned to at least one milestone. `Existing` and `partial` statuses are based on current repository anchors; `missing` and `planned` rows are ordering commitments only, not implementation evidence or authority.

## 6. Sequencing Rules

1. No milestone may be opened before every named dependency is accepted and its checkpoint confirms the next milestone boundary.
2. Once this sequence is accepted, candidate selection is not allowed; packages execute the next unmet dependency in milestone order.
3. Every future package must reference one milestone ID (`M01`-`M16`) and one unique package ID.
4. Future packages must not invent or substitute a new product direction.
5. A package may be skipped only when this Master Sequence marks the capability `existing` and a read-only review confirms the existing implementation satisfies that milestone's exact contract and acceptance evidence.
6. `Partial` never permits skipping the missing portion.
7. A blocker must name one concrete technical blocker: the exact missing endpoint, schema, model, service, parser contract, external specification, formula, component, environment dependency, or failing validation, plus the exact package needed to remove it.
8. Generic planning, authority, discovery, risk, or readiness language is not a blocker after this sequence is accepted.
9. Each milestone must be split into narrow contract, schema/data if needed, backend, frontend, validation, review, commit, and closure packages appropriate to its actual dependency graph.
10. No calculation engine may consume live mutable or external data; it consumes versioned snapshots only.
11. Source facts, corrections, assumptions, engine inputs, engine outputs, judgments, and display artifacts remain separate.
12. Every package follows `specs/acceptance/package_acceptance_standard.md`; documentation alone is not positive implementation evidence.

## 7. Package Instruction Standard v2

Every future implementation instruction must contain all fields below:

| Required field | Standard |
|---|---|
| Milestone ID | One exact ID from `M01`-`M16`. |
| Package ID | Unique, ordered ID under the milestone. |
| Purpose | One concrete deliverable that unlocks a named dependency or milestone output. |
| Exact allowed files | Exact repository paths. Directory patterns are insufficient at execution time unless the package creates a new directory with an exact file manifest. |
| Exact forbidden files | All files outside the allowlist plus named high-risk areas and behaviors. |
| Expected behavior | Inputs, outputs, state transitions, API/UI behavior, ownership, immutability, errors, and source-of-truth rules. |
| Explicit non-goals | Adjacent milestone behavior and every tempting expansion excluded from the package. |
| Tests required before commit | Exact targeted tests plus relevant regression, build, migration, runtime, browser, rendering, security, or external-failure tests. |
| Full validation when relevant | Backend suite, frontend suite/build, migrations, E2E, governance, git status, and milestone-specific validation. |
| Stop conditions | Exact technical conditions requiring stop before broadening or fixing outside scope. |
| No-broadening rule | No file, behavior, dependency, formula, integration, or output outside the accepted package contract. |
| Exact blocker format | `BLOCKER: <one concrete missing/failing item>; EVIDENCE: <command/path/error>; REQUIRED PACKAGE: <ID/name>; ALLOWED FILES: <exact paths>; UNLOCKS: <dependency>.` |
| Review-before-commit | Read-only status, scoped diff, full changed-file content, command evidence, exceptions, and acceptance recommendation; no edits/tests/commit during review unless explicitly requested. |
| Post-commit checkpoint | Confirm HEAD/subject, exact committed files, clean or approved status, accepted evidence, unresolved exceptions, and whether the next named package may open. |

Every package must also report files changed, exact commands/results, exceptions, final git status, and commit status. A package with an unnamed file, formula, source, or dependency stops before implementation.

## 8. Anti-Failure Rules

- Do not call a milestone plan a full-system plan.
- Do not use product discovery to choose the next package once this sequence is accepted.
- Do not select "lowest risk" evidence-only work unless it is the next milestone dependency.
- Do not return NO-GO without one concrete technical blocker in the Package Instruction Standard v2 format.
- Do not create governance packages that do not unlock implementation, acceptance, or closure of the current milestone.
- Do not reopen admin/settings.
- Do not reopen broad V1/V2 mapping.
- Do not claim implementation evidence from documentation-only packages.
- Do not proceed to code without exact allowed files.
- Do not proceed to commit without a separate read-only review.
- Do not copy V1 code or treat V1 behavior as V2 authority.
- Do not hide missing formulas, source contracts, legal rules, external failure policies, or output approvals behind a generic planning package.
- Do not let UI, reports, comparisons, or recommendations recalculate authoritative numbers.

## 9. Status of 02K/02L/02M

- 02K belongs to **M01 Internal Pension Analysis Workspace**. It is the M01 build plan only, not the full-system plan.
- 02L belongs to **M01 Internal Pension Analysis Workspace**. It is the minimal frontend-first M01 implementation contract only.
- 02M belongs to **M01 Internal Pension Analysis Workspace** and is currently frozen pending review of this Master Sequence.
- If this Master Sequence is accepted after review, 02M may resume as the first M01 implementation package unless that review identifies one concrete technical blocker using the required blocker format.
- This file does not unfreeze or authorize 02M.

## 10. Master Sequence Acceptance Gate

This file is ready for review only. It does not say or imply that the full-system build plan is accepted, and it authorizes no implementation. Review must verify all M01-M16 definitions, dependency order, capability coverage, existing/partial/missing/planned classifications, package standard, and 02M freeze. The next step is a read-only review of this Master Sequence. Until that review accepts the sequence, 02M remains frozen.

Missing required capabilities: none; every required capability is assigned and classified.

Missing milestone definitions: none; M01-M16 each define purpose, need, dependencies, expected data objects, backend, frontend, tests, exclusions, output, unlock, known unknowns, and stop conditions.

MASTER_SEQUENCE_READY_FOR_REVIEW
