<!-- Materialized from the accepted WORK definition in "GPT Work  V2", response 9abe826b-1d46-5829-b13b-0b4b71ecd552. -->

Governance protocol: `RETIREMENT_PLANNING_V2_GOVERNANCE_PROTOCOL v1`.

This Git materialization is docs-only. Implementation remains NOT_AUTHORIZED.
All implementation, migration, deletion, and test requirements below are future
package obligations; none is executed or authorized by this materialization.

`REPLACED_MEANS_REMOVED`: A new canonical path alongside a still-reachable
obsolete professional path is a blocking package failure. No deferred cleanup
package is allowed for the in-scope replaced paths.

# First Recovery Package Definition

## Source verification

| Source | Required commit | Verified tree |
|---|---|---|
| V1 `omerb21/retire` | `e4bd8618cb194aff5f7b9aa0b5388f71cf838292` | `7dbaf217649b680656352e6b03150bd550632aea` |
| V2 `omerb21/retireV2` | `7b5f3739caa67a8422c5fff67ab7386b2f300741` | `cf228c73935857cc81cc14d66da01c8565a5ed75` |

Both inspected worktrees were clean. This definition is based only on those exact commits.

## 1. Exact package name

`FIRST_RECOVERY_PKG_001_CANONICAL_PENSION_PRODUCT_AND_COMPONENT_SOURCE`

## 2. Exact base commit

`7b5f3739caa67a8422c5fff67ab7386b2f300741`

Implementation must begin from this exact V2 commit. A different base requires a new definition audit.

## 3. In-scope PARITY IDs

| ID | Package disposition |
|---|---|
| `PARITY-0002` | Restore direct professional pension-product access without an M01 progression gate |
| `PARITY-0003` | Restore import directly into canonical products/components |
| `PARITY-0004` | Restore manual product creation |
| `PARITY-0005` | Restore the professional pension-product table |
| `PARITY-0006` | Implement the fixed V1 component ontology |
| `PARITY-0007` | Implement exact recognized import-code mappings |
| `PARITY-0008` | Restore direct product/component editing |
| `PARITY-0009` | Restore explicit save without review or conversion side effects |
| `PARITY-0010` | Restore direct product deletion with integrity protection |

Source-model dependencies only:

- `PARITY-0011`
- `PARITY-0012`
- `PARITY-0014`
- `PARITY-0015`

These dependencies require canonical source data suitable for later conversion. Conversion behavior is not implemented here.

## 4. In-scope REMOVAL IDs

- `V2-REM-0001` through `V2-REM-0009`
- Source-side portions of `V2-REM-0018`
- Source-side portions of `V2-REM-0020`

`REPLACED_MEANS_REMOVED` applies. The old M02/M03/M04/M05 professional authority cannot remain reachable after cutover.

## 5. In-scope Parallel Path Risks

- `PPR-001`: competing pension-product source models
- `PPR-002`: M05 ledger as a competing balance authority
- `PPR-010`: generic rewards/contribution classification competing with the fixed ontology
- `PPR-011`: reconciliation totals being treated as conversion components
- `PPR-003`: source-contract dependency of later conversion, limited to caller migration

The package fails if any production path can still choose between canonical values and M02/M05 values.

## 6. Target professional behavior

The ordinary workflow becomes:

1. Open the client’s pension-products screen directly.
2. Import a recognized source or create a product manually.
3. View products, metadata, all predefined component balances and reconciliation totals.
4. See discrepancies without entering a review ceremony.
5. Edit product metadata, component balances or reported totals directly.
6. Save explicitly and atomically.
7. Delete a product subject only to genuine referential-integrity protection.

There is no M01 progression prerequisite and no M03, M04 or M05 professional ceremony.

## 7. Canonical data ownership

### Canonical product

One `pension_products` row per imported or manually created professional product, containing:

- Stable product ID
- Client ID
- Source kind: imported or manual
- Provider name and identifier
- Product name and type
- Account or policy reference
- Product start date
- Statement/balance date
- Historical-employer metadata where available
- Reported product total
- Reported rewards total
- Reported severance total
- Optional technical source linkage
- Optimistic concurrency version
- Created/updated audit metadata

### Canonical components

Each product has exactly these 11 predefined component rows:

| Group | Canonical component |
|---|---|
| Severance | `פיצויים_מעסיק_נוכחי` |
| Severance | `פיצויים_לאחר_התחשבנות` |
| Severance | `פיצויים_שלא_עברו_התחשבנות` |
| Severance | `פיצויים_ממעסיקים_קודמים_רצף_זכויות` |
| Severance | `פיצויים_ממעסיקים_קודמים_רצף_קצבה` |
| Rewards | `תגמולי_עובד_עד_2000` |
| Rewards | `תגמולי_עובד_אחרי_2000` |
| Rewards | `תגמולי_עובד_אחרי_2008_לא_משלמת` |
| Rewards | `תגמולי_מעביד_עד_2000` |
| Rewards | `תגמולי_מעביד_אחרי_2000` |
| Rewards | `תגמולי_מעביד_אחרי_2008_לא_משלמת` |

