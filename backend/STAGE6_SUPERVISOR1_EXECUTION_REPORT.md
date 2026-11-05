# RETIRE V2 - דוח ביצוע להוראת מפקח 1

תאריך: 2026-11-05

Repository: `omerb21/retireV2`  
Branch: `feature/neon-stage6-db-reconnect-20261105`  
Baseline: `dfec1a4a93bd8507050b90a742615c1db3d68b13`  
PR: https://github.com/omerb21/retireV2/pull/7

**החלטה מומלצת: תיקונים הוכנו, אך אין לקבל את הוראת המפקח או לאשר Stage 6 לפני ביצוע הבדיקות החדשות.**

## 1. ממצאים ושורשי תקלות

1. `scenario_draft_service.replace` מחקה את כל רשומות `scenario_draft_pension_elections` בכל החלפה. לכן הוספת המרה עצמאית מחקה בחירה תקפה של החלטה אחרת.
2. שמירת טיוטה הסתמכה על אכיפת יתרה פנויה ב-Frontend. גם אם ה-Backend חסם אומדן מאושר, השרת עדיין קיבל טיוטת הקצאת יתר והחזיר את החלטותיה כ-`unverified` ללא סימון ברור לכל החלטה. מקור של לקוח אחר לא נדחה במפורש.
3. `rename` העלה את גרסת החלופה, אך `current_elections` מציג רק בחירות המתאימות לגרסה הנוכחית, ולכן שינוי שם הסתיר את הבחירה התקפה למרות שהשורה עצמה נשארה במסד.
4. בחירה שנשמרה לפני שינוי המקור עשויה הייתה להמשיך להופיע ב-`current_elections` עד לעדכון הבא, גם כאשר ראיית המקור כבר התיישנה.
5. פריסת Render אחרונה: כשל תפעולי לאחר בנייה מוצלחת, פירוט בסעיף 6.

## 2. קבצים ששונו

| קובץ | שינוי |
| --- | --- |
| `backend/app/services/scenario_draft_service.py` | CAS נשאר בראש פעולת ההחלפה; בדיקת הבעלות והזיהוי של מקור; סכום מצטבר לכל רכיב; שמירת החלטה ללא ריענון אוטומטי של טביעת מקור ישנה; שמירת בחירות קצבה **רק** בהחלטות שלא השתנו ובמקור שעדיין תקף; פסילת אחרות; שימור בחירות תקפות גם בעת שינוי שם; audit של בחירות שנשמרו או נפסלו. |
| `backend/app/services/scenario_pension_election_store_service.py` | שאילתה מחודשת להחלטות ומקורות כדי לא להציג בחירה שהתיישנה או קשורה להקצאת יתר, גם לפני כתיבה נוספת. |
| `backend/tests/test_scenario_draft.py` | תשעה test functions חדשים (אחד מהם פרמטרי עם שלוש חלופות): הוספת המרה ללא מחיקת בחירה קיימת, עריכה והחלפת סכום/מועד/יעד, מקור מיושן, לקוח אחר, הקצאת יתר, CAS, גרסאות, שכפול, Rename, התאמת מענקי DB וטיוטה ישנה. |
| `backend/tests/test_stage6_p1d_postgresql.py` | בדיקות שליליות ב-PostgreSQL אמיתי נגד לקוח אחר והחלטה מחלופה אחרת, גם כשקיימות ראיות מקצועיות סינתטיות לחלופה הנכונה. |
| `backend/STAGE6_SUPERVISOR1_FRONTEND_TEST_COVERAGE_MATRIX.md` | מטריצת שמונה בדיקות Frontend שנמחקו בגרסה הקודמת, דרישת הבטיחות, תחליף קיים ופערים פתוחים. |
| `backend/scripts/run_supervisor1_offline_acceptance_win.ps1` | מסלול בדיקות שמנטרל URL חיצוני ל-DB, מפעיל Backend suite ואחריו כל Frontend Vitest + build, ללא Deploy וללא GitHub Actions. |
| דוח זה | ראיות, סטטוס בדיקות וסיכונים. |

## 3. הכרעות לוגיות והגנות

