# Retire V2 Machine Universe Coverage Verification

Package: `V2-REQ-04_MACHINE_VERIFY_UNIVERSE_COVERAGE`

Repository baseline reviewed: `807b07a0843aaf37860e9f601cbfbd36606ae606`

Implementation authorization: `NO`

## Current Truth

The prose Universe coverage proof is insufficient by itself because its row counts and relationships can drift without an executable failure. This package adds a machine-checkable verifier and mutation tests for the accepted requirement-to-control mapping.

This is governance verification only. It changes no requirement, ledger status, gap, milestone, product behavior, or implementation authority. 02M remains frozen.

## Verifier Scope

`scripts/verify_universe_coverage.py` reads the Required Capability Universe, Mechanical Parity Ledger, Full Gap Register, Master Sequence, and Universe Coverage Proof from a repository root. It checks:

- exactly 137 sequential, unique Requirement IDs and the accepted requirement-status counts;
- exactly 113 unique ledger rows, accepted ledger-status counts, and the exact `L-009` RTL/Hebrew mapping;
- exactly 96 unique gaps, accepted severity counts, and the exact `GAP-096` back-reference;
- every verified, gap, unknown, and domain-decision requirement against its required mechanical rules;
- the exact four domain-decision Requirement IDs;
- M01-M16 presence in the Master Sequence; and
- the final proof PASS marker, required mapping-level conclusion, frozen 02M statement, and absence of the false unfrozen statement.

On success it prints `MACHINE_UNIVERSE_COVERAGE_VERIFICATION_PASS` and concise counts. On failure it exits non-zero and prints every detected failure with a code, optional Requirement ID, expected value, actual value, and source file.

## Mutation Tests

`tests/test_verify_universe_coverage.py` runs the verifier against the current repository and against temporary mutated control copies. The mutations prove failure when `REQ_UNMAPPED` is introduced, `GAP-096` or `L-009` is removed, `REQ-116` loses its gap, the proof falsely says 02M is unfrozen, a Requirement ID is duplicated, or status counts drift.

## Run Commands

```powershell
python scripts/verify_universe_coverage.py
pytest tests/test_verify_universe_coverage.py -q
```

The verifier uses only the Python standard library. The tests use the repository's existing pytest environment; no dependency installation is required.

## Execution Evidence

- `python scripts/verify_universe_coverage.py`: PASS; 137 requirements, 0 failed requirements, 0 unmapped requirements, 113 ledger rows, 96 gap rows, and 4 domain decisions.
- `pytest tests/test_verify_universe_coverage.py -q`: PASS; 8 tests passed, including all seven required mutation failures.

## What This Does Not Prove

This package does not prove implementation completeness, V1 parity, formula correctness, tax or legal correctness, external-provider selection, execution readiness, report/PDF/RTL behavior, or production readiness. It closes no gap, changes no control status, authorizes no implementation, and does not unfreeze 02M.

## Final Status

Ready for review only. 02M remains frozen and no implementation is authorized.

MACHINE_UNIVERSE_COVERAGE_VERIFICATION_READY_FOR_REVIEW