A database uniqueness constraint must enforce one row per product and component code.

Generic `תגמולים` or `contribution_component` is not a canonical component.

All monetary values use fixed decimal storage, at least `NUMERIC(20,2)`. Floating-point storage is prohibited.

## 8. Exact frontend scope

Add one professional route:

`/clients/:clientId/pension-products`

The screen contains:

- Import control
- Manual-product creation
- Product table
- Editable product metadata
- The 11 fixed component balances
- Reported product, rewards and severance totals
- Computed component sums and discrepancies
- Explicit save
- Delete with confirmation
- Structural/import diagnostics that do not create approval states

Proposed implementation paths:

- `frontend/src/pages/PensionProductsScreen.tsx`
- `frontend/src/api/pensionProductsApi.ts`
- `frontend/src/components/pension-products/PensionProductTable.tsx`
- `frontend/src/components/pension-products/PensionProductRow.tsx`
- `frontend/src/components/pension-products/PensionProductForm.tsx`
- `frontend/src/components/pension-products/PensionImportControl.tsx`
- `frontend/src/components/pension-products/ReconciliationDisplay.tsx`

No conversion control is added by this package.

## 9. Exact backend scope

Create:

- `backend/app/models/pension_product.py`
- `backend/app/schemas/pension_product.py`
- `backend/app/services/pension_product_service.py`
- `backend/app/services/pension_product_import_service.py`
- `backend/app/services/pension_product_reconciliation.py`
- `backend/app/services/canonical_pension_source_reader.py`
- `backend/app/api/pension_product_routes.py`

Required endpoints:

- `GET /api/clients/{client_id}/pension-products`
- `GET /api/clients/{client_id}/pension-products/{product_id}`
- `POST /api/clients/{client_id}/pension-products`
- `POST /api/clients/{client_id}/pension-products/imports`
- `PUT /api/clients/{client_id}/pension-products/{product_id}`
- `POST /api/clients/{client_id}/pension-products/save-selected`
- `DELETE /api/clients/{client_id}/pension-products/{product_id}`

All writes must be transactional and concurrency-protected.

## 10. Exact persistence/migration scope

Create:

- `pension_products`
- `pension_product_components`
- `pension_product_source_links`
- `pension_product_audit_events`

Migration must:

1. Preflight existing active M02/M05 data.
2. Identify products by deterministic provider/account/source identity.
3. Create one canonical product for each deterministic identity.
4. Create all 11 component rows, including zero balances.
5. Map only exact recognized component identities.
6. Populate reported totals only from fields proven to be summary totals.
7. Preserve unmapped material as diagnostics/provenance, never as balances.
8. Reject conflicting or ambiguous active authorities before cutover.
9. Produce counts for products, components, source links, conflicts and unmapped values.
10. Switch every caller and disable old authority in the same deployment.
11. Leave exactly one Alembic head.

No generic amount may be distributed among canonical components.

## 11. Exact import behavior

Recognized employee/employer codes:

- `2`, `8`: employee
- `3`, `9`: employer

Recognized period/layer codes:

- `1`: before 2000
- `2`: after 2000
- `7`, `9`, `13`: after 2008, non-paying

Recognized severance source tags include:

- Current employer:
  - `ERECH-PIDION-PITZUIM-MAASIK-NOCHECHI`
  - `YITRAT-PITZUIM-MAASIK-NOCHECHI`
- Post-settlement:
  - `ERECH-PIDION-PITZUIM-LEKITZBA-MAAVIDIM-KODMIM`
- Unsettled:
  - `TZVIRAT-PITZUIM-PTURIM-MAAVIDIM-KODMIM`
  - `YITRAT-PITZUIM-LELO-HITCHASHBENOT`
- Prior-employer rights continuity:
  - `TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-ZECHUYOT`
- Prior-employer pension continuity:
  - `TZVIRAT-PITZUIM-MAAVIDIM-KODMIM-BERETZEF-KITZBA`

Unknown or ambiguous codes remain unmapped technical diagnostics. They must not be guessed, converted to generic components or block workflow unless the source is structurally invalid.

Repeated import of the same checksum and account is idempotent. A newer statement updates the same canonical product atomically while retaining technical source history.

After successful import, the user reaches the canonical product table directly.

## 12. Exact manual-entry behavior

Manual creation:

