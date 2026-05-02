# V2 Full System Master Spec - עברית

## 1. מטרת המערכת

מערכת V2 היא בנייה מחדש מאפס של מערכת תכנון פרישה מקצועית, דטרמיניסטית ושקופה.

המטרה אינה לשפר את V1 ואינה להעתיק את V1, אלא לבנות מערכת חדשה שבה:
- כל חישוב נמצא במקום אחד בלבד
- כל תוצאה ניתנת לשחזור
- כל שלב מתועד
- אין קופסה שחורה
- אין אלתור של מודל מבצע
- אין תלות ב-LLM לצורך חישובים
- אין לוגיקה עסקית ב-UI או ב-API

V1 משמשת כ-reference לקריאה בלבד: מקור להבנת התנהגות, שדות, נוסחאות שאושרו, מקרי קצה וטעויות שיש להימנע מהן.

## 2. גבולות המערכת המלאה

המערכת המלאה מיועדת לתמוך בעתיד ב:
- ניהול לקוחות
- פרופיל לקוח
- מוצרים פנסיוניים
- תעסוקה ומענקים
- היוונים בפועל
- קיבוע זכויות
- הכנסות נוספות
- נכסים
- מיסוי
- תזרים פרישה
- תרחישים
- השוואת חלופות
- תכנית פרישה סופית
- דוחות עתידיים, רק לאחר שהחישובים יציבים

מחוץ למערכת עד להחלטה אחרת:
- Agent / LLM
- אוטומציות שיווק
- חיבור למסלקה
- אינטגרציות חיצוניות
- OCR / parsing מסמכים
- המלצות חכמות
- PDF בשלב 1
- חישוב הצמדה אוטומטי בשלב 1

## 3. עקרונות אכיפה קבועים

1. כל חישוב מתבצע רק בתוך Engine ייעודי.
2. אין חישובים ב-Frontend.
3. אין חישובים ב-API routes.
4. אין DB access בתוך Engines.
5. אין fallback בשום חישוב.
6. אין מקור סמכות כפול לאותו נתון.
7. אין hidden state.
8. אין mutation של תוצאות עבר.
9. כל calculation run נשמר כ-snapshot בלתי ניתן לשינוי.
10. כל output ניתן לשחזור מלא מתוך input snapshot.
11. אין שימוש ב-V1 כקוד מקור.
12. אם משהו לא מוגדר במסמכים, עוצרים ומעלים open question.

## 4. מודולי המערכת המלאה

### Client & Profile Module
אחראי על נתוני לקוח, פרופיל בסיסי ונתוני רקע. לא מחשב.

### Pension & Savings Module
אחראי על מקורות פנסיוניים, קופות, קצבאות צפויות ונתוני מוצר. לא מחשב מס ולא קיבוע.

### Employment & Grants Module
אחראי על תעסוקה, מענקים, תאריכים וסכומים. אינו מחשב פגיעה בפטור.

### Actual Capitalizations Module
אחראי על היוונים/משיכות הוניות בפועל בלבד. אינו מסיק נתונים מתרחישים.

### Fixation Engine
אחראי על:
- תקרת הון פטורה
- פגיעה ממענקים
- פגיעה מהיוונים בפועל
- שריון מענק עתידי
- השפעת IDF אם רלוונטי
- יתרת הון פטורה
- קצבה פטורה
- audit rows

### Tax Engine
אחראי על מס בלבד. אינו מחשב זכאות לפטור.

### Cashflow Engine
אחראי על תזרים חודשי/שנתי בפרישה. משתמש בתוצאות Engines אחרים, לא מחשב אותן מחדש.

### Scenario Engine / Builder
אחראי על הרצת חלופות והזנת פרמטרים. אינו מחזיק נוסחאות עסקיות.

### Comparison Module
אחראי להצגת השוואות בין תרחישים קיימים. אינו מחשב מחדש.

### Retirement Plan Module
אחראי לאריזת תכנית פרישה מסכמת מתוך outputs קיימים.

## 5. Source of Truth

- פטור הוני: Fixation Engine בלבד
- קצבה פטורה: Fixation Engine בלבד
- פגיעת מענקים: Fixation Engine בלבד
- פגיעת היוונים בפועל: Fixation Engine בלבד
- IDF impact: Fixation Engine בלבד
- מס: Tax Engine בלבד
- תזרים: Cashflow Engine בלבד
- תרחיש: Scenario Builder כ-orchestrator בלבד
- תכנית סופית: snapshot של outputs, לא מקום חישוב

## 6. זרימת עבודה מלאה עתידית

Client → Profile → Pension Data → Employment → Grants → Actual Capitalizations → Fixation → Tax → Cashflow → Scenario → Comparison → Retirement Plan

אין קפיצה של מודול קדימה לחישוב של מודול אחר. אין חישוב חוזר ב-read. אין עדכון לאחור של תוצאה.

## 7. חלוקת שלבים

### Phase 1 of V2
Fixation workflow בלבד:
- Client
- Profile
- Employment
- Grants
- Actual Capitalizations
- Fixation Parameters
- Fixation Engine
- Result
- Audit
- History

### Phase 2
הוספת Pension Engine, Tax Engine, Cashflow Engine.

### Phase 3
Scenario Builder והשוואת חלופות.

### Phase 4
Retirement Plan מלא ודוחות.

## 8. Tech Stack נעול

- Backend: FastAPI מאפס
- Frontend: React custom app מאפס
- Database: PostgreSQL
- ORM: SQLAlchemy
- Migrations: Alembic
- Validation: Pydantic
- Tests: Pytest + FastAPI TestClient + Golden tests
- Hosting during build: local-first
- Auth: deferred, auth-ready only
- Templates/boilerplates: forbidden

## 9. Phase 1 אסור לכלול

- Pension Engine
- Tax Engine
- Cashflow Engine
- Scenario Builder
- Scenario Comparison
- Reports / PDF
- LLM / Agent
- External integrations
- Automatic indexation
- Authentication implementation
- Admin screens
- Business table management UI

## 10. כלל סופי

כל עבודה על V2 חייבת להתבצע לפי Build Management Manual. אם יש סתירה בין מסמכים, פועלים לפי Artifact Hierarchy שמוגדרת שם.
