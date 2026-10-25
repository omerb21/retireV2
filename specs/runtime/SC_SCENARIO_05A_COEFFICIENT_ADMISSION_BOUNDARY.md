# RETIRE V2 — SC-05A: scenario annuity coefficient admission boundary

**Status:** design checkpoint; not accepted for execution. Baseline SC-04 PASS at `feaa35c2b21599a59883f2e493f8e2f6e9fb49ab`.

## Existing production behavior

`canonical_component_conversion_service.preview()` is **not read only**. It calls `lock_client()` and `_preflight()`, which calls `get_product(..., locked=True)` and `PensionProductComponent ... with_for_update()`. It cannot be invoked from the Scenario PostgreSQL READ ONLY snapshot. `execute()` creates conversions, pensions, allocations, changes component balances and product version, and writes audit events; it is categorically prohibited in a scenario evaluation.

`annuity_coefficient_service.coefficient()` looks up controlled `snapshot.json` with a verified checksum, but has potentially material defaults:
- missing gender interpreted as male;
- missing date of birth and retirement_age becomes age 67;
- missing target_year becomes host-local current year;
- missing `survivors_option` becomes `תקנוני`;
- missing match **or caught lookup failure** returns coefficient **200** with `fallback_used=True`;
- product.start_date can determine insurance generation. It must originate from the same trusted scenario source state.

Those defaults and a historical conversion's persisted coefficient cannot be silently treated as admitted scenario calculation assumptions.

## Proposed narrow SC-05A contract

Introduce a deterministic pure **coefficient eligibility assessment**. Inputs: one verified scenario decision, verified current product/profile facts, **explicit** scenario pension options, immutable coefficient catalog version, verified source/manifest identity. Do not invoke `preview`, `execute`, or financial projection.

Output states:
- `BLOCKED` for missing/invalid identity, source, professional permission, pension effective/start date or coefficient inputs.
- `UNRESOLVED` when a new scenario-specific, explicitly selected coefficient is unavailable.
- `COEFFICIENT_CANDIDATE_NOT_ADMITTED` only if all explicit inputs are present and the existing controlled catalog returns an actual catalog match with `fallback_used=False` and nondefault `source`. Candidate is not a monthly pension result or professional admission.

Always return `execution_allowed=False`, `financial_result=None`, `planning_snapshot=None`, `authority_state=NOT_EVALUATED`. Bind result to `client_id`, `scenario_id`, `scenario_version`, `manifest_fingerprint`, `decision_id`, verified product/component IDs, product version, and catalog version.

Proof obligations: missing birth date/gender, missing start date, missing pension election/options, missing target year, unmatched catalog, or any fallback code may never produce an admitted candidate. Keep category-specific policy explicit (pension fund versus insurance). No financial calculation or new persistence.

## First execution unit

Write focused tests for **absence of implicit assumptions** before building the adapter. No broad Codex/Work/CI. The code may call the coefficient lookup only after explicit source/profile inputs were validated; assert `fallback_used=False`. Distinguish a valid candidate factor from authorized scenario computation.

**Important:** the existing conversion matrix permits pension destinations for several product types, but matrix eligibility is not equivalent to regulatory/professional permission. SC-04 historical lineage is never coefficient authority.