- Creates one canonical product.
- Creates all 11 predefined component rows at zero.
- Requires the professional product metadata required by the V1 form.
- Stores the entered total as the reported product total.
- Leaves reported rewards/severance totals null unless explicitly supplied.
- Generates a stable technical product ID.
- Does not create M02, M03, M04 or M05 workflow records.
- Does not infer or distribute component balances.

## 13. Exact direct-edit/save/delete behavior

Users may edit:

- Product metadata
- All 11 component balances
- Reported product total
- Reported rewards total
- Reported severance total

Save is explicit, atomic and independent of review or conversion. Optimistic concurrency must reject stale overwrites.

Delete removes the canonical product and its current component rows in one transaction. Raw technical evidence may remain.

Deletion must fail closed if an existing downstream record would be orphaned. It must never silently delete conversion or historical records.

## 14. Exact reconciliation behavior

Computed display values:

- Rewards component sum = sum of the six rewards components
- Severance component sum = sum of the five severance components
- Product component sum = sum of all 11 components
- Rewards discrepancy = reported rewards total minus rewards component sum
- Severance discrepancy = reported severance total minus severance component sum
- Product discrepancy = reported product total minus product component sum

Reported totals and discrepancies are display/control data. They are not conversion components, do not change component balances and do not create approval or blocking states.

## 15. Retained backend-only technical mechanisms

The package may retain:

- Raw uploaded files
- Checksums
- Immutable source identity
- Source provenance
- Append-only technical history
- Serialized currentization
- Transaction safety
- Audit timestamps and actor metadata
- Import diagnostics

These mechanisms must not:

- Require planner approval
- Expose professional revision chains
- Determine current professional balances independently
- Become prerequisites for direct editing
- Block ordinary use except for structural, concurrency or referential-integrity failure

## 16. Code paths, components, routes and endpoints to DELETE

Delete or remove from production registration:

### Frontend

- `M03SourceReviewScreen.tsx` and tests
- `M04ClassificationScreen.tsx` and tests
- `M05LedgerScreen.tsx` and tests
- `m03ReviewApi.ts`
- `m04ClassificationApi.ts` and tests
- `m05LedgerApi.ts`
- Old professional portions of `M02PensionIntakeScreen.tsx`
- Old M02 lifecycle operations in `m02IntakeApi.ts`
- Routes:
  - `/clients/:clientId/pension-intake`
  - `/clients/:clientId/source-review`
  - `/clients/:clientId/classification`
  - `/clients/:clientId/pension-ledger`
- Navigation, hidden controls and status labels for those workflows

### Backend

- M03 action routes, services and schemas
- M04 preview, revision and revalidation routes, services and schemas
- M05 start, reconcile, warning-review, block, adjust, supersede and revalidate routes, services and schemas
- M02 `accept_for_review`, rejection, supersede and professional lifecycle transitions
- M01 professional lifecycle progression endpoint and gate
- Router registration for all removed endpoints
- Any generic-component professional reader or writer

Reusable pure import mappings must first be moved into the canonical import service.

## 17. Code paths, components, routes and endpoints to REWRITE

Rewrite:

- `frontend/src/routes/AppRoutes.tsx`
- Client-detail navigation and action controls
- Client-detail route tests
- M02 upload handling into the canonical import boundary
- `backend/app/main.py`
- Model registry and migration bootstrap
- Client summary API where it exposes lifecycle stages
- Localization resources for removed statuses and the new table
- M06 source-selection imports and queries
- Test fixtures and factories that construct active M02/M05 authority

M06 may read only through `canonical_pension_source_reader.py`. If its current semantics cannot use canonical components safely, the affected action must fail closed. It must not fall back to M02/M03/M04/M05.

## 18. Models/tables/columns allowed to remain backend-only

The following may remain physically present:

- M02 preserved blob/source tables
- Raw-source checksums and storage metadata
- Historical M02/M03/M04/M05 records required for audit preservation
- Historical foreign-key targets required by existing M06 records

Conditions:

- No production route may expose them as current professional state.
- No production writer may create new professional revisions.
- No current balance query may read them.
- They must be clearly frozen/archive-only.
- They may not block the canonical workflow except to prevent destructive referential corruption.

Physical retention is not authority retention.

## 19. Callers that must be migrated

At minimum:

- Application router registration
- Client-detail navigation
- M02 import/upload callers
- Client summary/status presentation
- M01 lifecycle consumers
- M06 candidate/source readers
- Model registry and database bootstrap
- API clients
- Test fixtures and factories
- Any reporting/export code reading M02 declared values or M05 ledger values
- Any background task referencing M03/M04/M05 lifecycle state

No caller migration may be deferred.

## 20. Obsolete tests to delete or rewrite

Delete tests whose required outcome is an obsolete workflow:

