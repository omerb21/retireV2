# Canonical pre-retirement capital projection execution — implementation evidence

Authority: accepted consolidated definition SHA256
`E8C00818AACD8F325FB86B2BCCA6F4E12B09C7DC61AC5B553F2B6AC2EAC931C2`.
Base `ec5d7fbb92a72d2378c514b04f07665e8da652c9`, tree
`b9bf11ae69f4a897659ca9ee12b8e7a186ed3edd`. Document 3 overrides 2 overrides 1.

## Arithmetic proof

The mathematical inputs remain exact Decimal A/r and integer n=4*days, denominator
1461. Each of the seven precisions 80,160,320,640,1280,2560,5120 restarts from
those inputs. Directed addition encloses exact B=1+r even when it does not fit
the current precision; no rounded B or q becomes exact authority.

Python Decimal `ln` and `exp` guarantee correctly rounded HALF_EVEN values:
<https://docs.python.org/3.11/library/decimal.html#decimal.Decimal.ln> and
<https://docs.python.org/3.11/library/decimal.html#decimal.Decimal.exp>.
The immediately preceding/following p-digit representables enclose a correctly
rounded result's exact real value. Applying that bound to ln(B_lower/upper),
then directed multiplication by positive n and division by positive 1461,
then bounding exp at each endpoint, preserves enclosure by monotonicity.
No empirical agreement of approximations is used as evidence.

For A>0, floor(A*F_lower), ceiling(A*F_upper) enclose A*F; for A=0 the
amount interval is exactly [0,0]. A<0 is outside admission and never multiplied.
Both complete intervals must have identical C34 endpoint representations.
C34 uses exact integer digit rounding with ties-to-even; it does not depend on
the ambient Decimal context or currency scale. No serialized factor is reused
for multiplication. The first successful step returns; failure at 5120 returns
only PROJECTION_EXECUTION_NUMERIC_DOMAIN_FAILURE. Fixed exponent limits are
technical representation limits, not professional caps; underflow, subnormal,
clamping, overflow and nonfinite bounds cannot become authoritative results.

## Independent oracle

Golden estimates are not trusted: test-only Fraction arithmetic certifies
`lower**denominator < (1+r)**numerator < upper**denominator` exactly, without
the production ln/exp-neighbour algorithm. Bounds spanning 130 decimal places
are independently rounded by integer rational division, including amount bounds.
This is the definition's independently certified-enclosure oracle alternative,
not an assertion that two approximations agree. Static golden strings are also
checked against these independently certified intervals.
The real resource-boundary vector r=500000004, days=1461, A=1 has exact factor
500000005**4, a 35-digit integer ending in 5. The general certified interval
straddles this exact Decimal34 tie at all seven steps and fails closed.

Cross-runtime tests distinguish live source reads (identical numeric results)
from identical admitted-input fingerprint tests. Independently inserted DB rows
have different upstream timestamp-bearing planning identities; these are not
identical admission inputs. A separate in-memory boundary fixture supplies one
explicit common planning identity and recertified admissions to both DB-derived
payloads, then proves byte-identical complete execution results/fingerprints.
This does not change or normalize upstream production fingerprint semantics.

## API and reachability

GET `/api/clients/{client_id}/retirement-planning-input/capital-projection` only.
Fresh consistent read transaction -> current planning snapshot -> accepted basis
authority -> complete registry admission -> pure numerical execution -> rollback.
Blocked registries return HTTP409 and no projected sources/fingerprint. Hard
structural/numeric failures return the existing domain-error envelope.
No schema/model/migration/frontend change, no write endpoint/cache/run storage,
no pension/M09/M10 calculation, no monetary total or monetary quantization.

## Acceptance mapping

All test names below are in test_projection_execution.py unless marked PG.

