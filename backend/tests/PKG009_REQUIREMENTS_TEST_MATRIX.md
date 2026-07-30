# PKG-009 Implementation Requirements-to-Tests Matrix

This implementation-only evidence matrix maps the accepted M04 lifecycle
contract without changing package status or the accepted definition.

| Action | Allowed source state | Result state | Server-owned evidence | M03 revalidation | Archived behavior | Concurrency | API tests | UI tests | A→B | A→B→A |
|---|---|---|---|---|---|---|---|---|---|---|
| start | no chain | `under_review` | ID, sequence, actor, timestamp, snapshot, M03 revision, catalogue | required | rejected | unique subject/root and atomic concurrent-start test | `test_concurrent_start_is_atomic`, forgery test | explicit-start workflow and API intent matrix | shared generation guard | shared generation guard |
| proposal creation | `under_review` | `proposed` | refreshed snapshot, exact catalogue/rules, action evidence | required | rejected | stale-leaf and unique-child enforcement | exact preview/proposal and incomplete-accept tests | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| unresolved | `under_review` | `unresolved` | server snapshot, rule/conflict evidence, actor/time | required | rejected | stale-leaf and unique-child enforcement | opaque-upload unresolved test | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| accept | `proposed` | `accepted` | copied proposal axes/evidence, server actor/time | required | rejected | stale-leaf and unique-child enforcement | resolved accept and incomplete-accept tests | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| reject | `proposed` | `rejected` | copied proposal evidence and server provenance | required | rejected | stale-leaf and unique-child enforcement | rejected override test | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| reopen | `accepted`, `unresolved`, `rejected` | `under_review` | fresh snapshot; no proposed values | required | rejected | stale-leaf and unique-child enforcement | unresolved/reopen and archived tests | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| override | `proposed`, `accepted`, `unresolved`, `rejected` | planner-authored `proposed` | old/new values, reason, confirmation, fresh server provenance | required | rejected | stale-leaf and unique-child enforcement | override/accept and rejected-override tests | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| undo | `proposed`, `accepted`, `unresolved`, `rejected` | planner-authored `proposed` | selected history, copied values, reason, confirmation, fresh provenance | required | rejected | stale-leaf and unique-child enforcement | undo-does-not-reactivate test | action-state matrix and API intent matrix | shared mutation guard | shared mutation guard |
| `start_revalidation` | post-archive historical `accepted`, `unresolved`, `rejected` | fresh-snapshot `under_review` | current M03/catalogue context; prior values are historical only | required | allowed only after M01 reopen | stale-leaf and unique-child enforcement | archive/reopen/revalidation test | revalidation-only UI test and API intent matrix | shared mutation guard | shared mutation guard |

Shared frontend evidence:

- `M04ClassificationScreen` captures `clientId` plus route-context generation
  for candidate, target, history, component, matched-rule, preview, and
  eligibility reads.
- All nine mutations use the same guarded mutation path. A stale mutation
  exits before starting any follow-up refresh.
- Deterministic controlled-promise tests cover stale success, rejection,
  structured API error, stale `finally`, A→B, A→B→A, a new authoritative A
  request, and zero stale mutation refreshes.

Backend integrity evidence:

- `test_pkg009_m04_classification.py` covers lifecycle, exact rules,
  immutability, caller forgery, client isolation, archive/revalidation,
  predecessor invalidation, raw-SQL corruption, and fail-closed M05
  eligibility.
- `test_pkg009_migration.py` covers the single head, additive SQLite
  upgrade/downgrade/re-upgrade, empty/no-backfill state, bounded downgrade, and
  PostgreSQL offline DDL generation.