- הבחנה: שמירת טיוטה אינה אישור מקצועי ואינה ביצוע המרה. חסימה פיננסית ו-Stage 6 נשארות בשרת.
- `replace` משתמש בגרסת חלופה צפויה באמצעות CAS. ניסיון כתיבה עם גרסה ישנה נדחה ב-409.
- רכיב השייך ללקוח אחר, מוצר אחר או קוד רכיב שגוי נדחה ב-422. מקור שאין לו כלל רשומה קנונית יכול להישאר placeholder לתיקון אך מקבל `needs_revalidation`, ולא עובר חישוב.
- סכומים של מספר החלטות על אותו רכיב נסכמים ב-Decimal בשרת. כאשר הסכום חורג מיתרת המקור, כל פעולת השמירה נדחית ב-422. לא נשמרת קבוצת החלטות חלקית.
- הוספת החלטה חדשה אינה מאפסת את בחירת הקצבה של החלטה קודמת שלא השתנתה, אם מקור ההחלטה והבחירה תקפים. לא נשמרת בחירת קצבה של החלטה שמקורה, הסכום, היעד או תאריך ההמרה שלה השתנו.
- טביעת מקור ישנה של החלטה שלא השתנתה **אינה מוחלפת** אוטומטית כשהמקור השתנה. `read` מחשב גם חריגה מצטברת של הקצאות היסטוריות ומסמן `needs_revalidation`.
- בחירות קצבה הן טיוטות, לא מקדם מאושר. הן משוחזרות בגרסה החדשה בעזרת `DELETE` ו-`INSERT` בלבד, מכיוון שלתפקיד האפליקציה אין הרשאת `UPDATE` על הטבלה.
- יומן אישורי המקדמים המקצועיים לא משתנה ולא מעודכן. זהות אישור מקצועי קשורה לגרסת החלופה, ל-manifest ולבחירה הנוכחית; לכן אישור כספי ישן לא מועבר אוטומטית לגרסה החדשה.

## 4. בדיקות - מקור הראיות

| קבוצה | תוצאה | משמעות |
| --- | --- | --- |
| Frontend לפני הוראה זו | **385 PASS**, מתוך 47 קבצים, לפי Build קודם ב-Render | בסיס היסטורי בלבד, לא אישור לקוד הנוכחי. |
| Backend יחידה/API לפני הוראה זו | **201 PASS** לפי הרצה קודמת של המשתמש | בסיס היסטורי בלבד. |
| PostgreSQL Integration לפני הוראה זו | **9 PASS** לפי הרצה קודמת של המשתמש | בסיס היסטורי בלבד. |
| Neon/Alembic Migration | PASS לפי ראיות קודמות | מסד Staging נפרד, לא בדיקת השינויים כעת. |
| Backend regression לאחר התיקון | **NOT RUN** | אין checkout פעיל ובטוח של המאגר בסביבת הביצוע. לא הופעלו Actions/Deploy. |
| PostgreSQL integration לאחר התיקון | **NOT RUN** | נדרש PostgreSQL 16 מקומי מבודד והרצת הקבצים החדשים. |
| Frontend all tests לאחר התיקון | **NOT RUN** | לא נערכה בניית Render כי נדרש אישור מפקח לפריסת Staging. |
| Synthetic positive gross in live Neon | **NOT RUN / BLOCKED** | אין הרשאה ליצור אסמכתה מקצועית או להזין נתוני Staging. |

אין לסווג בדיקה שלא הורצה כ-PASS. ניתן לבצע את הבדיקות האופליין במחשב בעל checkout קיים בסקריפט שצורף לענף, ואת בדיקות PostgreSQL בסקריפט Docker המבודד שכבר קיים: `backend/scripts/run_stage6_pg_integration_win.ps1`.

## 5. הרשאות והפרדת נתונים

- שירות הטיוטות מאתר חלופה באמצעות שילוב `client_id + scenario_id` ב-`_scenario`.
- ב-Backend התווספו בדיקות שלילת קריאה, שינוי, שכפול, ארכיון ו-Rename תחת לקוח שגוי. שדות `source_product_id` ו-`source_component_id` נבדקים מול הרשומות הקנוניות והלקוח.
- ב-Stage 6 P1D נוספו ארבעה מצבי ניסיון להשתמש בזהות לקוח אחר או החלטה מחלופה אחרת, עם ציפייה מפורשת ל-`BLOCKED`, ללא סכום וללא טביעת אישור מקצועי.
- קיימים מראש מבחני UI למעבר לקוח A/B, שלילת תוצאה אסינכרונית מיושנת, חזרת חלופה קיימת, ונעילת Stage 6 כאשר capability לא אומת.
- הסרת כפתורי הרשאות מהמסך אינה מסירה את `validate_session`, `validate_origin`, `validate_csrf`, את סינון ה-DB לפי client ואת שערי המקדם, המקור והחישוב.
- **פער פתוח:** אין הרצה חדשה של מקרי האינטגרציה ו-UI לאחר השינוי. אין אישור אבטחה סופי.

## 6. אבחון Render - קריאה בלבד

Service: `srv-dbm5nerbc2fs738d4kqg`  
Deploy: `dep-dbm8eik9v7es73965q6g`  
Commit: `95dabc8c3794cf87124e53eb080a86ea215d5833`  
Outcome: `update_failed` at **2026-11-05T13:59:27Z**.

