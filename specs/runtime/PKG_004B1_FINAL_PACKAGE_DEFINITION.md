# PKG_004B1_FINAL_PACKAGE_DEFINITION.md

## 1. Executive Definition Summary

`PKG-004B1` מוגדרת כחבילת תשתית צרה לשמירת פרופיל ראיות M07 והערכת שלמות טכנית של הראיות.

החבילה תשמור:

* עובדות מקור המקושרות ללקוח.
* מקורות ופרטי provenance.
* מצבי איסוף ואימות.
* חוסרים, אי-בהירויות וסתירות.
* הצהרות מתכנן כרשומות נפרדות.
* אזהרות טכניות.
* תוצאות assessment טכניות.
* גרסאות, fingerprints והיסטוריית revisions.

החבילה לא תיצור:

* `qualified`.
* `warning_reviewed`.
* החלטת קבלה מקצועית.
* `accepted_for_use`.
* סמכות M07 נוכחית.
* selector מקצועי או downstream eligibility.
* אינטגרציה אוטומטית ל-M08.

הארכיטקטורה המינימלית המומלצת כוללת רשומת revision ראשית ושלוש קבוצות child records: עובדות, הצהרות וממצאי assessment. בעת finalization יישמר גם canonical payload חתום ב-fingerprint.

לא נמצאה החלטת עומר נוספת הנדרשת להגדרת B1 בלבד. השאלות המקצועיות נשארות מחוץ לחבילה.

הדוח אינו מאשר implementation.

## 2. Repository Safety Check

| בדיקה                        | ראיה                                       | תוצאה |
| ---------------------------- | ------------------------------------------ | ----- |
| `origin/master`              | `120b59a247e820de89b72038775038b8bd0d8eb3` | PASS  |
| Commit                       | `docs: accept PKG-004A`                    | PASS  |
| Source of truth              | קיים ב-Repository                          | PASS  |
| PKG-001 record               | קיים                                       | PASS  |
| PKG-002 record               | קיים                                       | PASS  |
| PKG-003 record               | קיים                                       | PASS  |
| PKG-004A record              | קיים ומסומן `ACCEPTED_WITH_FOLLOW_UP`      | PASS  |
| Alembic graph                | 17 revisions, head יחיד `a8e4f2c6d901`     | PASS  |
| M08E                         | נשאר מוחרג מהשלב הראשון                    | PASS  |
| Full M08F                    | נשאר לא שלם ומחוץ לחבילה                   | PASS  |
| M09-M14                      | נשארים `BLOCKED_FOR_LOGIC_DETAIL`          | PASS  |
| 02M                          | נשאר `FROZEN`                              | PASS  |
| Next package                 | `NOT_AUTHORIZED`                           | PASS  |
| Implementation authorization | `NO`                                       | PASS  |
| Tracked changes              | לא נוצרו                                   | PASS  |

ה-head של Alembic אומת באמצעות ניתוח סטטי של כל `revision` ו-`down_revision`. פקודת `alembic` עצמה אינה מותקנת בסביבת הבדיקה.

## 3. Package Identity and Status

| שדה                       | ערך                                                                 |
| ------------------------- | ------------------------------------------------------------------- |
| Package                   | `PKG-004B1 - M07 Source Profile and Assessment Evidence Foundation` |
| Package type              | Evidence persistence foundation                                     |
| Client scope              | Client-specific                                                     |
| Authority classification  | `EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY`                          |
| Base                      | `120b59a`                                                           |
| Planned migration parent  | `a8e4f2c6d901`                                                      |
| Definition status         | Ready for a separate implementation-authorization decision          |
| Implementation authorized | NO                                                                  |
| PKG-004B2                 | מחוץ ל-scope                                                        |
| Production readiness      | לא נטענת                                                            |
| M07 completion            | לא נטענת                                                            |

## 4. Professional and Technical Boundary

| שכבה                                     | B1       |
| ---------------------------------------- | -------- |
| Source fact                              | INCLUDED |
| Source reference                         | INCLUDED |
| Collection state                         | INCLUDED |
| Verification state                       | INCLUDED |
| Planner assertion                        | INCLUDED |
| Missing, unresolved or conflict evidence | INCLUDED |
| Technical assessment outcome             | INCLUDED |
| Professional qualification decision      | EXCLUDED |
| Warning review or acceptance             | EXCLUDED |
| Accepted-for-use                         | EXCLUDED |
| Current M07 authority                    | EXCLUDED |
| Downstream eligibility                   | EXCLUDED |
| Professional stale status                | EXCLUDED |

כל תוצאה של B1 מתארת רק את מצב הראיות שנשמרו. היא אינה קביעה מקצועית לגבי זכאות, נכונות חיצונית או אפשרות להשתמש במידע לחישוב.

## 5. Source-of-Truth Contract

החוזה נגזר משורת M07, מ-Q-013, מ-Q-014 ומחוזי PKG-001.

עקרונות קבועים:

* M07 שומר פרופיל מס פרישה מקושר למקורות.
* M07 אינו מבצע חישוב מס, קיבוע זכויות, פטור, 161D, המלצה או תרחיש.
* כל עובדה מהותית צריכה provenance ומצב אימות.
* מצב חסר, לא נאסף, לא ידוע, לא פתור או לא מאומת נשמר במפורש.
* מקור שנדחה או הוחלף נשמר היסטורית.
* conflict אינו מוכרע אוטומטית.
* הצהרת מתכנן אינה משנה את עובדת המקור.
* אין הנחת ערך שקטה.
* M07 מחזיק שנת מס או אירוע ויכול לזהות parameter set שנדרש מאוחר יותר.
* ערכי parameter set עצמם אינם בבעלות M07.
* qualification, warning review ושימוש downstream אינם חלק מ-B1.

## 6. Included Evidence Fields

