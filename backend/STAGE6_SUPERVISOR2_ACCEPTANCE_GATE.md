# RETIRE V2 - הוראת מפקח 2: דוח שער אימות (ללא אישור קבלה)

תאריך: 2026-11-05  
Repository: `omerb21/retireV2`  
Branch: `feature/neon-stage6-db-reconnect-20261105`  
Baseline: `8f7371d361d149739adca9f51288235c4354637b`  
PR #7: https://github.com/omerb21/retireV2/pull/7

## הכרעה

**NOT ACCEPTED / BLOCKED**. אין ראיות להרצה בפועל של הרגרסיות החדשות, ולכן אין לאשר Staging, מיזוג או Stage 6. לא בוצע Deploy, לא הופעלו GitHub Actions ולא בוצע שינוי ב-Neon או בנתוני לקוח.

## 1. בדיקת יכולת הרצה אמיתית

סביבת המבצע זמינה ב-Linux עם Python 3.13, Node 22 ו-git, אך ללא checkout של `retireV2`, ללא PowerShell, Docker, PostgreSQL/psql או חבילות PostgreSQL להורדה. פקודת `curl https://api.github.com/repos/omerb21/retireV2` לא הצליחה בגלל כשל DNS. חיבור GitHub מאפשר קריאה וכתיבה לקוד בענף בלבד, ולא הפעלת סביבת הרצה מקומית.

לא ניתן להציג בדיקת Vitest/pytest/PG שהתבצעה ב-GitHub כאילו הורצה במכולת המבצע. בדיקות קודמות של המשתמש, 201 Backend, 385 Frontend ו-9 PostgreSQL, הן **היסטוריות בלבד** ואינן ראיה עבור הקוד הנוכחי.

## 2. פערי בדיקה שהתגלו ונסגרו בקוד הבדיקות

1. סקריפט `run_stage6_pg_integration_win.ps1` כלל בדיקות Stage 6 אך לא את `test_scenario_draft_postgresql.py`. הוספתי אותה לשער, תוך הפעלת `RECOVERY_POSTGRES_TEST=1`. ה-fixture הקיים יוצר מכולות PostgreSQL 16 עצמאיות זמניות דרך Docker, ואינו משתמש ב-`DATABASE_URL` של היישום. משתנה הסביבה מוחזר לערכו הקודם בסיום.
2. בדיקת `test_scenario_pension_election_store_real_postgresql.py` בדקה את מחיקת הבחירה לאחר שינוי, אך לא את השימור עם תפקיד PostgreSQL שאסור לו `UPDATE`. נוספו באותה בדיקה תנאי שימוש ב-ROLE מוגבל עם GRANT מצומצם; דחיית הקצאת יתר ו-Rollback ל-CAS; הוספת החלטה בלתי קשורה ושימור הבחירה; שינוי שם ללא אובדן בחירה; כשל מוזרק בזמן INSERT ובדיקת Rollback מלא; שינוי יתרת מקור בטרנזקציה אחרת במהלך שמירת טיוטה ואימות פסילת התוצאה ברענון; ופסילה בעקבות שינוי סכום. הסכמה וה-ROLE הניסיוניים נמחקים בסיום.
3. הוספתי `run_supervisor2_acceptance_win.ps1` כנקודת כניסה יחידה למחשב המשתמש, הקוראת לשני סקריפטי הבדיקה הקיימים ברצף. היא בודקת מראש את שם הענף, ועוצרת בכשל הראשון. לא מפעילה GitHub Actions, לא ניגשת ל-Neon, אינה פורסת שירות.

לא שונה קוד עסקי או ממשק במסגרת הוראה 2. לא נכתבה מחדש מטריצת הבדיקות מהוראה 1.

## 3. תמונת כיסוי נדרשת

| דרישה | מבחן מסוים | סטטוס הנוכחי |
| --- | --- | --- |
| שימור בחירת קצבה בהוספת המרה | `test_scenario_draft.py::test_unrelated_conversion_preserves_existing_election_without_professional_admission` + PG restricted role | NOT RUN |
| פסילת בחירה בשינוי מהותי | `test_material_change_invalidates_that_pension_election` + PG | NOT RUN |
| שימור בחירה במעבר גרסת שם | `test_metadata_rename_preserves_valid_draft_election_but_not_source_staleness` + PG | NOT RUN |
| CAS ושמירה מתחרה | `test_scenario_draft_postgresql.py::test_postgresql_draft_migration_and_cas` | NOT RUN |
| Rollback אטומי תחת ROLE מוגבל | `test_scenario_pension_election_store_real_postgresql.py` (INSERT failure injection) | NOT RUN |
| איסור UPDATE לבחירת קצבה | PG role privilege assertion + INSERT/DELETE flow | NOT RUN |
| הקצאת יתר בבקשת API ישירה | `test_server_rejects_overallocation_foreign_component_and_foreign_client_atomically` + PG | NOT RUN |
| שינוי יתרת מקור בעת שמירה | PG two-session concurrent source mutation with stale read | NOT RUN |
| הפרדת A1/A2/B1 | `test_a1_a2_b1_api_isolation_on_read_mutation_clone_archive_and_reload` + Stage 6 P1D PG | NOT RUN |
| מעבר לקוח אסינכרוני | `ScenarioDraftPanel.workflow.test.tsx` + `ScenarioStage6Panel.test.tsx` | NOT RUN |
| Frontend full Vitest | `npm test -- --reporter=dot` | NOT RUN |
| Frontend TypeScript/Vite | `npm run build` | NOT RUN |

