/**
 * UX-MOCK ONLY. Snapshot of the V1 backend conversion permission matrix,
 * from app/services/pension_portfolio/conversion_rules.py (2026-10-23).
 * NOT a legal/tax authority and NOT a substitute for server-side validation.
 * Never use this for authoritative scenario execution or tax decisions.
 */
type Action = "pension" | "capital" | "unchanged";
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
export function mockConversionRejection(code: string, productType: string, action: Action): string | null {
  if (action === "unchanged") return null;
  const kind = (productType || "").toLowerCase();
  // V1 backend product-type overrides come before component rules.
  if (kind.includes("גמל להשקעה") || kind.includes("investment_provident_fund") ||
      kind.includes("השתלמות") || kind.includes("education_fund") || kind.includes("klal_stud")) return null;
  if (BLOCKED[code]) return BLOCKED[code];
  if (BOTH.has(code)) return null;
  if (PENSION_ONLY.has(code)) return action === "pension" ? null : "רכיב כספי זה אינו ניתן להמרה להון לפי כללי V1.";
  return "אין כלל המרה מזוהה לרכיב זה; החלטת ההדמיה נחסמה.";
}