Timeline:
- 13:40:27Z - deploy and build started.
- 13:41:25Z - **build succeeded**.
- 13:41:48-49Z - Uvicorn started on `0.0.0.0:10000`, application startup completed; lifespan later emitted `CancelledError` during process teardown.
- 13:56:31Z - Render: **Port scan timeout reached, no open ports detected**.
- 13:59:27Z - Render: **Timed Out** and `deploy_ended(failed)`.

Last confirmed LIVE staging commit: `82023eb42ecf5b2ce2cf5ccbcb255741ea5de8e3`, deploy `dep-dbm8dj5g1s2s73cdsneg`.

**Observed direct cause:** Render could not detect a listening port during its deployment window, even though the new instance briefly started Uvicorn. The lower-level reason for losing the listener is not established by the available logs (resource termination, process restart, platform behavior or health gate are not proven). No configuration change or redeployment performed. Independently probing `/healthz/ready` via the public read-only source was unavailable, so no new claim of health=200.

Production service `srv-dbgr0ik9v7es73b6hs7g` remains on `codex/render-v2-runtime-recovery-01`, auto-deploy off.

## 7. RESULT_READY - positive synthetic acceptance plan

**Distinct prerequisites, in order:**

1. **Client and canonical portfolio:** authorized client identity, scoped pension product, canonical component and amount, valid source version/fingerprint and product statement date. Client profile must have birth date and gender for documentary review.
2. **Scenario decisions:** active draft, allocations within source balances, correct source IDs and version, pension action, and planned effective date. All inputs must share the same current scenario version.
3. **Pension election:** a current `ScenarioDraftPensionElection` for each pension decision; payout start >= decision effective date; survival option, spouse-age difference, payout option, `manual_review_required` as appropriate.
4. **Retirement target and income sources:** payout date must not contradict a global retirement target (if supplied). Recurring incomes require separate current source facts to enter the aggregate cashflow. Gross pension calculation itself does not require an optional comparison target to be marked READY.
5. **Professional factor evidence:** an explicit admissible factor amount, evidence type, documentary reference and authenticated authorized planner approval through Stage 6 professional admission. The server checks source, manifest, election, permission and ruleset fingerprints and the latest immutable admission revision.
6. **PTE gross result:** only after all gates, one trusted execution inside the read-only PostgreSQL snapshot. `RESULT_READY` requires correctly sealed fingerprints and valid gross amount.
7. **Aggregation/comparison:** aggregate only complete compatible pension decisions under the same basis; scenario A/B comparison uses independently verified calculations, never combines alternatives or fabricates net income.

**Deterministic control calculation already encoded in `test_stage6_p1d_postgresql.py`:**

| Decision / value | Synthetic amount | Factor | Monthly gross |
| --- | ---: | ---: | ---: |
| Alternative A - decision 1 | 400.00 ILS | 200 | 2.00 ILS |
| Alternative A - decision 2 | 600.00 ILS | 300 | 2.00 ILS |
| A pension total | | | **4.00 ILS** |
| B pension decisions | 400.00 + 600.00 ILS | 100 / 100 | **10.00 ILS** |
| Shared verified recurring income | | | 1,200.00 ILS |
| A monthly gross cashflow | | | **1,204.00 ILS** |
| B monthly gross cashflow | | | **1,210.00 ILS** |
| B less A monthly | | | **6.00 ILS** |

These small numbers exist to make independent exact-ratio verification obvious; they are not advice, real market factors or approved professional evidence.

**Current Staging blocker:** real client profile/election/target and **professional factor admission** have not been established for the synthetic staging drafts. Nothing was inserted into Neon in this instruction. No `RESULT_READY` from live Staging is claimed. To test a live positive result, the supervisor must separately authorize a synthetic fixture strategy and the actual planner must authorize the professional assumption/reference or provide an admissible document. Without that, remain BLOCKED.

## 8. Risks and recommendation

1. **BLOCKER:** New backend, PostgreSQL and frontend regressions have been added but not executed.
2. **BLOCKER:** Latest Render deployment is `update_failed`, with no root cause proven beyond a port-scan timeout. Deployment authorization is separately required.
3. **BLOCKER:** Positive live Stage 6 result still lacks approved professional factor evidence; no fake admission permitted.
4. **REVIEW:** The legacy placeholders-with-missing-source policy remains: they are labelled `needs_revalidation` and blocked by snapshot/admission. Supervisor should explicitly approve or tighten that policy.
5. **REVIEW:** New election retention logic requires real PostgreSQL restricted-role verification, including DELETE/INSERT grants and DB transaction rollback behavior.
6. **REVIEW:** Existing frontend security-test replacements were mapped, but not all former transient preview behaviors have an exact live-browser E2E equivalent.

**Recommendation: תיקונים מחייבים / NOT ACCEPTED YET.** Do not merge PR #7 or deploy to production. Keep the isolated Staging environment unchanged pending supervisor permission and test results.