| Field group                             | Classification                      | הערה                                              |
| --------------------------------------- | ----------------------------------- | ------------------------------------------------- |
| Stable M07 profile ID                   | INCLUDED_REQUIRED                   | מזהה לוגי משותף ל-revisions                       |
| Evidence revision ID                    | INCLUDED_REQUIRED                   | מזהה ייחודי לכל revision                          |
| Client ID                               | INCLUDED_REQUIRED                   | FK והיקף isolation                                |
| Revision number                         | INCLUDED_REQUIRED                   | ייחודי בתוך profile                               |
| Predecessor revision                    | INCLUDED_CONDITIONAL                | כאשר מדובר בתיקון או revision חדש                 |
| Tax or event year                       | INCLUDED_REQUIRED                   | שנת הקשר, ללא חישוב מס                            |
| Relevant event reference                | INCLUDED_CONDITIONAL                | רק כאשר קיים מקור או אירוע מפורש                  |
| Retirement age/date or eligibility fact | INCLUDED_REQUIRED                   | נשמר כעובדה מסומנת במקור, ללא קביעת סמכות גלובלית |
| Pension commencement fact               | INCLUDED_CONDITIONAL                | כאשר applicable או known                          |
| Employment status                       | INCLUDED_REQUIRED                   | לפי vocabulary המאושר                             |
| Grant/severance collection state        | INCLUDED_REQUIRED                   | ללא קביעת שימוש בחישוב                            |
| Actual-capitalization collection state  | INCLUDED_REQUIRED                   | ללא accepted-for-use                              |
| Grant/severance evidence items          | INCLUDED_CONDITIONAL                | כאשר recorded                                     |
| Actual-capitalization evidence items    | INCLUDED_CONDITIONAL                | כאשר recorded                                     |
| Prior-withdrawal status                 | INCLUDED_CONDITIONAL                | נשמר בלבד                                         |
| Form 161 status/evidence                | INCLUDED_CONDITIONAL                | נוכחות מסמך אינה מוכיחה עובדה מתוכו               |
| Form 161D status/evidence               | INCLUDED_CONDITIONAL                | מסמך היסטורי בלבד, לא output חדש                  |
| Existing or expected pension facts      | INCLUDED_CONDITIONAL                | עם source ו-verification                          |
| M05/M06 references                      | INCLUDED_CONDITIONAL                | רק אם records מתאימים קיימים                      |
| Source provenance                       | INCLUDED_REQUIRED לכל material fact | אין material fact ללא מקור או assertion basis     |
| Verification state                      | INCLUDED_REQUIRED לכל material fact | נשמר בנפרד מ-collection                           |
| Missing input records                   | INCLUDED_CONDITIONAL                | structured findings                               |
| Unresolved input records                | INCLUDED_CONDITIONAL                | structured findings                               |
| Conflict records                        | INCLUDED_CONDITIONAL                | ללא source ranking                                |
| Planner assertions                      | INCLUDED_CONDITIONAL                | additive ונפרד מעובדות                            |
| Technical warnings                      | INCLUDED_CONDITIONAL                | versioned and fingerprinted                       |
| Technical rule outcomes                 | INCLUDED_REQUIRED                   | תוצאה טכנית בלבד                                  |
| Annual parameter-set reference          | INCLUDED_CONDITIONAL                | ID ו-fingerprint בלבד                             |
| Schema version                          | INCLUDED_REQUIRED                   | contract version                                  |
| Rule version                            | INCLUDED_REQUIRED                   | assessment rule identity                          |
| Assessment timestamp                    | INCLUDED_REQUIRED                   | מועד assessment טכני                              |
| Canonical evidence payload              | INCLUDED_REQUIRED בעת finalization  | נוצר בצד השרת                                     |
| Evidence fingerprint                    | INCLUDED_REQUIRED בעת finalization  | deterministic                                     |
| Planner notes                           | INCLUDED_OPTIONAL                   | אינן decision authority                           |
| Source metadata                         | INCLUDED_OPTIONAL                   | JSON מובנה ומוגבל                                 |

## 7. Excluded Decision Fields

| Field or concept                         | Classification                 | סיבה                                        |
| ---------------------------------------- | ------------------------------ | ------------------------------------------- |
| `qualified`                              | EXCLUDED_PROFESSIONAL_DECISION | שייך לחבילת החלטה עתידית                    |
| `warning_reviewed`                       | EXCLUDED_PROFESSIONAL_DECISION | B1 שומר warning בלבד                        |
| Warning accepted                         | EXCLUDED_PROFESSIONAL_DECISION | אין קבלת אזהרה ב-B1                         |
| Professional review outcome              | EXCLUDED_PROFESSIONAL_DECISION | אינו assessment טכני                        |
| `accepted_for_use`                       | EXCLUDED_PROFESSIONAL_DECISION | אינו מצב ראיות                              |
| Qualification actor                      | EXCLUDED_PROFESSIONAL_DECISION | אין qualification                           |
| Review actor                             | EXCLUDED_PROFESSIONAL_DECISION | אין warning review                          |
| Current authority                        | OUT_OF_SCOPE                   | אין selector סמכותי                         |
| Downstream eligibility                   | OUT_OF_SCOPE                   | Full M08F אינו נפתח                         |
| Professional stale status                | OUT_OF_SCOPE                   | שינוי מקור נשמר טכנית בלבד                  |
| Authoritative eligibility-date inference | DEFERRED_MISSING_SOURCE        | ניתן לשמור sourced fact, לא לבחור authority |
| Automatic prior-fixation conclusion      | DEFERRED_MISSING_SOURCE        | אין authoritative runtime source            |
| Tax or fixation result                   | OUT_OF_SCOPE                   | אין calculation ב-M07                       |
| Formal 161D result                       | OUT_OF_SCOPE                   | M08E מוחרג                                  |

## 8. Proposed Persistence Model

הארכיטקטורה הצרה המומלצת היא ארבעה records, ללא table נפרד נוסף רק לצורך normalization תאורטי.