**תוצאות הרצה בפועל של קוד הוראה 2:** Backend `0 executed / PASS not established`; Frontend `0 executed / PASS not established`; PostgreSQL `0 executed / PASS not established`. אין תוצאת FAIL מוכחת, אך גם אין PASS. כלל הקבלה נשאר חסום.

## 4. רציפות וסטטוס המקור

סקירת קוד (לא הוכחת רגרסיה):
- `replace` משמר רק טיוטת בחירה של אותה החלטה, עם מזהה, מקור, רכיב, סכום, פעולה ומועד שלא השתנו ושמקורם עדיין מתאים לטביעת המקור המקורית.
- `read` מסמן `needs_revalidation` כאשר גרסה, fingerprint או יתרת מקור אינם תקפים או כשהקצאות חורגות במצטבר.
- `current_elections` אינו מציג בחירה שאינה בתוקף מבחינת מקור/יתרות.
- יומן אישורי המקדמים המקצועיים לא עודכן, ולכן אין גרירת אישור לגירסת חלופה חדשה. תוצאת `RESULT_READY` דורשת מחדש עדות אישור מקצועי חתומה וזהות גרסה נוכחית.
- מקור שהשתנה במהלך שמירה נבדק מחדש בקריאה הבאה. המבחן החדש מכוון להוכיח fail-closed אחרי commit, אבל **אינו מוכיח נעילה סריאלית של מקור במהלך כל פעולת השמירה**. סיכון זה נשאר לביקורת המפקח.

## 5. Render - אבחון קריאה בלבד

| פריט | נתון מבוסס |
| --- | --- |
| Service | `srv-dbm5nerbc2fs738d4kqg`, Frankfurt, Docker, Free, autoDeploy=no |
| פריסה כושלת | `dep-dbm8eik9v7es73965q6g`, SHA `95dabc8c3794cf87124e53eb080a86ea215d5833` |
| סטטוס סופי | `update_failed` בתאריך 2026-11-05 13:59:27 UTC |
| Build | `build_ended(succeeded)` 13:41:25 UTC |
| Process | Uvicorn התחיל והודיע `Application startup complete` ו-`0.0.0.0:10000` ב-13:41:49 UTC |
| Runtime | אחרי startup הופיע `asyncio.exceptions.CancelledError` בזמן lifespan; אין הוכחה מי יזם shutdown |
| Failure | `Port scan timeout reached, no open ports detected` 13:56:31 UTC; `Timed Out` 13:59:27 UTC |
| Command | Dockerfile CMD דורש `PORT`, מפעיל `python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:?PORT is required}" --workers 1 --no-proxy-headers` |
| Health | serviceDetails.healthCheckPath ריק; endpoint `/healthz/ready` קיים בקוד אך אינו configured כ-health path ב-Render |
| Code comparison | Dockerfile, main.py ו-requirements.txt עם SHA blob זהה ב-deploy LIVE וב-deploy שנכשל. שני הקבצים היחידים שהשתנו בין commit `82023eb4` לבין `95dabc8` הם `ScenarioDraftPanel.tsx` ו-`ScenarioDraftPanel.workflow.test.tsx` |
| Event evidence | אין אירוע `server_failed` נוסף בחלון שנבדק; אירוע `deploy_ended` מסווג `failed` ללא reason מפורט |
| Last LIVE | `dep-dbm8dj5g1s2s73cdsneg`, SHA `82023eb42ecf5b2ce2cf5ccbcb255741ea5de8e3` |

**שורש מוכח:** Render לא זיהה פורט מאזין בתוך חלון הפריסה. **שורש לא מוכח:** מדוע תהליך Uvicorn החדש איבד זמינות; הלוגים אינם מוכיחים אם השבתת התהליך בוצעה על ידי Render או היישום. אין הצדקה לשינוי תצורה או Redeploy בהוראה 2.

## 6. פקודת הרצה אחת למחשב שבו המאגר קיים

ב-PowerShell מתוך תיקיית `backend` של הענף הנכון:

```powershell
git pull --ff-only
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_supervisor2_acceptance_win.ps1
```

הסקריפט מריץ באופן סדרתי:
- בדיקות Backend ממוקדות (`pytest`).
- כל בדיקות Frontend (`vitest`).
- בניית TypeScript/Vite מלאה.
- PostgreSQL 16 מקומי זמני, כולל role מוגבל, CAS, מקור מתחרה ובדיקות מקצועיות.

**יש לשמר את פלט ה-console המלא.** `SUPERVISOR2_ACCEPTANCE_PASS` הוא תנאי הכרחי, אבל לא מספיק; המפקח חייב לבחון גם את תוצאות כל קבוצת בדיקות ואת החסמים שנותרו. אין מיזוג או פריסה אוטומטיים.

## 7. המלצה

**לדחות קבלה לעת עתה**. תיקוני הכיסוי שמרו על גבולות ההוראה ונשמרו ב-GitHub, אבל מבחני הקבלה המחייבים לא הורצו בפועל. יש לקבל פלט מההרצה המקומית, לטפל רק בכשלי בדיקות ממשיים אם יופיעו, ולהעביר מחדש למפקח. Stage 6 אינו מוכרז כמושלם.
