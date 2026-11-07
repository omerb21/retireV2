# RETIRE V2 - Package 1 unified retirement scenario result contract

Baseline: `d2128b0898fa6bcfd4ad1d035f2f845209fbf68e`
Scope: Package 1 only. Internal Python service, no HTTP route, no migration or write.
Implementation: `app.services.scenario_unified_result_service`.

## Consumer entrypoint

```python
from app.services.scenario_unified_result_service import (
    build_unified_scenario_result, assert_unified_result_current,
)
result = build_unified_scenario_result(
    session_factory, client_id=client_id, scenario_id=scenario_id,
)
current = assert_unified_result_current(
    session_factory, client_id=client_id, scenario_id=scenario_id,
    expected_result_fingerprint=result["result_fingerprint"],
)
```

The factory must be backed by PostgreSQL. The existing
`build_manifest_candidate_snapshot` owner creates one dedicated
`REPEATABLE READ READ ONLY` transaction and uses the already accepted
`build_inert_manifest` and source-partition validator. No HTTP permission is
introduced by this package. A later authorized route must apply the existing
authentication/CSRF/client isolation boundary. Direct Python callers are
trusted internal services only.

## Closed semantic envelope V1

- `schema_version`: `UNIFIED_RETIREMENT_SCENARIO_RESULT_V1`
- `identity`: `client_id`, `scenario_id`, `scenario_version`,
  `scenario_status`.
- `reference_dates`: separate client-intended date, explicit planning
  base date and target date, planning decision version and fingerprint. A
  client's suggested date never silently replaces a missing planning date.
- `client_facts`: client identity, birth date, employment status and
  update timestamp (no client name or identification number).
- `manifest_fingerprint`, `source_candidate_state`, `source_facts`:
  existing DB-owned source identities, versions, balances and hashes
  restricted to referenced components. These are **not** all client assets.
- `decisions`: original canonical inert decision + source integrity state,
  version-bound draft pension election, election integrity state, and
  `dependency_fingerprint`. Saved elections never imply coefficient approval.
- `assumptions`: explicit active client-level assertions, owner, effective
  dates, review date, version-sensitive fingerprint via complete envelope.
  They are not execution-ready professional evidence.
- `income_target`: existing user-confirmed goal metadata, if present. A
  monetary target is not a calculated pension, and is not re-admitted
  for scenario execution by this package.
- `financial_domains`: pension gross, capital, severance, fixation/tax,
  monthly cashflow and comparison. Each has `state`, `result=None`,
  `professional_authority=False`, `result_fingerprint=None`.
- `blockers`: stable sorted reasons, including missing retirement target,
  source drift, stale/missing draft election, inactive scenario.
- `execution_allowed=False`, `professional_authority=False`.
- `result_fingerprint`: SHA-256 over all other canonical envelope fields.

No amount can become `VALID` merely by providing a caller-supplied result.
Financial domains remain `NOT_CONNECTED` when structural inputs are sound
or `BLOCKED` when dependency blockers exist. The future package 2 must
explicitly define, validate and admit each engine result in a consistent
snapshot before introducing a `VALID` financial domain.

## Invalidation and reproducibility

- All inputs are read in one PostgreSQL snapshot; no write transaction.
- Repeated reads without modifications yield identical fingerprints.
- Changes to source balances/version, decisions, client facts, retirement
  target, planning version, election, or active planner assumptions change
  the overall fingerprint.
- Individual decision fingerprints bind their own decision/source/election
  evidence. They do not imply independence of professional results:
  all future result admissions must also bind the full scenario version.
- A caller with a previous fingerprint must re-derive via
  `assert_unified_result_current`; failure or mismatch never authorizes old
  results.
- Missing source is `MISSING`; stale source/election is `BLOCKED_STALE`;
  structurally current source is `CURRENT_STRUCTURAL_ONLY`. None means a
  certified pension or tax entitlement.
- Source facts are only from the canonical DB owner. No external preimage
  claims are accepted. No professional admission is carried or fabricated.

## Deferred to Package 2

1. Admission-controlled positive PTE results in the same scenario/version
   identity, without reusing a past professional approval.
2. Canonical capital, severance and fixation mapping with explicit authority,
   periods, tax-year rules and source fingerprints.
3. Compatible monthly gross/net cashflow and comparable price/date bases.
4. Data contract/engine validation for every future populated financial
   domain. No historical M06/M09/M10 archive promotion.

## Tests

Focused test source: `backend/tests/test_scenario_unified_result.py`.

From `backend` with Python 3.11 dependencies installed:

```powershell
python -m pytest -q tests/test_scenario_unified_result.py
python -m pytest -q tests/test_scenario_input_manifest.py tests/test_scenario_snapshot_candidate.py tests/test_scenario_draft.py tests/test_scenario_pension_election_store.py
```

Test status on delivery: **NOT RUN**. The executor's runtime has no authenticated
checkout of the private repository. No GitHub Actions, Render deploy, Neon
writes or existing acceptance gates were executed.

Use existing approved Windows/PG16 acceptance runner only if the supervisor
separately requests its execution; no need to rerun already closed Staging
write gates solely because this internal, unmounted service was added.