| Proposed record           | Purpose                                                                    | Required fields                                                                                                                                  | Mutability                                                 | Authority meaning                                      |
| ------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------ |
| `m07_evidence_revisions`  | זהות, scope, lifecycle, versions, assessment summary ו-canonical snapshot  | Revision ID, profile ID, client ID, revision number, tax year, schema/rule version, status, timestamps, outcomes, canonical payload, fingerprint | Draft editable דרך services; finalized immutable           | `EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY`             |
| `m07_fact_evidence`       | עובדות, collection, verification ו-source provenance                       | Fact ID, revision/client IDs, field code, structured value, collection state, verification state, source fields, evidence fingerprint            | Draft service operations בלבד; immutable לאחר finalization | `EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY`             |
| `m07_planner_assertions`  | הצהרות מתכנן additive ונפרדות מעובדות                                      | Assertion ID, revision/client IDs, field code, asserted value, basis, actor, timestamp, optional predecessor assertion                           | Append-oriented; immutable לאחר finalization               | `ASSERTION_EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY`   |
| `m07_assessment_findings` | חוסרים, unresolved, conflicts, rejected evidence, warnings ו-rule outcomes | Finding ID, kind, code, field references, description, source/fact refs, rule version, assessment time, technical effect, fingerprint            | Rebuilt only while draft; immutable לאחר finalization      | `TECHNICAL_ASSESSMENT_ONLY_NOT_PROFESSIONAL_AUTHORITY` |

Warning נשמר כ-finding subtype עם stable ID ו-fingerprint. אין צורך ב-warning table נוסף בשלב זה.

ה-canonical payload נבנה בצד השרת מכל child records בעת finalization. הוא אינו DTO שה-caller רשאי למסור כרשומה מוגמרת.

## 9. Client and Revision Identity

### Identity contract

* `m07_profile_id`: מזהה לוגי יציב של evidence profile.
* `m07_evidence_revision_id`: מזהה ייחודי לכל revision.
* `client_id`: חובה בכל revision ובכל child record.
* `revision_number`: מספר חיובי וייחודי בתוך `(client_id, m07_profile_id)`.
* `predecessor_revision_id`: optional self-reference.
* `superseded_by_revision_id`: נרשם רק במהלך atomic supersession.
* `tax_event_year`: חובה.
* `scope_event_type` ו-`scope_event_id`: optional, כאשר קיים אירוע persisted.
* `assessment_timestamp`: חובה לאחר technical assessment.
* `schema_version`: חובה.
* `rule_version`: חובה.
* `source_snapshot_fingerprint`: חובה בעת finalization.

### Retirement or eligibility date

B1 רשאית לשמור:

* field type, למשל `retirement_date_claim`, `retirement_age_claim` או `eligibility_date_claim`;
* value;
* source;
* collection state;
* verification state;
* basis;
* recorded actor and time.

השם הסופי של field code הוא החלטה טכנית. עצם הערך אינו הופך ל-authoritative eligibility date. B1 אינה בוחרת בין מקורות מתחרים ואינה מסיקה את התאריך ממועד לידה.

## 10. Collection and Verification Vocabulary

### M07 collection states

| Persisted M07 state | משמעות טכנית                                                 |
| ------------------- | ------------------------------------------------------------ |
| `recorded`          | קיים evidence item אחד לפחות. אין משמעות של אימות או קבלה    |
| `confirmed_none`    | נרשמה הצהרה מפורשת שאין פריטים, עם source או assertion basis |
| `unknown`           | לא ידוע אם קיימת עובדה או רשומה                              |
| `not_collected`     | פעולת האיסוף לא בוצעה או לא הושלמה                           |
| `unresolved`        | נאסף מידע אך לא ניתן לייצג עובדה יחידה ללא הכרעה             |
| `not_applicable`    | נרשמה אי-תחולה עם basis. אין בכך קביעת eligibility           |

### Mapping from existing M08 collection vocabulary

| Existing M08     | Persisted M07    | Mapping status                                         |
| ---------------- | ---------------- | ------------------------------------------------------ |
| `unknown`        | `unknown`        | Exact label, אך אין backfill                           |
| `not_collected`  | `not_collected`  | Exact label, אך אין backfill                           |
| `confirmed_none` | `confirmed_none` | דורש ב-B1 basis שאינו קיים בהכרח ב-M08                 |
| `items_recorded` | `recorded`       | Explicit transport mapping בלבד; אינו מוכיח provenance |
| אין מקביל        | `unresolved`     | נשמר רק ב-M07                                          |
| אין מקביל        | `not_applicable` | נשמר רק ב-M07                                          |

### M07 verification states

| Persisted M07 state | משמעות טכנית                                  |
| ------------------- | --------------------------------------------- |
| `unverified`        | העובדה לא אומתה                               |
| `partly_verified`   | רק חלק מהראיות או רכיבי העובדה אומתו          |
| `verified`          | נרשמה פעולת אימות מלאה לפי evidence contract  |
| `planner_asserted`  | הערך מגיע מהצהרת מתכנן מקושרת, לא מעובדת מקור |
| `source_conflict`   | קיימים מקורות סותרים ללא בחירה                |
| `rejected`          | evidence item נדחה אך נשמר                    |
| `superseded`        | evidence item הוחלף אך נשמר                   |

### Mapping from generic retirement-fact vocabulary

| Existing generic value         | M07 mapping                              | החלטה                                                      |
| ------------------------------ | ---------------------------------------- | ---------------------------------------------------------- |
| `verified`                     | `verified`                               | ניתן למפות רק בפעולת ingestion מפורשת                      |
| `partially verified`           | `partly_verified`                        | ניתן למפות במפורש                                          |
| `collected - not yet reviewed` | `unverified`                             | מיפוי מפורש בלבד                                           |
| `reviewed`                     | אין mapping מדויק                        | Review אינו בהכרח verification                             |
| `verification not applicable`  | אין mapping אוטומטי                      | ניתן לשקול `not_applicable` כ-collection state רק עם basis |
| Generic `source_status` values | אין mapping ל-collection או verification | נשמרים כ-source metadata                                   |

לא מתבצע backfill או mapping שקט של records קיימים.

## 11. Source Provenance

כל material fact צריך לשמור לכל הפחות:

| Field                       | Requirement                                                  |
| --------------------------- | ------------------------------------------------------------ |
| `source_type`               | חובה, controlled technical category                          |
| `source_record_type`        | חובה אם המקור הוא runtime record                             |
| `source_record_id`          | חובה אם קיים runtime source                                  |
| `source_document_reference` | conditional                                                  |
| `source_date`               | conditional                                                  |
| `source_excerpt`            | optional, בכפוף לפרטיות ונפח                                 |
| `structured_value`          | חובה כאשר collection state הוא `recorded`                    |
| `source_metadata`           | optional structured JSON                                     |
| `recorded_at`               | חובה                                                         |
| `recorded_by`               | חובה דרך service/admin boundary                              |
| `verification_state`        | חובה                                                         |
| `verified_at`               | חובה עבור `verified` או `partly_verified`                    |
| `verified_by`               | חובה עבור `verified` או `partly_verified`                    |
| `evidence_fingerprint`      | חובה לאחר finalization                                       |
| `basis`                     | חובה עבור `confirmed_none`, `not_applicable` ו-asserted fact |

Ordinary client payload אינו רשאי לקבוע actor מאומת. עד שתהיה תשתית authentication מתאימה:

* actor מתקבל רק כ-administrative/service input.
* ה-service חייב להבדיל בין caller payload לבין administrative actor context.
* ה-record מתעד מי הוזן כ-actor, אך אינו טוען שהמערכת אימתה רישיון, תפקיד או הרשאה מקצועית.

## 12. Planner Assertions

Planner assertion היא record נפרד ואינה סוג של source fact.

שדות מינימליים:

* assertion ID;
* revision ID;
* client ID;
* affected field code;
* asserted structured value;
* basis or reason;
* source note;
* actor;
* timestamp;
* optional predecessor assertion;
* assertion fingerprint.

כללים:

* Assertion היא additive.
* שינוי assertion יוצר assertion חדש.
* Assertion אינה מוחקת או מחליפה source fact.
* Assertion אינה בוחרת מקור מתוך conflict.
* `planner_asserted` verification state חייב להפנות ל-assertion record.
* Assertion אינה יוצרת `qualified`, acceptance או accepted-for-use.
* לאחר finalization היא immutable.
* actor מגיע מ-service boundary ולא משדה actor בתוך ordinary client DTO.

Child table נפרד מוצדק, מפני שהוא מאפשר audit, immutability והפרדה אמיתית מעובדות המקור.

## 13. Missing, Unresolved and Conflict Evidence

`m07_assessment_findings` ישמור את המצבים הבאים:

| Finding kind             | דרישת evidence                                        |
| ------------------------ | ----------------------------------------------------- |
| `missing_required_field` | Field identity, rule code, description, assessed time |
| `not_collected`          | Field identity, collection status, assessment context |
| `unknown`                | Field identity והסבר טכני                             |
| `unresolved`             | Field identity, source/fact references והסבר          |
| `source_conflict`        | כל source/fact references הרלוונטיים, ללא דירוג       |
| `rejected_evidence`      | Evidence ID, reason, timestamp                        |
| `confirmed_none`         | Field identity, source או assertion basis             |
| `not_applicable`         | Field identity ו-basis                                |
| `incompatible_evidence`  | Schema/rule incompatibility evidence                  |

כל finding כולל:

* stable finding ID;
* revision/client IDs;
* kind;
* code/category;
* field identities;
* description;
* relevant fact, assertion and source references;
* rule version;
* assessment timestamp;
* technical blocking effect כאשר קבוע ב-Q-014;
* fingerprint.

אין `stale`, eligibility או professional rejection outcome.

## 14. Warning Evidence

Warning ב-B1 הוא evidence טכני בלבד.

שדות:

* stable warning ID;
* warning code;
* warning message;
* rule version;
* affected field codes;
* affected fact/assertion IDs;
* evidence revision ID;
* assessment timestamp;
* fixed technical blocking indicator, אם נגזר ישירות מ-Q-014;
* deterministic warning fingerprint.

Fingerprint מחושב לפחות מ:

* code;
* message;
* rule version;
* sorted affected field identities;
* sorted affected evidence identities;
* revision identity.

לא יישמרו ב-B1:

* review status;
* reviewed by;
* review timestamp;
* acceptance reason;
* permission to proceed;
* qualification result.

כך חבילה מאוחרת תוכל, אם תאושר, להתייחס ל-warning ID ול-fingerprint מדויקים במקום לטקסט mutable.

## 15. Technical Assessment Outcomes

B1 רשאית לשמור את ה-outcomes הבאים:

| Outcome                | משמעות                                                                        |
| ---------------------- | ----------------------------------------------------------------------------- |
| `evidence_complete`    | כל required evidence נמצא ואין blocker טכני קבוע. אין משמעות של qualification |
| `evidence_incomplete`  | חסר required evidence או שהוא unknown, not collected או unverified            |
| `evidence_conflicting` | קיים unresolved או source conflict מהותי                                      |
| `technical_blocked`    | קיים blocker טכני לפי Q-014                                                   |
| `warning_present`      | קיימת אזהרה טכנית אחת לפחות                                                   |

ה-outcome נשמר כקבוצה versioned, לא כהחלטה מקצועית יחידה.

כללים:

* `evidence_complete` אינו יכול להופיע יחד עם `evidence_incomplete`, `evidence_conflicting` או `technical_blocked`.
* `warning_present` יכול להופיע לצד outcome אחר.
* Missing schema version, rule version או required field גורם fail-closed.
* Source conflict אינו נפתר אוטומטית.
* `finalized` revision יכול להיות incomplete או blocked. Finalization פירושו sealed evidence בלבד.
* אין שימוש במילים `qualified`, `accepted`, `eligible` או `current_authority`.

## 16. Lifecycle and Immutability

### Technical lifecycle

| State        | משמעות                                                        |
| ------------ | ------------------------------------------------------------- |
| `draft`      | ניתן לבנייה דרך narrow service commands                       |
| `finalized`  | הראיות וה-assessment ננעלו עם canonical payload ו-fingerprint |
| `superseded` | revision finalized הוחלף ב-revision finalized אחר, ללא מחיקה  |
| `abandoned`  | draft נסגר ללא finalization וללא משמעות מקצועית               |

### Transition rules

