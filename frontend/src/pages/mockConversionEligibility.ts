/**
 * UX-MOCK ONLY. Snapshot of the V1 backend conversion permission matrix,
 * from app/services/pension_portfolio/conversion_rules.py (2026-10-23).
 * NOT a legal/tax authority and NOT a substitute for server-side validation.
 * Never use this for authoritative scenario execution or tax decisions.
 */
type Action = "pension" | "capital";
const PENSION_ONLY = new Set([
  "פיצויים_ממעסיקים_קודמים_רצף_קצבה",
  "תגמולי_עובד_אחרי_2000", "תגמולי_מעביד_אחרי_2000",
  "תגמולי_עובד_אחרי_2008_לא_משלמת", "תגמולי_מעביד_אחרי_2008_לא_משלמת",
]);
const BOTH = new Set([
  "פיצויים_לאחר_התחשבנות", "תגמולי_עובד_עד_2000", "תגמולי_מעביד_עד_2000",
]);
const BLOCKED: Record<string, string> = {
  "פיצויים_מעסיק_נוכחי": "לא ניתן להמיר כספים ממעסיק נוכחי. נדרש תהליך סיום עבודה.",
  "פיצויים_שלא_עברו_התחשבנות": "לא ניתן להמיר כספים שלא עברו התחשבנות.",
  "פיצויים_ממעסיקים_קודמים_רצף_זכויות": "לא ניתן להמיר כספים ברצף זכויות ללא התחשבנות.",
};
const REWARD_COMPONENTS = new Set([
  "תגמולי_עובד_עד_2000", "תגמולי_עובד_אחרי_2000", "תגמולי_עובד_אחרי_2008_לא_משלמת",
  "תגמולי_מעביד_עד_2000", "תגמולי_מעביד_אחרי_2000", "תגמולי_מעביד_אחרי_2008_לא_משלמת",
]);
const SPECIAL_SAVINGS_TYPES = new Set([
  "קופת גמל להשקעה", "investment_provident_fund",
  "קרן השתלמות", "education_fund", "klal_stud",
]);
const RECOGNIZED_STANDARD_TYPES = new Set([
  "קרן פנסיה", "pension_fund",
  "קופת גמל", "provident_fund",
  "ביטוח מנהלים", "insurance_policy",
  "פוליסת ביטוח חיים משולב חיסכון", "פוליסת ביטוח חיים", "פוליסת חיסכון טהור",
]);
export function mockConversionRejection(code: string, productType: string, action: Action): string | null {
  const kind = (productType || "").trim().toLowerCase();
  if (SPECIAL_SAVINGS_TYPES.has(kind)) {
    return REWARD_COMPONENTS.has(code)
      ? null
      : "רכיב פיצויים אינו תואם לסוג מוצר חיסכון זה; נדרשת התאמת מקור לפני הדמיה.";
  }
  if (!RECOGNIZED_STANDARD_TYPES.has(kind)) {
    return "סוג המוצר חסר, עמום או לא מזוהה; נדרשת התאמת מקור לפני הדמיה.";
  }
  if (BLOCKED[code]) return BLOCKED[code];
  if (BOTH.has(code)) return null;
  if (PENSION_ONLY.has(code)) return action === "pension" ? null : "רכיב כספי זה אינו ניתן להמרה להון לפי כללי V1.";
  return "אין כלל המרה מזוהה לרכיב זה; החלטת ההדמיה נחסמה.";
}
