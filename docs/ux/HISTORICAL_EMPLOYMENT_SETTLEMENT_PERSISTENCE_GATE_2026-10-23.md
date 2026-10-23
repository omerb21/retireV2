# Historical employment settlement persistence gate — 2026-10-23

## Verified state
- User confirmed Backend 4/4, Frontend 24/24 and Vite/TypeScript build passed on branch at `a133c24`.
- `EmploymentRecord` currently has no persisted exempt-grant review status. `EmploymentSettlementCreateRequest` accepts `not_reviewed`, `none`, `recorded`, but only `recorded` creates a linked `Grant`. The first two statuses are lost on reload.
- `Grant` has existing nullable `employment_record_id` FK and historical synthetic records already contain two linked exempt amounts for one period. No automatic deletion or matching is acceptable.
- Application-side duplicate checks exist, but do not guarantee uniqueness against concurrent inserts.

## Approved business identity invariants
- One EmploymentRecord is one continuous employment period; rehire under the same legal employer is another record.
- A historical employment period has at most ONE exempt severance grant field, with explicit reviewed/not-reviewed status.
- This is different from multiple settlement components (taxable severance, pension continuity, severance continuity, retained amounts, evidence) that can coexist within the same settlement. Do not model them as extra exempt-grant rows.
- An active current employer has no completed historic termination settlement; future allocations must remain scenario-only.

## Persistence and compatibility proposal
1. Add a separate one-to-one `historical_employment_settlements` table with `employment_record_id` PK/FK, `client_id`, `exempt_grant_status` CHECK (`not_reviewed`, `none`, `recorded`, `requires_reconciliation`), status source and updated audit metadata. Preserve other settlement components separately under this single parent.
2. Backfill safely: one existing linked grant -> candidate `recorded` (still verify evidence); multiple linked grants -> `requires_reconciliation` with all grant rows intact; no linked grant -> `not_reviewed`, NEVER `none` by inference.
3. Persist the explicit `none` choice even without a grant row. The professional interface must expose and edit the persisted choice on reload, rather than merely displaying a list count.
4. Guard schema concurrency with a UNIQUE index on non-null `grants.employment_record_id`, ONLY after detecting and manually reconciling duplicate links; introducing it now would fail on existing records. An alternative is one-to-one canonical settlement grant reference with transactional ownership; both require migration plan and tests.
5. API acceptance: atomic employer + settlement + optional single exempt grant creation; status readback; idempotent update with version guard; reject inconsistent `none` with linked grant; explicit rollback on failed writes; same-client checks and no scenario/canonical product mutation.
6. Do not auto-derive historical tax approvals, 161d offsets, indexed values or original source evidence from a declared amount.
7. Existing user-visible grant creation/linking affordances should not offer duplicate exempt grants; reconciliation UI should allow identification and correction of existing synthetic duplicates without silent removal.

## Gate before schema migration
- Confirm the actual Alembic head(s) from the branch and PostgreSQL-specific triggers/permissions, since migrations are numerous. Do not pick a guessed down_revision.
- Confirm current employer and historical grant POST callers; retain compatibility until new read/write contract and tests are accepted.
- The development branch must not be merged or deployed before migration upgrade/downgrade safety tests, client isolation, and synthetic PostgreSQL end-to-end acceptance.

No schema, API, or tax calculation change is made by this document.