* `draft -> finalized`
* `draft -> abandoned`
* `finalized -> superseded`, רק יחד עם successor finalized
* אין חזרה מ-finalized ל-draft.
* אין mutation רגיל של finalized, superseded או abandoned.
* Correction נעשית ב-revision חדש.
* Supersession מתבצע בפעולת service אטומית.
* אין transition ל-qualified, warning_reviewed או accepted.
* אין delete רגיל של revision עם evidence.
* אין delete של finalized, superseded או abandoned records.
* Child records כפופים למצב ה-parent.
* canonical payload ו-fingerprint מחושבים מחדש רק כל עוד ה-revision הוא draft.

נדרשת ORM mutation protection בדומה ל-PKG-004A. Raw SQL או database-admin bypass נשאר limitation תפעולי ואינו trust mechanism אפליקטיבי.

## 17. Selection Boundary

PKG-004B1 לא תחשוף current authoritative selector.

מותר:

* get revision by client and revision ID;
* list revisions for a client;
* list revisions by profile ID;
* filter by tax year;
* filter by technical lifecycle status;
* filter by explicit event reference;
* return chronological ordering;
* expose finalized revisions.

לא מומלץ endpoint בשם `latest`. אם נדרש שימוש פנימי, עליו להיקרא ולהיות מתועד כ-`latest_chronological_evidence_revision`.

Chronological latest:

* אינו qualified;
* אינו accepted;
* אינו authoritative;
* אינו selector ל-M08;
* אינו עוקף ambiguous results;
* אינו מאפשר latest-wins authority.

Query שמצופה להחזיר record יחיד ומחזיר מספר candidates תיכשל ב-`ambiguous_revision_query`, ללא בחירה אוטומטית.

## 18. Service and API Boundary

### Included service operations

* `create_draft_evidence_revision`
* `record_or_update_draft_fact_evidence`
* `append_planner_assertion`
* `record_assessment_finding`
* `run_technical_evidence_assessment`
* `finalize_evidence_revision`
* `create_successor_revision`
* `supersede_evidence_revision`
* `get_client_evidence_revision`
* `list_client_evidence_revisions`

השמות הסופיים הם החלטת implementation טכנית.

### HTTP boundary

מומלץ:

* לכלול לכל היותר client-scoped read endpoints ל-list ו-detail.
* לא לכלול write HTTP API ב-B1.
* לא להמציא production administrative authentication.
* לבצע write operations דרך service layer בלבד.
* read DTO חייב לכלול classification מפורש: `EVIDENCE_ONLY_NOT_PROFESSIONAL_AUTHORITY`.
* אין endpoint בשם `current`, `qualified`, `accepted` או `eligible`.

Ordinary caller אינו יכול לשלוח DTO שלם ולבקש לשמור אותו כ-finalized profile.

## 19. Non-Forgeable Evidence Boundary

הגבול הנדרש:

1. השרת פותר `client_id` independently מה-command context.
2. כל source reference נבדק מול אותו client.
3. ה-command מציין פעולה צרה, לא complete official profile.
4. actor מגיע מ-service context נפרד.
5. lifecycle transition מבוצע רק בשירות ייעודי.
6. canonical payload ו-fingerprint נוצרים בצד השרת.
7. finalization נועלת parent ו-child records.
8. supersession אטומי ומקושר ל-successor.
9. DTO שהוחזר לקריאה אינו קביל כ-write authority command.
10. equality ל-snapshot היסטורי אינה מעניקה שום status.

אסור להוסיף:

* `trusted=True`;
* trust token;
* provenance token;
* authority wrapper;
* importable trusted factory;
* caller-created finalized DTO;
* caller-controlled lifecycle marker;
* arbitrary `official` provenance string;
* direct public status mutation.

Caller-supplied `qualified` נשאר מחוץ ל-B1 ואינו יוצר record מקצועי.

## 20. Relationship to Existing M07EntryContext

`M07EntryContext` נשאר downstream transport and admission envelope הקיים.

B1:

* אינה מחליפה אותו.
* אינה מוסיפה לו repository authority.
* אינה מייצרת `state="qualified"`.
* אינה מייצרת `state="warning_reviewed"`.
* אינה ממלאת review reason, reviewer או review timestamp.
* אינה משנה את התנהגות PKG-001.
* אינה משלבת repository lookup ב-fixation admission.
* אינה משדרגת caller-supplied context.
* אינה מבצעת backfill.

חבילת integration עתידית תצטרך, לאחר החלטות ואישור נפרדים, למפות:

* evidence profile/revision identity;
* client binding;
* qualification decision חיצונית ל-B1;
* exact warning set;
* review evidence חיצונית ל-B1;
* qualification trace/version.

אין הגדרה נוספת של חבילה זו במסגרת B1.

## 21. Relationship to PKG-004A

בהתאם ל-Q-013:

* M07 שומרת tax/event year.
* M07 יכולה לשמור reference ל-official parameter set שהתקיים בזמן assessment.
* M07 אינה בעלת parameter values.
* M07 אינה יוצרת client-specific parameter set.
* M07 אינה מעתיקה global authority lifecycle.

הבחירה המומלצת:

| Parameter evidence                          | B1                                                  |
| ------------------------------------------- | --------------------------------------------------- |
| Official parameter-set ID                   | Optional, רק לאחר server-side repository resolution |
| Parameter-set fingerprint                   | Optional, לצד ה-ID                                  |
| Resolution timestamp                        | Optional technical evidence                         |
| Requested tax year/effective date           | Included as assessment context                      |
| Parameter values snapshot                   | Excluded                                            |
| Client ownership                            | Forbidden                                           |
| Caller-supplied official authority          | Forbidden                                           |
| Parameter accepted-for-use                  | Excluded                                            |
| Automatic parameter resolution for fixation | Excluded                                            |

אם אין active official parameter set, B1 יכולה לשמור absence או finding טכני. היא אינה ממציאה set ואינה חוסמת עבודה שאינה דורשת אותו.

## 22. Migration Boundary

ה-migration הצפוי יהיה additive בלבד.

### Expected tables

* `m07_evidence_revisions`
* `m07_fact_evidence`
* `m07_planner_assertions`
* `m07_assessment_findings`

### Migration requirements

