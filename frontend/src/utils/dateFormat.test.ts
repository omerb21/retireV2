import { describe, expect, it } from "vitest";
import { formatIsoDate, formatIsoTimestamp, parseHebrewDate } from "./dateFormat";

describe("Hebrew date contract", () => {
  it("formats ISO dates as unambiguous DD/MM/YYYY", () => {
    expect(formatIsoDate("2026-08-30")).toBe("30/08/2026");
  });

  it("parses day before month and returns the API ISO contract", () => {
    expect(parseHebrewDate("30/08/2026")).toBe("2026-08-30");
    expect(parseHebrewDate("01/02/2026")).toBe("2026-02-01");
  });

  it("rejects impossible and non-leap dates", () => {
    expect(parseHebrewDate("31/02/2026")).toBeNull();
    expect(parseHebrewDate("29/02/2027")).toBeNull();
  });

  it("accepts a valid leap day", () => {
    expect(parseHebrewDate("29/02/2028")).toBe("2028-02-29");
  });

  it("preserves a blank nullable date", () => {
    expect(parseHebrewDate("")).toBeNull();
    expect(formatIsoDate(null)).toBe("");
  });

  it("renders timestamps without exposing raw ISO", () => {
    expect(formatIsoTimestamp("2026-08-30T12:34:00Z")).toMatch(/^30\/08\/2026 \d{2}:\d{2}$/);
  });
});