- M03 review and annotation tests
- M04 preview/revision/revalidation tests
- M05 start/reconcile/warning/adjust/supersede/revalidate tests
- Frontend M03/M04/M05 screen tests
- M01 progression-gate tests
- M02 `accepted_for_review` lifecycle tests
- Generic `contribution_component` authority tests

Raw preservation, transaction and Decimal-integrity tests must be migrated, not discarded.

## 21. New parity tests required

Tests must prove:

- Exactly 11 components per product
- Exact employee/employer and period mappings
- Exact severance-tag mappings
- Unknown codes remain unmapped
- Import idempotency and statement currentization
- Manual creation produces the complete zero-valued ontology
- Direct edit and atomic save
- Optimistic concurrency rejection
- Product deletion and referential protection
- Three independent reconciliation calculations
- Reported totals never become components
- No automatic distribution of generic amounts
- Direct route access without M01 progression
- No M03/M04/M05 creation during import, edit or save
- M06 source reads use canonical tables only
- Historical tables cannot determine current balances
- Migration aborts on ambiguous competing authority

## 22. Dead-code/reachability proof

Future acceptance evidence must include repository-wide searches proving no production reachability for:

- M03 UI route, action API or annotation path
- M04 preview or revalidation workflow
- M05 start/reconcile/warning/supersede/adjust/revalidate workflows
- User-triggered M05 revalidation
- M01 professional progression gate
- M02 `accept_for_review`
- Generic `contribution_component` authority
- Duplicate M02/M05 balance readers
- Hidden navigation
- Fallback implementations
- Feature flags restoring old workflows
- Obsolete tests enforcing removed behavior

Search targets must include symbols, endpoint fragments, route strings, imports, navigation definitions, status enums, test names and feature-flag configuration.

Acceptance also requires:

- Frontend production build
- Backend and frontend test suites
- `git diff --check`
- Clean tracked worktree/index
- Exactly one Alembic head
- A database-query or architecture test proving canonical-table-only current balance reads

## 23. Explicit out-of-scope list

- Actual conversion execution
- Full M06 replacement
- Pension destination creation
- Capital destination creation
- Source depletion or reversal
- Conversion-rule matrix implementation
- Employer termination workflow
- Fixation changes
- Scenarios
- Cashflow
- M09
- M10
- M11-M14
- Visual redesign beyond the canonical working screen
- Product-owner reinterpretation of unknown import codes

## 24. Acceptance criteria

The package is accepted only when:

1. The canonical product and 11-component model is operational.
2. Import and manual entry reach it directly.
3. Direct edit, save and delete work atomically.
4. Reconciliation totals remain distinct from components.
5. Exact recognized V1 mappings are covered by tests.
6. Ambiguous values are not inferred.
7. All current professional balance readers use canonical tables.
8. M02 and M05 cannot determine current professional balances.
9. No M03/M04/M05 professional workflow is reachable.
10. No M01 or M02 progression prerequisite remains.
11. M06 has no fallback to an old source authority.
12. All callers are migrated in the same package.
13. Mandatory repository-wide deletion searches pass.
14. Obsolete workflow tests are absent.
15. Historical evidence and technical integrity remain preserved.
16. Migration completes without unresolved competing authority.
17. Worktree, schema graph and test suites pass the required integrity checks.

A new canonical screen alongside a reachable old path is a blocking failure.

## 25. Rollback and data-migration risks

| Risk | Required control |
|---|---|
| Ambiguous generic M02/M05 values | Preflight failure; no automatic classification |
| Duplicate provider/account identities | Deterministic identity report and conflict resolution before cutover |
| Summary totals mistaken for components | Separate columns and explicit mapping allowlist |
| Decimal drift | Fixed-decimal database and API validation |
| Existing M06 foreign keys | Preserve archive targets and migrate source reads |
| Product deletion with downstream references | Transactional fail-closed deletion |
| Loss of raw evidence | Retain immutable blob/source records and checksums |
| Partial deployment creating two authorities | One atomic deployment/cutover; no temporary feature flag |
| Downgrade after canonical writes | Pre-cutover backup and tested reverse migration, or prohibit unsafe downgrade |
| Migration interruption | Transactional migration with restart-safe preflight and verification |

Implementation rollback must never reactivate the old professional authority while retaining newer canonical writes without a verified reverse transformation.

# Final decision

`ACCEPT_FIRST_RECOVERY_PACKAGE_DEFINITION`

This decision accepts the definition only. It does not authorize implementation.

- `FIRST_STAGE_INTEGRATED_SYSTEM_AND_UI_VALIDATION`: `ACTIVE`
- `M11-M14`: `NOT_AUTHORIZED`
- Next implementation package: `NOT_AUTHORIZED`
- `02M`: `FROZEN`
- `M08E`: `EXCLUDED`
- Production readiness: `NOT_CLAIMED`