* Parent revision: `a8e4f2c6d901`.
* Head יחיד לאחר migration.
* אין seed.
* אין backfill.
* אין יצירת M07 profiles מלאכותיים.
* אין שינוי ב-fixation snapshots.
* אין שינוי ב-dependency manifests.
* `client_id` FK בכל parent ו-child.
* Composite client/revision invariant ברמת DB ככל שניתן.
* IDs באורך עד 64.
* `Date`, timezone-aware `DateTime`, bounded strings ו-JSON תואמי PostgreSQL ו-SQLite.
* Fingerprints באורך 64 hex.
* Indexes על client, profile, revision, tax year, event reference ו-lifecycle.
* אין unique constraint בשם או במשמעות של current authority.
* אין latest-wins constraint.
* Downgrade יסרב למחיקה כאשר קיימת finalized, superseded או abandoned evidence.
* Downgrade ריק יכול להסיר את הטבלאות לפי convention קיים.
* אין destructive alteration לטבלאות קיימות.

Final DDL אינו מוגדר בדוח זה.

## 23. Historical Behavior

* Existing fixation snapshots נשארים historical-only.
* Caller-provided M07 context אינו הופך ל-B1 evidence.
* אין backfill של `profile_id`.
* אין inference של qualification.
* אין inference של warning review.
* אין inference של reviewer authority.
* אין conversion של dependency manifest לרשומת B1.
* Existing runs, results, audits ו-validation errors אינם משתנים.
* Finalized B1 revision נשאר immutable גם אם source CRUD record משתנה או נמחק.
* canonical payload חייב להספיק להבנת הראיות כפי שהיו בעת finalization.
* Future run reference דורש authorization לחבילת integration נפרדת.

## 24. Client Isolation

Invariants חובה:

* כל profile revision שייך ללקוח אחד בלבד.
* כל fact, assertion ו-finding שייך לאותו client ולאותו revision.
* Cross-client child reference נכשל.
* Source record reference נבדק לפי client.
* Read/list query מתחיל ב-`client_id`.
* Revision ID של לקוח אחר מוחזר כ-not found ולא חושף existence.
* Supersession בין clients אסור.
* Supersession בין profiles שונים אסור.
* Parameter-set reference נשאר global ומסומן ככזה.
* Global parameter reference אינו מקבל `client_id`.
* Service אינו מקבל client identity רק מתוך complete caller DTO.
* DB constraints ו-service invariants נדרשים יחד.

## 25. Error Taxonomy

| Error code                         | שימוש                                               |
| ---------------------------------- | --------------------------------------------------- |
| `revision_not_found`               | Revision אינו קיים בהיקף הלקוח                      |
| `client_mismatch`                  | Parent, child או source reference שייך ללקוח אחר    |
| `cross_revision_reference`         | Child או finding מפנה ל-revision אחר                |
| `invalid_draft_transition`         | פעולה אינה מותרת במצב הנוכחי                        |
| `finalized_evidence_immutable`     | ניסיון לשנות finalized evidence                     |
| `abandoned_revision_closed`        | ניסיון לשנות abandoned draft                        |
| `supersession_conflict`            | Revision כבר superseded או successor אינו תקין      |
| `source_reference_invalid`         | Source record חסר או אינו תואם ללקוח                |
| `duplicate_fact_identity`          | Fact identity כפול בתוך revision                    |
| `duplicate_finding_identity`       | Stable finding identity כפול                        |
| `invalid_collection_state`         | Collection vocabulary לא תקין                       |
| `invalid_verification_state`       | Verification vocabulary לא תקין                     |
| `assertion_basis_required`         | Assertion חסרה basis                                |
| `condition_basis_required`         | `confirmed_none` או `not_applicable` ללא basis      |
| `missing_required_evidence`        | Required evidence חסר                               |
| `evidence_conflict`                | נמצאו מקורות סותרים                                 |
| `technical_assessment_unavailable` | Assessment אינו יכול להתבצע                         |
| `incompatible_schema`              | Schema version אינה נתמכת                           |
| `incompatible_rule_version`        | Rule version אינה נתמכת                             |
| `ambiguous_revision_query`         | Query יחידאית החזירה יותר מ-revision אחד            |
| `authority_field_forbidden`        | Command כולל qualified, accepted או authority field |
| `caller_actor_forbidden`           | Ordinary payload מנסה לקבוע actor מאומת             |

אלה technical errors בלבד.

## 26. Test Plan

### Model and migration

* Additive upgrade מכל head קיים.
* Head יחיד `new_revision`.
* Empty migration creates no evidence rows.
* No backfill.
* Client FK enforced.
* Composite child/client/revision invariants.
* Stable generated IDs are unique and at most 64 characters.
* SQLite persistence.
* PostgreSQL-compatible DDL inspection.
* Downgrade succeeds when tables contain no retained evidence.
* Downgrade refuses silent loss of finalized evidence.
* Existing migration chain remains intact.

### Evidence

* Structured source facts preserved.
* Multiple sources for one field preserved.
* Provenance fields preserved.
* Verification fields preserved.
* `confirmed_none` requires basis.
* `not_applicable` requires basis.
* Missing, unknown, not-collected and unresolved remain distinguishable.
* Source conflicts preserve all candidate evidence.
* Rejected and superseded evidence remain readable.
* Canonical payload is deterministic.
* Fingerprint is order-independent where order has no meaning.
* Meaningful source, fact or rule change changes fingerprint.

### Planner assertions

* Assertion remains separate from source fact.
* Assertion cannot overwrite source value.
* New assertion is additive.
* Actor and timestamp required.
* Basis required.
* `planner_asserted` fact references an assertion.
* Finalized assertion is immutable.
* Assertion alone does not resolve conflict.
* Assertion creates no qualification or acceptance.

### Warning and technical assessment

* Warning has stable ID.
* Warning fingerprint binds code, content, rule version and affected evidence.
* Changed warning content changes fingerprint.
* Changed rule version changes fingerprint.
* Required missing fact returns incomplete and blocked outcomes.
* Source conflict returns conflicting and blocked outcomes.
* Complete evidence returns `evidence_complete`.
* Warning can coexist without generating `warning_reviewed`.
* Assessment is deterministic.
* Unknown rule version fails closed.
* No professional state is serialized.

