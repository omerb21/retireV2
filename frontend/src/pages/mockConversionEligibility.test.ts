import { describe, expect, it } from "vitest";
import { mockConversionRejection } from "./mockConversionEligibility";

describe("V1-derived mock conversion warnings (not authoritative)", () => {
  it("blocks current-employer severance even for pension", () => {
    expect(mockConversionRejection("פיצויים_מעסיק_נוכחי", "קרן פנסיה", "pension")).toMatch(/מעסיק נוכחי/);
  });
  it("blocks capital conversion of pension-continuity severance", () => {
    expect(mockConversionRejection("פיצויים_ממעסיקים_קודמים_רצף_קצבה", "קרן פנסיה", "capital")).toMatch(/הון/);
    expect(mockConversionRejection("פיצויים_ממעסיקים_קודמים_רצף_קצבה", "קרן פנסיה", "pension")).toBeNull();
  });
  it("allows both actions on settled severance and pre-2000 rewards", () => {
    expect(mockConversionRejection("פיצויים_לאחר_התחשבנות", "קרן פנסיה", "capital")).toBeNull();
    expect(mockConversionRejection("תגמולי_עובד_עד_2000", "קרן פנסיה", "capital")).toBeNull();
  });
  it("rejects capital on post-2000 pension contributions", () => {
    expect(mockConversionRejection("תגמולי_עובד_אחרי_2000", "קרן פנסיה", "capital")).toMatch(/הון/);
  });
  it("limits exact investment/education exceptions to recognized reward components", () => {
    expect(mockConversionRejection("תגמולי_עובד_אחרי_2000", "קופת גמל להשקעה", "capital")).toBeNull();
    expect(mockConversionRejection("תגמולי_מעביד_אחרי_2008_לא_משלמת", "קרן השתלמות", "capital")).toBeNull();
    expect(mockConversionRejection("פיצויים_לאחר_התחשבנות", "קופת גמל להשקעה", "capital")).toMatch(/התאמת מקור/);
    expect(mockConversionRejection("פיצויים_מעסיק_נוכחי", "education_fund", "pension")).toMatch(/התאמת מקור/);
  });
  it("fails closed for missing, ambiguous, substring-only and unknown product types", () => {
    expect(mockConversionRejection("תגמולי_עובד_אחרי_2000", "", "capital")).toMatch(/התאמת מקור/);
    expect(mockConversionRejection("תגמולי_עובד_אחרי_2000", "סוג מוצר לא ממופה", "capital")).toMatch(/התאמת מקור/);
    expect(mockConversionRejection("תגמולי_עובד_אחרי_2000", "קרן השתלמות ישנה", "capital")).toMatch(/התאמת מקור/);
    expect(mockConversionRejection("unknown", "קרן פנסיה", "capital")).toMatch(/אין כלל/);
  });
});
