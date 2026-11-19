import { ApiTransportError } from "../api/clientsApi";

export const CAS_CONFLICT_MESSAGE = "השמירה לא בוצעה. הרשומה בשרת השתנתה מאז טעינת המסך. הקלט שהזנת נשאר בטופס לצורך בדיקה או העתקה. יש לרענן את הרשומות, להשוות את הנתונים ולפתוח עריכה חדשה לפני ניסיון שמירה נוסף.";

export function isCasConflict(error: unknown): boolean {
  return error instanceof ApiTransportError
    && error.status === 409
    && typeof error.body === "object"
    && error.body !== null
    && "detail" in error.body
    && typeof error.body.detail === "object"
    && error.body.detail !== null
    && "code" in error.body.detail
    && error.body.detail.code === "RECORD_VERSION_CONFLICT";
}