### Lifecycle

* Draft accepts allowed commands.
* Finalization creates canonical payload and fingerprint.
* Finalization of incomplete evidence is permitted but remains technically incomplete.
* Finalized revision cannot be updated.
* Finalized child cannot be added, updated or deleted.
* Abandoned revision cannot be reopened.
* Correction creates a new revision.
* Supersession is additive and atomic.
* Failed supersession rolls back.
* Direct ORM mutation is blocked.
* Finalized evidence cannot be deleted.
* No trust token, wrapper or marker exists.

### Client isolation

* Cross-client read returns not found.
* Cross-client list is empty or rejected.
* Cross-client source reference fails.
* Cross-client fact creation fails.
* Cross-client assertion fails.
* Cross-client finding fails.
* Cross-client predecessor fails.
* Cross-client supersession fails.
* Global parameter reference remains global.

### Authority boundary

* Caller `qualified` payload does not create B1 record.
* Caller `warning_reviewed` payload does not create B1 record.
* Caller `accepted_for_use` field is rejected.
* Caller actor is not treated as authenticated.
* Returned read DTO cannot be posted as finalize command.
* Equality to historical snapshot grants nothing.
* Finalized evidence is not an M07 authority record.
* Chronological latest is not current authority.
* No current selector exists.
* No fixation admission mapping exists.
* No historical backfill occurs.

### Regression

* Focused PKG-004B1 tests.
* Full backend suite.
* Migration safety suite.
* PKG-001 regression.
* PKG-002 regression.
* PKG-003 regression.
* PKG-004A regression.
* Relevant client API isolation tests.
* Frontend tests.
* Frontend production build.
* Python compile/static check.
* `alembic heads`.
* `git diff --check`.

## 27. Acceptance Criteria

כל השורות הן mandatory acceptance evidence. אין PASS לפני implementation audit עצמאי.

| AC        | Requirement                                 | Required implementation evidence            | Required test evidence                   | Definition status |
| --------- | ------------------------------------------- | ------------------------------------------- | ---------------------------------------- | ----------------- |
| AC-B1-001 | Client-specific source evidence persisted   | Parent and child models with client FK      | Persistence and cross-client tests       | MANDATORY         |
| AC-B1-002 | Material facts preserve provenance          | Source fields and structured value          | Round-trip evidence tests                | MANDATORY         |
| AC-B1-003 | Material facts preserve verification        | M07-specific verification field             | Vocabulary and round-trip tests          | MANDATORY         |
| AC-B1-004 | Collection states remain distinct           | M07 collection contract                     | State-specific tests                     | MANDATORY         |
| AC-B1-005 | Missing evidence is explicit                | Structured finding                          | Required-field negative tests            | MANDATORY         |
| AC-B1-006 | Unresolved evidence is explicit             | Structured finding                          | Unresolved behavior test                 | MANDATORY         |
| AC-B1-007 | Conflicts preserve every source             | Conflict finding and source refs            | No-ranking conflict test                 | MANDATORY         |
| AC-B1-008 | Planner assertions are separate             | Dedicated assertion records                 | Non-overwrite tests                      | MANDATORY         |
| AC-B1-009 | Warning evidence is stable and versioned    | Warning subtype and fingerprint             | Content and version mutation tests       | MANDATORY         |
| AC-B1-010 | Technical outcomes are deterministic        | Versioned assessment logic                  | Repeated assessment equality tests       | MANDATORY         |
| AC-B1-011 | No professional qualification exists        | Models and schemas lack professional states | Forbidden-field tests                    | MANDATORY         |
| AC-B1-012 | Finalized revisions are immutable           | ORM and service protections                 | Direct mutation tests                    | MANDATORY         |
| AC-B1-013 | Corrections create revisions                | Predecessor and successor linkage           | Correction history tests                 | MANDATORY         |
| AC-B1-014 | Supersession is atomic                      | Narrow service operation                    | Rollback and race-negative tests         | MANDATORY         |
| AC-B1-015 | No current authority selector exists        | No current resolver or route                | Signature and repository search tests    | MANDATORY         |
| AC-B1-016 | Caller cannot forge finalized evidence      | Command-based write boundary                | Whole-DTO rejection tests                | MANDATORY         |
| AC-B1-017 | Historical snapshots remain unchanged       | No migration or service mutation            | Before/after snapshot tests              | MANDATORY         |
| AC-B1-018 | No automatic fixation integration           | No admission-service changes                | PKG-001 regression and caller-path tests | MANDATORY         |
| AC-B1-019 | Parameter authority is not duplicated       | ID/fingerprint reference only               | No-values and no-client-ownership tests  | MANDATORY         |
| AC-B1-020 | Migration is additive and single-head       | One new migration                           | Upgrade, downgrade and heads tests       | MANDATORY         |
| AC-B1-021 | No seed or backfill                         | Empty upgrade behavior                      | Row-count tests                          | MANDATORY         |
| AC-B1-022 | Client isolation applies to all children    | DB and service invariants                   | Cross-client matrix                      | MANDATORY         |
| AC-B1-023 | Final canonical payload is readable         | Server-built JSON snapshot                  | Schema and round-trip tests              | MANDATORY         |
| AC-B1-024 | Fingerprint binds material evidence         | Canonical fingerprint builder               | Material-change and ordering tests       | MANDATORY         |
| AC-B1-025 | Every record declares evidence-only meaning | Contract field or documented invariant      | Serialization tests                      | MANDATORY         |

## 28. Negative Acceptance Criteria

