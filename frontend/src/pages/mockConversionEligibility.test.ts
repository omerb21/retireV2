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
  it("retains V1 product-specific investment/education exemptions and fails closed for unknowns", () => {
    expect(mockConversionRejection("תגמולי_עובד_אחרי_2000", "גמל להשקעה", "capital")).toBeNull();
    expect(mockConversionRejection("unknown", "קרן פנסיה", "capital")).toMatch(/אין כלל/);
    expect(mockConversionRejection("unknown", "קרן פנסיה", "unchanged")).toBeNull();
  });
});
