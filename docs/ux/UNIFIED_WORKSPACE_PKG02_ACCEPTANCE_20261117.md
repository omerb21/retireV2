# RETIRE V2 | Unified Workspace PKG-02 | Isolated Technical Acceptance

**Directive:** 196 (documentation-only closure)  
**Technical acceptance decision:** supervisor accepted PKG-02, CAS and Gate 195 on 2026-11-17.  
**Accepted implementation and test HEAD:** `c2c44bed48267fa56cf8d41f19686cee1bfc810d`  
**Branch:** `fix/pkg02-dependency-cas-20261116`  
**Product baseline:** `2c2eb2ce0269f46310bc6a731d0baad902530b64` (PKG-02 editors), itself based on `c623577b76317009e2262c5b7fc23d1fe19c66b7`.  
**PR #7:** Draft; not merged.

## Accepted scope

PKG-02 integrates four supplementary fact editors into the unified client workspace, reusing the established legacy fact-editing experience:

1. Actual capitalizations: create/read/update/delete with confirmation for deletion.
2. Capital assets: existing and new asset rows, with converted capital destinations remaining read-only in the ordinary facts editor.
3. Recurring incomes: create/read/update, frequency and amount basis preserved.
4. Recurring expenses: create/read/update, frequency preserved.

The implementation preserves the legacy editors and client isolation, prevents accidental abandonment of tested dirty drafts, and refreshes the workspace after successful saves. The subsequent CAS package adds PostgreSQL atomic optimistic concurrency to all four fact tables, requiring an `expected_version` for PUT and for capitalization DELETE. Version conflicts return HTTP 409 with `RECORD_VERSION_CONFLICT`; missing or cross-client records return 404. A version-only metadata change does not invalidate a professional input fingerprint.

**Migration:** `backend/alembic/versions/c194e2f0a816_pkg02_atomic_fact_versions.py`, Alembic revision `c194e2f0a816`, down revision `b2d7e4c9f108`. Adds `version BIGINT NOT NULL DEFAULT 1` with a positive-version check to `actual_capitalizations`, `capital_asset`, `recurring_income`, and `recurring_expense`. Existing synthetic row identities and money fields were preserved. **Migration tested only on a disposable PostgreSQL 16 database; not applied to Railway Staging or Production.**

## Immutable verification evidence

| Stage | Run | Evidence | Result |
|---|---|---|---|
| Directive 192: four editors | [GitHub Actions #43885203707](https://github.com/omerb21/retireV2/actions/runs/43885203707) | PG16 synthetic, 491 frontend tests, TS/Vite, 16 Chromium Playwright | **PASS** |
| Directive 194: CAS plus four-domain fingerprint and saved capital decision | [GitHub Actions #43900264202](https://github.com/omerb21/retireV2/actions/runs/43900264202) | 7 targeted PG16, 50 focused frontend, TypeScript/build, 16 real-DB Chromium | **PASS** |
| Directive 195: four focused risk paths, first pass | [GitHub Actions #43914150080](https://github.com/omerb21/retireV2/actions/runs/43914150080) | 3 targeted PG16 passed; fourth asserted incorrect dependency name although actual API returned changed | **3 PASS; 1 test assertion failure** |
| Directive 195: precise fixation assertion rerun | [GitHub Actions #43914512132](https://github.com/omerb21/retireV2/actions/runs/43914512132) | One targeted PG16 test, saved fixation manifest compared before/after capitalization amount change | **1 PASS** |

Artifact references:
- [192 artifacts](https://github.com/omerb21/retireV2/actions/runs/43885203707/artifacts/14234636144)
- [194 artifacts](https://github.com/omerb21/retireV2/actions/runs/43900264202/artifacts/14239984347)
- [195 final artifacts](https://github.com/omerb21/retireV2/actions/runs/43914512132/artifacts/14249621115)

Do not aggregate the 195 initial failed run into a single green run. The corrected assertion was run separately; the three unaffected PG16 risk tests were not rerun.

## Verification classification and limits

| Verification | Classification | Exact boundary |
|---|---|---|
| Four editors' CRUD, persistence, client isolation, draft handling in tested flows | **PASS** | Existing 192 and affected 194 browser/unit acceptance |
| PG16 synthetic CAS version migration, existing-row data preservation, 409/404/422 and two concurrent writes | **PASS** | Only synthetic PG16, not deployed schema |
| Change to capital asset invalidates directly related saved projection basis; unrelated expense change does not falsely invalidate asset-specific source basis | **PASS** | One saved professional projection decision tested |
| Recurring income identity resolution after an amount/frequency change | **PASS** | Stale resolution rejected through active planning-input API |
| Saved fixation manifest comparison after change to accepted actual capitalization | **PASS** | Comparison returned `changed`, type `capitalization` and path `capitalization:cap-1.amount` |
| Two internal ORM concurrency paths: income resolution vs stale income edit; canonical conversion reversal vs stale capital edit | **PASS** | Tested transaction interleavings and rollback/no silent overwrites, not every possible interleaving |
| New execution of M09 archive-only cashflow via active production endpoint | **NOT APPLICABLE** | M09 endpoints are archive reads, not a current execution producer |
| System-wide professional-currentness enforcement of persisted fixation runs | **NOT VERIFIED** | Separate finding `FIXATION-CURRENTNESS-001`; dependency comparison needs caller-supplied current context |
| Full user-facing live Staging acceptance including migration | **NOT VERIFIED** | No Staging deployment, database change or production credential was used |
| Production readiness / release authorization | **NOT VERIFIED** | Supervisor explicitly accepted only isolated technical gate, not deployment |

## Control requirements

- No production financial, tax, exemption, 161D, scenario formula or canonical conversion engine changes are authorized by this record.
- Historical fixation runs remain historical records; a technical comparison is not a statement of professional validity.
- Preserve old routes until an explicitly authorized retirement plan and user acceptance cover them.
- The visible workspace note still references preflight-only protection (`PKG02-CONCURRENCY-001`) although CAS is implemented on this branch. Treat that wording as a deployment/UX acceptance item; this documentation directive does not authorize a code edit.
- `FIXATION-CURRENTNESS-001` remains a separate unresolved gate, documented in `docs/ux/FIXATION_CURRENTNESS_001_20261117.md`.

**Final acceptance statement:** PKG-02's *isolated technical acceptance* is **PASS and closed** by supervisory decision. Live Staging acceptance, migration rollout, production authorization, merge, deployment and PR #7 state are explicitly outside this acceptance. This record is not a deploy approval.