| NAC        | Prohibited behavior                             |
| ---------- | ----------------------------------------------- |
| NAC-B1-001 | Persisting `qualified`                          |
| NAC-B1-002 | Persisting `warning_reviewed`                   |
| NAC-B1-003 | Professional acceptance                         |
| NAC-B1-004 | `accepted_for_use`                              |
| NAC-B1-005 | Reviewer authorization or review decision       |
| NAC-B1-006 | Current M07 authority selector                  |
| NAC-B1-007 | Latest-wins authority                           |
| NAC-B1-008 | Automatic eligibility-date inference            |
| NAC-B1-009 | Caller actor treated as authenticated           |
| NAC-B1-010 | Trust token, marker, wrapper or trusted factory |
| NAC-B1-011 | Caller-created finalized profile DTO            |
| NAC-B1-012 | Direct mutation of finalized evidence           |
| NAC-B1-013 | Deletion of finalized evidence                  |
| NAC-B1-014 | Source ranking or automatic conflict resolution |
| NAC-B1-015 | Planner assertion overwriting source fact       |
| NAC-B1-016 | Backfill from historical fixation runs          |
| NAC-B1-017 | Backfill from dependency manifests              |
| NAC-B1-018 | Client-owned duplicate parameter sets           |
| NAC-B1-019 | Parameter values copied into each M07 revision  |
| NAC-B1-020 | Automatic M08 admission integration             |
| NAC-B1-021 | Professional stale lifecycle                    |
| NAC-B1-022 | Full M08F implementation                        |
| NAC-B1-023 | M08E or formal 161D generation                  |
| NAC-B1-024 | M09-M14 changes                                 |
| NAC-B1-025 | 02M changes                                     |
| NAC-B1-026 | UI changes                                      |
| NAC-B1-027 | CBS calls or adapter changes                    |
| NAC-B1-028 | Fixation engine changes                         |
| NAC-B1-029 | Production-readiness claim                      |
| NAC-B1-030 | V1/V2 parity claim                              |

## 29. Explicit Exclusions

* PKG-004B2.
* Professional qualification.
* Warning review and acceptance.
* Accepted-for-use.
* Current M07 authority.
* Automatic current-context resolver.
* Automatic retirement or eligibility determination.
* Automatic pension-commencement determination.
* Professional source ranking.
* Conflict resolution.
* Downstream eligibility.
* Stale, valid, invalidated or requires-review lifecycle.
* Fixation admission integration.
* Grant/capitalization authority.
* Future-reserve authority.
* Prior-fixation authority.
* Automatic official parameter selection for calculations.
* Tax calculations.
* Fixation calculations.
* CBS.
* Engine changes.
* Formal 161D.
* M08E.
* Full M08F.
* M09-M14.
* 02M.
* UI.
* Production administration/authentication.
* Production readiness.
* V1/V2 parity.

## 30. Stop Conditions

Implementation must stop if:

* A professional rule must be invented.
* Qualification must be added.
* Warning review or acceptance must be added.
* Accepted-for-use must be added.
* An authoritative eligibility date must be inferred.
* Caller data must be upgraded into authority.
* Source facts and planner assertions cannot remain separate.
* Conflict evidence would require automatic source selection.
* A caller-provided actor must be trusted as authenticated.
* Finalized evidence cannot be made immutable.
* Migration requires destructive alteration.
* Existing fixation snapshots or manifests must be rewritten.
* Historical runs must be backfilled.
* A current-authority selector becomes necessary.
* M08 admission integration becomes necessary.
* Professional stale lifecycle must be introduced.
* Full M08F or M08E must be opened.
* M09-M14, 02M, UI, CBS or the engine must be changed.
* A code correction outside the authorized package would be required.

## 31. Known Limitations

| Limitation                                                                       | Classification                            |
| -------------------------------------------------------------------------------- | ----------------------------------------- |
| No production administrative authentication                                      | Accepted limitation for service-first B1  |
| Actor is administrative/service context rather than proven professional identity | Accepted with explicit disclosure         |
| No authoritative retirement-date resolver                                        | Outside B1                                |
| No authoritative pension-commencement resolver                                   | Outside B1                                |
| No qualification decision                                                        | Intended exclusion                        |
| No warning review                                                                | Intended exclusion                        |
| No accepted-for-use                                                              | Intended exclusion                        |
| No current selector                                                              | Intended exclusion                        |
| No automatic fixation integration                                                | Intended exclusion                        |
| Existing source CRUD records remain mutable                                      | Mitigated by finalized canonical snapshot |
| Generic fact vocabularies do not map automatically                               | Intended fail-closed behavior             |
| No prior-withdrawal authoritative model                                          | Missing upstream source                   |
| No prior-fixation authoritative model                                            | Missing upstream source                   |
| No typed Form 161/161D fact model                                                | Generic document metadata only            |
| Official parameter content may not be populated                                  | Does not block evidence storage           |
| Raw SQL/database-admin bypass                                                    | Operational limitation                    |
| No UI                                                                            | Intended exclusion                        |
| No historical backfill                                                           | Intended exclusion                        |
| No professional stale mapping                                                    | Intended exclusion                        |

## 32. Omer Decisions Required

לא נדרשת החלטת עומר נוספת כדי להגדיר או, לאחר authorization נפרד, לממש את B1 בלבד.

הסיבות:

* החוזה המאושר כבר מגדיר את קבוצות העובדות הנדרשות והמותנות.
* collection, verification, missing, unresolved, conflict ו-assertion boundaries מתועדים.
* B1 יכולה לשמור retirement או eligibility fact עם מקור מבלי לבחור מקור authoritative.
* B1 יכולה לשמור pension commencement fact כאשר קיים מבלי להכריע applicability מקצועית.
* technical assessment מתאר evidence בלבד.
* incomplete ו-conflicting revisions יכולים להישמר ולהינעל ללא qualification.

החלטות בנושאים הבאים נשארות מחוץ ל-B1:

* משמעות `qualified`.
* משמעות `warning_reviewed`.
* זהות הגורם המוסמך להחליט.
* review granularity.
* accepted-for-use.
* current authority.
* professional stale behavior.

היעדר ההחלטות האלה אינו חוסם את B1, כל עוד הן לא נכנסות ל-implementation.

## 33. Recommended Implementation Gate

הגדרת החבילה מספקת boundary טכני צר, acceptance criteria, negative criteria, migration seam ו-stop conditions.

המלצת ה-gate פירושה שהחבילה מוכנה לעבור להחלטת authorization נפרדת של עומר או GPT Chat. היא אינה authorization בפני עצמה.

PKG_004B1_READY_FOR_IMPLEMENTATION_AUTHORIZATION
