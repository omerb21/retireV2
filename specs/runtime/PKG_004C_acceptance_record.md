# PKG-004C Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-004C — M08A Eligibility Date Evidence Contract` |
| Status | `ACCEPTED` |
| Accepted implementation HEAD | `bd92733fe3e4834cdd9230f07e382734181b1a0a` |
| Base | `870afee14e0ba39af1c13daeb4a598615aa88e3e` |
| Alembic head | `a9c4e7f2b615` |
| Definition | `specs/runtime/PKG_004C_FINAL_PACKAGE_DEFINITION.md` |

## Accepted Scope

PKG-004C establishes:

- the exact B1 field code `eligibility_date`;
- the meaning: date of eligibility used by the bounded M08A
  fixation-rights calculation;
- strict string representation as `YYYY-MM-DD`;
- valid-calendar-date enforcement;
- valid leap-date support;
- rejection of:
  - blank values;
  - null values;
  - year-only values;
  - age or other numeric values;
  - localized dates;
  - free text;
  - invalid calendar dates;
  - datetime values;
  - timezone-bearing datetime values;
  - Python date or datetime structured values;
  - nested or adjacent-field objects;
- support through the existing B1 fact-evidence and planner-assertion write
  paths;
- preservation of client, revision, source, and provenance boundaries;
- atomic validation failure without evidence mutation;
- continued distinction between `eligibility_date` and
  `retirement_timing`.

## Eligibility-Year Boundary

- `eligibility_year` is not a B1 evidence field.
- It was not introduced by PKG-004C.
- It will be derived later as `eligibility_date.year`.
- A caller-supplied conflicting year remains prohibited.
- No automatic legal or professional eligibility-date derivation exists.

## Existing Mechanism

The implementation uses:

- `M07FactEvidence.structured_value`;
- `M07PlannerAssertion.asserted_value`;
- the existing B1 write services;
- the existing client and revision ownership checks;
- the existing provenance and fingerprint mechanisms.

No new persistence model was introduced.

## Explicitly Absent

PKG-004C does not introduce:

- a new table;
- a migration;
- a new evidence lifecycle;
- a current selector;
- source ranking;
- latest-wins selection;
- qualification;
- warning review;
- accepted-for-use state;
- professional approval;
- a direct B2 input;
- a production M08A manifest;
- B2-to-M08A integration;
- any fixation route, admission, dependency, snapshot, engine, or formula
  change;
- historical conversion or backfill;
- reinterpretation of `retirement_timing`.

## Acceptance Evidence

Focused audit result:

`FOCUSED_AUDIT_PASSED_ACCEPT_PKG_004C`

| Audit area | Result |
|---|---|
| Repository safety | `PASS` |
| Accepted implementation commits | exactly two |
| Changed files | exactly two |
| Exact field identity | `PASS` |
| Strict date validation | `PASS` |
| Write-path completeness | `PASS` |
| B1 isolation and provenance | `PASS` |
| No adjacent-field reinterpretation | `PASS` |
| Forbidden architecture | `PASS` |
| Defects | `none` |

Test and verification evidence:

| Verification | Result |
|---|---|
| Focused PKG-004C | `29 passed` |
| PKG-004B1 evidence | `47 passed` |
| PKG-004B2 resolver | `24 passed` |
| Focused client-isolation slice | `6 passed` |
| Independent two-path matrix | `30 invalid-path rejections and 4 valid writes` |
| Python compile | `PASS` |
| Alembic | single head `PASS` |
| Git diff check | `PASS` |
| Prior full backend implementation evidence | `530 passed` |

Frontend tests and the frontend build were not run because no frontend files
changed.

## Accepted Limitations

The following are accepted package boundaries:

- no production M08A manifest;
- no B2-to-M08A integration;
- no change to obsolete M07 qualification gates in fixation admission;
- no dependency-manifest integration;
- no automatic determination of the professional or legal eligibility date;
- no UI or API;
- no historical mapping from `retirement_timing`;
- no M08-completion or production-readiness claim;
- no V1/V2 parity claim.

## Follow-Up Boundary

- The next possible package may define the narrow B2-to-M08A consumer
  integration.
- That later package must separately register an M08A-specific production
  manifest.
- It must separately replace obsolete M07 qualification admission gates.
- It must preserve the M08B, M08C, and M08D boundaries.
- PKG-004C acceptance does not authorize that work.
- No next package is authorized by this acceptance record.