| CPX-AC | Material evidence |
| --- | --- |
| 001,003,004,005,006 | test_golden_certified_independent_oracle |
| 002,007 | test_exact_branches_no_transcendental |
| 008 | test_forged_ready_structure[date] |
| 009,010,011,012,013 | test_registry_fail_closed_before_any_calculation |
| 014 | test_empty_and_unready_context |
| 015,017,018,019,020,021 | test_order_bases_fingerprints_and_metadata |
| 016,041 | PG test_pg_sqlite_byte_identical_and_read_only |
| 022,023,026 | test_api_read_only_stable_and_conflict; PG snapshot/read-only tests |
| 024 | golden oracle; forged float; AST reachability |
| 025 | certified golden endpoints; first-success and fixed-schedule tests |
| 027 | test_pension_excluded |
| 028,029,030,031 | test_reachability_no_schema_frontend_or_downstream_changes |
| 032 | Full backend and governance validation (completed results below) |
| 033,036,037,038,046,047,048 | test_c34_independent_half_even |
| 034,035 | test_golden_certified_independent_oracle |
| 039 | test_internal_factor_not_serialized_factor |
| 040,061 | test_order_bases_fingerprints_and_metadata |
| Result/aggregate envelopes, 005 | test_end_to_end_golden_fingerprint_envelopes |
| 013 (late numeric failure) | test_numeric_failure_after_first_source_never_returns_partial |
| 042,043,044 | AST/Git reachability and API result field checks |
| 045,049,050,052,062,064 | test_fixed_schedule_rejects_matching_approximations |
| 051 | test_first_success_restarts_exact_inputs |
| 053 | test_real_valid_input_halfway_unproven_at_limit |
| 054 | PG test_pg_sqlite_failure_boundary |
| 055,056,057 | test_golden_certified_independent_oracle |
| 058 | test_zero_amount_factor_not_shortcut |
| 059 | test_registry_fail_closed_before_any_calculation[negative] |
| 060 | test_forged_ready_structure[negative] |
| 063 | test_representation_failure_never_fallback |

## Validation

Completed fresh validation on 2026-09-23 (local date), after the resume request.
The interrupted/prior full run is not the final regression evidence.

| Scope | Final result |
| --- | --- |
| Execution focused | 52 passed |
| Planning-input focused | 37 passed |
| Projection-basis focused | 63 passed |
| Governance focused | 14 passed |
| Combined focused | 166 passed, 0 failed, 0 skipped, 1 warning |
| Full backend, restarted from the beginning | 1,268 passed, 0 failed, 36 skipped, 8 warnings; exit 0; 1,625.31 seconds |
| PostgreSQL execution | 3 passed |
| PostgreSQL projection basis | 8 passed |
| PostgreSQL planning input | 7 passed |
| PostgreSQL retirement target | 6 passed |
| Combined PostgreSQL | 24 passed, 0 failed, 0 skipped, 1 warning; exit 0 |
| Alembic | 1.14.0; exactly one head: d9e5a2b8c076 |
| git diff --check | PASS |

All CPX-AC-001 through CPX-AC-064 have material test mappings above; no unmapped
acceptance requirement was identified. This is implementation evidence, not an
independent WORK acceptance verdict.

Environment: existing isolated Docker Python 3.11.16 validation container,
read-only authoritative source mount, writable `/cpx_validation` copy;
PostgreSQL 16.14 isolated fixture clusters. Git subprocesses inherited
process-scoped `core.autocrlf=true`; no host security/configuration change.
The normal full-suite skip conditions were preserved; PostgreSQL opt-in was
enabled only for the separately listed package/dependency PostgreSQL suites.

JUnit artifacts retained inside the existing validation containers:

- Python container `retire-projection-validation-20260916`:
  `/tmp/cpx-resume-focused.xml`, `/tmp/cpx-resume-full-backend.xml`.
- PostgreSQL container `retire-projection-pg-validation-20260921`:
  `/tmp/cpx-resume-postgresql.xml`.

The new final runs had no failures or independent regression to classify.
Warnings were the Starlette/AnyIO deprecation and seven existing PKG-003
Pydantic warnings for adversarial float evidence fixtures; no warning was
suppressed. Earlier fixture comparison issues are explained in the independent
oracle section and were resolved before these final runs.

Read-only repository-wide reference search found execution imports only in the
planning-input GET route and the two execution service modules. AST checks,
captured SQL and before/after database snapshots passed. No source/decision/
snapshot mutation, persisted projected value/run, pension execution, M09/M10
execution, database-native POWER/LN/EXP, authoritative binary float, currency
quantization, model/schema/migration change or frontend change was introduced.

Source/copy integrity after the full run: all 519 tracked/untracked source files
compared byte-identically. PostgreSQL copy comparison also found no differences
across 361 app/test/migration/runtime files. Only this evidence document was
subsequently updated to record the completed results; tested code/tests remained
unchanged. The protected CURRENT_PROJECT_STATE.md SHA256 remained
`94A247000C37B153268937FDD29DAFF4D5E8E3A1711C26FE4130B955E59DDBB6`.

No commit, staging, push or merge. Master/origin/master remain at the base above.
No implementation acceptance or production-readiness claim. No downstream
package authorized; existing governance boundaries remain unchanged.
