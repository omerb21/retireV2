# PKG-004D Acceptance Record

## Identity

| Field | Value |
|---|---|
| Package | `PKG-004D — M08A Resolver Admission Integration` |
| Status | `ACCEPTED` |
| Accepted implementation HEAD | `4ab2c9a295a82f00a23007dada1f48b999295234` |
| Base | `404c6becb3361309e97f14e3b3416a49798551ad` |
| Alembic head | `a9c4e7f2b615` |
| Definition | `specs/runtime/PKG_004D_FINAL_PACKAGE_DEFINITION.md` |

## Accepted Scope

PKG-004D establishes:

- one server-owned production manifest:
  - scope `m08a_fixation`;
  - version `1`;
  - one required field only: `eligibility_date`;
  - type `date`;
  - normalizer `iso_date`;
  - null prohibited;
- server-side invocation of PKG-004B2;
- authoritative client ID from the route;
- a B1 revision reference and optional conflict selections;
- exactly three resolver outcomes:
  - `resolved`;
  - `missing_inputs`;
  - `ambiguous_inputs`;
- server-derived `eligibility_year = eligibility_date.year`;
- removal of caller-supplied M07 qualification context from
  new-calculation admission;
- rejection of direct caller-supplied eligibility date, year, scope, version,
  outcome, fingerprint, normalized values, and source references;
- no fabricated `qualified` state;
- missing and ambiguous resolution stopping before CBS and engine invocation;
- unchanged construction of the existing `FixationInput`;
- unchanged fixation engine and formulas.

## Request and Admission Boundary

New calculations use:

- `m07_input_reference.b1_evidence_revision_id`;
- optional valid PKG-004B2 selections;
- existing non-M07 M08B, M08C, and M08D request content.

The accepted boundary confirms:

- `validate`, `calculate`, and `save` use the shared admission boundary;
- no alternate helper path can use legacy `M07EntryContext` to admit a new
  calculation;
- request schemas forbid unsupported extra fields.

## Resolver and Isolation Behavior

- A finalized same-client B1 revision may resolve.
- Draft, missing, and foreign-client revisions fail safely.
- Missing and foreign references have equivalent external behavior.
- No caller-forged resolver result is accepted.
- No B1 evidence is mutated.
- Stale, unavailable, wrong-field, or foreign-revision selections cannot
  resolve ambiguity.

## M08 Boundary Preservation

### M08B

The following remain unchanged:

- the caller-supplied parameter wrapper remains temporarily in place;
- tax-year matching uses the server-derived year;
- effective-period checks use the resolved date;
- accepted-for-use and fail-closed behavior remain;
- no official-parameter-resolver integration occurred.

### M08C

The following remain unchanged:

- collection states;
- grant and capitalization inputs;
- future grant reservation;
- inclusion decisions;
- conflict behavior;
- support status;
- accepted-for-use gates.

### M08D

The following remain unchanged:

- the CBS server trust boundary;
- caller-forged system-evidence rejection;
- asserted/system-calculated distinction;
- typed failures;
- no fallback;
- no CBS call before successful M07 resolution.

### Engine

- The `FixationInput` definition is unchanged.
- The fixation engine is unchanged.
- Formulas are unchanged.
- Golden outcomes are unchanged.
- B1, B2, and resolver concepts do not enter the engine.

## Snapshot and Dependency Evidence

New snapshots preserve:

- B1 revision ID;
- scope;
- manifest version;
- resolver outcome;
- resolver fingerprint;
- normalized eligibility date;
- derived eligibility year;
- source references;
- explicit selection evidence when used;
- existing non-M07 admitted input context.

The new dependency-manifest version is:

`pkg004d.fixation-dependency-manifest.v2`

The accepted dependency behavior confirms:

- v2 uses resolver evidence instead of M07 qualification state;
- materially identical v2 evidence compares as unchanged;
- material resolver changes compare as changed;
- v1-to-v2 and v2-to-v1 compare as technically `unknown`;
- source ordering alone does not create a false material change where order is
  non-material;
- historical v1 manifests and snapshots remain readable;
- no historical rewrite or backfill occurred.

## Explicitly Absent

PKG-004D does not introduce:

- a migration;
- a database model;
- a persistent B2 resolution table;
- a resolution lifecycle;
- frontend or UI;
- a new public calculation API;
- historical backfill;
- source ranking;
- latest-wins behavior;
- qualification or approval fabrication;
- an M08B redesign;
- M08C gate removal;
- M08D weakening;
- a formula change;
- M08E;
- full M08F;
- M09-M14;
- formal 161D;
- 02M;
- a production-readiness claim;
- a V1/V2 parity claim.

## Acceptance Evidence

Focused audit result:

`FOCUSED_AUDIT_PASSED_ACCEPT_PKG_004D`

| Audit area | Result |
|---|---|
| Repository safety | `PASS` |
| Accepted implementation commits | exactly three |
| Changed-file scope | expected |
| Production manifest | `PASS` |
| Request boundary | `PASS` |
| Resolver/client isolation | `PASS` |
| Outcome handling | `PASS` |
| Validation order | `PASS` |
| M08B preserved | `PASS` |
| M08C preserved | `PASS` |
| M08D/CBS preserved | `PASS` |
| Engine unchanged | `PASS` |
| Snapshot evidence | `PASS` |
| Dependency v2 | `PASS` |
| Legacy compatibility | `PASS` |
| API failure safety | `PASS` |
| Forbidden architecture | `PASS` |
| Defects | `none` |

Test and verification evidence:

| Verification | Result |
|---|---|
| Focused PKG-004D | `25 passed` |
| PKG-004B1/B2/C | `100 passed` |
| PKG-001 admission | `19 passed` |
| PKG-002 CBS | `34 passed` |
| PKG-003 dependency manifest | `63 passed` |
| Phase 8/9/10 API/service regressions | `26 passed` |
| Engine/contract/golden | `105 passed` |
| Python compile | `PASS` |
| Alembic | single head `PASS` |
| Git diff check | `PASS` |
| Full backend implementation evidence | `555 passed` |

Frontend tests and the frontend build were not run because no frontend files
changed.

## Accepted Limitations

- The existing M08B caller-supplied parameter wrapper remains.
- No official parameter resolver integration exists.
- No UI support exists for the new request contract.
- No automatic legal derivation of eligibility date exists.
- No historical schema conversion occurred.
- Full M08F is not included.
- This acceptance is not M08 completion.
- This acceptance is not a production-readiness claim.
- This acceptance is not a V1/V2 parity claim.

## Follow-Up Boundary

- UI adaptation, if required later, must be separately scoped.
- M08B official-parameter integration remains separate.
- Broader M08F, M08E, and downstream work remain separate.
- PKG-004D acceptance does not authorize another package.
- The next package remains `NOT_AUTHORIZED`.
