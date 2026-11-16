# RETIRE V2 | Supervisor 130 | UI write-ownership and controlled legacy exceptions

Scope: frontend navigation, presentation, and test acceptance only.
Repository: `omerb21/retireV2`. Baseline: `7af2b7a8fbae4f7133a8b4ce7a7d71f4925e09e1`.
No database, tax, admissions, canonical-conversion engine, or clearinghouse-parser change is authorized.

## Authoritative data boundaries

| Entity | Backend authority (unchanged) | Ordinary primary workflow | Pre-130 UI writers | Post-130 write surface and controlled exception |
| --- | --- | --- | --- | --- |
| Client / M01 case | `getClient` / `updateClientCase` | Workspace > Client > `UnifiedClientIntake` | M01 `ClientDetailScreen`, intake | Intake remains primary; **EX-C01** legacy M01 editor remains for extended validation/evidence until parity acceptance |
| Client profile/contact | `getClientProfile` / `updateClientProfile` | Workspace > Client > intake contact details | M01 `ClientDetailScreen`, intake | Intake primary; **EX-C01** profile/professional identification and extended evidence remain in M01 |
| Pension product metadata | Pension Products API, product version CAS | Workspace > portfolio, diagnostic link to product editor | `PensionProductsScreen` | **EX-P01** advanced product editor retained for metadata, manual creation and deletion; not duplicated in primary path |
| Pension components and balances | Pension Products API `savePensionProduct` with `expected_version` | Workspace money-color ledger factual correction | Workspace and `PensionProductsScreen` | Workspace primary; **EX-P01** old component editor remains reachable under explicitly marked specialist tool until its metadata/conversion/deletion workflow is fully covered and accepted |
| Clearinghouse batch | `importPensionProducts` existing atomic import endpoint | Workspace > portfolio > `WorkspaceClearinghouseImport` | `PensionProductsScreen` and workspace | Main import is primary; **EX-P02** legacy import retained for rollback-free compatibility. No independent data store or parser |
| Canonical conversions | Existing canonical-conversions API and ledger | Advanced product tool | `CanonicalComponentConversionDialog` | **EX-P03** exclusive canonical-conversion UI, deliberately NOT merged with factual correction |
| Employment | Existing client employment endpoints | Workspace > supplementary | Workspace and `EmploymentHistoryScreen` | Workspace primary for documented add/edit; **EX-S01** extended legacy employment tools retained until full parity |
| Grant | Existing grant and employment linkage endpoints | Workspace > supplementary | Workspace and `GrantsScreen` | Workspace primary for documented add/edit/link; **EX-S01** extended legacy grant tools retained until full parity |
| Actual capitalization | Existing actual-capitalizations endpoints | Workspace > supplementary summary > specialized editor | `ActualCapitalizationsScreen` | **EX-S02** only detailed capitalization writer remains specialized (not duplicate) |
| Capital assets, recurring income/expense, projection assumptions | Existing planning-input endpoints | Workspace > supplementary > specialized editor | `PlanningInputScreen` etc | **EX-S02** writer remains specialized until a fully tested embedded editor exists |
| Scenario drafts/elections | Existing scenario-drafts API/version CAS | Workspace > planning and results | `ScenarioDraftPanel` | One underlying draft API; workspace-selected scenario is authoritative in both render modes |
| Professional fixation/admissions | Existing ledger, actor and source-fingerprint validators | Scenario > specialized professional panels | Existing specialized components | Unchanged, remains separated from execution authority |
| Calculated results | Stage 6 API and professional gates | Workspace > results | Stage 6 panels | Read/admission-only; no new execution permission |

**Controlled exception** means: existing professional writer is retained, explicitly reachable only through the specialist flow, anchored to the current client identity, and subject to its unchanged backend validation. This is a temporary, disclosed overlap, not proof of complete write consolidation.

## Workspace navigation and identity

- `/clients/:id/workspace` is the routine entrypoint.
- Routes for individual client professional tools reuse the `professional-workspace` frame and expose all five return steps, retaining `:id`.
- `?step=client|portfolio|supplement|scenario|results` selects the return step. Unsaved client-side editors block query-based navigation; client-switch cleanup remains intact.
- Standalone legacy fixation routes without `:id` are **EX-N01**, retained for compatibility and excluded from normal client workflow. Their client-binding behavior must be tested before deprecation.
- The main portfolio table is the sole ordinary factual product table. The second *planning* matrix is a different, scenario-only decision surface, not a competing factual table.
- The main table now displays canonical imported/manual origin, recorded source-history count, `SOURCE_PRESENT_NONZERO_UNMAPPED` diagnostics and reconciliation discrepancies. No missing source values are inferred or silently converted to zero.

## Preserved authority separation

1. Factual correction: `savePensionProduct` on actual product balances with product-version CAS.
2. Canonical conversion: existing `CanonicalComponentConversionDialog`, with its own ledger and permissions.
3. Planned conversion: `ScenarioConversionMatrix` to versioned scenario draft, never the source balance.
4. Professional review: pre-existing signed/recorded admission and approval records. No calculation permission automatically follows.

## Exit criteria for controlled exceptions

- **EX-C01:** demonstrate exact field/validation/evidence parity and cross-page save-refresh for M01 and profile before disabling any duplicate editor.
- **EX-P01 / EX-P02:** verify import repeatability, source diagnostics, all eleven component codes, full product metadata, manual create/delete, canonical conversion, version conflict handling, and independent audit history. Only then can old duplicate component/import controls be removed.
- **EX-S01 / EX-S02:** verify all specialized grant, employment, capitalization and planning-source operations, including long-tail historical cases and cross-module invalidation, before replacing their editors.
- **EX-N01:** verify client-specific legacy fixation/history deep links and no foreign-client context before a route change.

## Focused acceptance and rollout gate

The isolated `run_supervisor110_acceptance_win.ps1 -ExpectedHead <verified SHA>` runner now includes:
- Real PostgreSQL 16 approval/race and import-API tests;
- Frontend tests for workspace client and import workflow, source warnings, scenario selection, approval and navigation;
- TypeScript build validation;
- Localhost-only Chromium Supervisor 110 + Supervisor 130 journey;
- Screenshots `01-client.png`, `02-portfolio.png`, `03-supplement.png`, `04-scenario.png`, `05-results.png`, plus API evidence.

Supervisor 130 browser scenario uses a synthetic new client and the verified XML structure from `test_recovery_pension_products.py`; it asserts imported source identity, the single central ledger, return navigation, and another client's isolation.

**Not yet demonstrated:** a real successful execution of this runner; complete editing parity of all controlled exceptions; full browser coverage of canonical conversions, grant/IDF edge cases and concurrency; production UX visual acceptance. These remain release blockers. Do not claim full consolidation or remove retained editors until their acceptance passes.
