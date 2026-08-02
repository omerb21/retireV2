# PKG-009 Implementation Requirements-to-Tests Matrix

This implementation-only evidence matrix maps the accepted M04 lifecycle
contract without changing package status or the accepted definition.

| Action | Allowed source state | Result state | Server-owned evidence | M03 revalidation | Archived behavior | Concurrency | API tests | UI tests | A→B | A→B→A |
|---|---|---|---|---|---|---|---|---|---|---|
| start | no chain | `under_review` | ID, sequence, actor, timestamp, snapshot, M03 revision, catalogue | required | rejected | unique subject/root and atomic concurrent-start test | `test_concurrent_start_is_atomic`, forgery test | `start mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| proposal creation | `under_review` | `proposed` | refreshed snapshot, exact catalogue/rules, action evidence | required | rejected | stale-leaf and unique-child enforcement | exact preview/proposal and incomplete-accept tests | `proposal mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| unresolved | `under_review` | `unresolved` | server snapshot, rule/conflict evidence, actor/time | required | rejected | stale-leaf and unique-child enforcement | opaque-upload unresolved test | `unresolved mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| accept | `proposed` | `accepted` | copied proposal axes/evidence, server actor/time | required | rejected | stale-leaf and unique-child enforcement | resolved accept and incomplete-accept tests | `accept mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| reject | `proposed` | `rejected` | copied proposal evidence and server provenance | required | rejected | stale-leaf and unique-child enforcement | rejected override test | `reject mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| reopen | `accepted`, `unresolved`, `rejected` | `under_review` | fresh snapshot; no proposed values | required | rejected | stale-leaf and unique-child enforcement | unresolved/reopen and archived tests | `reopen mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| override | `proposed`, `accepted`, `unresolved`, `rejected` | planner-authored `proposed` | old/new values, reason, confirmation, fresh server provenance | required | rejected | stale-leaf and unique-child enforcement | override/accept and rejected-override tests | `override mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| undo | `proposed`, `accepted`, `unresolved`, `rejected` | planner-authored `proposed` | selected history, copied values, reason, confirmation, fresh provenance | required | rejected | stale-leaf and unique-child enforcement | undo-does-not-reactivate test | `undo mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |
| `start_revalidation` | post-archive historical `accepted`, `unresolved`, `rejected` | fresh-snapshot `under_review` | current M03/catalogue context; prior values are historical only | required | allowed only after M01 reopen | stale-leaf and unique-child enforcement | archive/reopen/revalidation test | `start_revalidation mutation …` parameter cases | executable success/rejected/API-error cases | executable success/rejected/API-error cases |

Executable frontend ownership evidence:

- Six `stale target-list` parameter cases execute A→B and A→B→A against
  success, rejected promises, and structured API errors.
- Twenty-four `bundle read` parameter cases execute detail, history,
  matched-rule, and eligibility ownership for both route transitions and all
  three outcomes.
- Three `same-generation target X-to-Y` cases prove target-bundle epochs.
- Three `same-target overlapping preview` cases prove preview epochs.
- Fifty-four action-named mutation cases execute all nine lifecycle actions,
  both route transitions, and all three outcomes. They keep a newer mutation
  pending while the stale request settles, prove stale `finally` cannot clear
  submitting ownership, prove zero stale follow-up reads, and then complete
  the current mutation and refresh.
- `renders complete persisted rule, component, revision, conflict, and
  authority evidence` proves current/history technical provenance rendering.
- Twelve unmount cases cover target list, detail bundle, preview, and mutation
  settlement across success, rejected promises, and structured API errors.
- Twenty-seven preview-to-mutation cases cover all nine lifecycle actions and
  all three older-preview outcomes; stale preview settlement cannot overwrite
  post-mutation authoritative state or launch follow-up reads.
- Three revision-bound preview cases prove that an R1 preview is stale after
  the selected target advances to R2.
- The nine visible `post-mutation new preview succeeds with action-specific
  payload` parameter cases exercise `start`, `proposal`, `unresolved`,
  `accept`, `reject`, `reopen`, `override`, `undo`, and `start_revalidation`.
  Each case holds P1 and the real action-specific mutation independently,
  verifies its exact payload and five-call authoritative refresh, then proves
  a separately controlled P2 applies normally while late P1 remains stale.

Backend integrity evidence:

- `test_pkg009_m04_classification.py` covers lifecycle, exact rules,
  immutability, caller forgery, client isolation, archive/revalidation,
  predecessor invalidation, raw-SQL corruption, and fail-closed M05
  eligibility.
- Instance, bulk, alias, synchronize-session, subject/cascade, controlled
  archive-generation, and unrelated-model DML tests cover ORM immutability.
- The ten-case `test_aggregate_corruption_matrix_fails_closed` recomputes
  digests after controlled corruption and proves semantic aggregate checks;
  positive derivation and pre-acceptance rejection tests cover the valid path.
- The twelve-case `test_raw_snapshot_component_multiplicity_fails_closed`
  matrix validates raw snapshot identities before normalization, including
  identical/conflicting duplicates, malformed identities and entries, and
  count/identity mismatches. Three API-level positive controls prove valid
  one-to-one pension, capital, and mixed component snapshots remain eligible.
- `test_pkg009_migration.py` covers the single head, additive SQLite
  upgrade/downgrade/re-upgrade, empty/no-backfill state, bounded downgrade, and
  PostgreSQL offline DDL generation.
