const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const HEBREW_DATE = /^(\d{2})\/(\d{2})\/(\d{4})$/;

function validDate(year: number, month: number, day: number): boolean {
  const value = new Date(Date.UTC(year, month - 1, day));
  return value.getUTCFullYear() === year &&
    value.getUTCMonth() === month - 1 && value.getUTCDate() === day;
}

export function formatIsoDate(value: string | null | undefined): string {
  if (!value) return "";
  const match = ISO_DATE.exec(value.slice(0, 10));
  if (!match) return value;
  const [, year, month, day] = match;
  return validDate(Number(year), Number(month), Number(day))
    ? `${day}/${month}/${year}` : value;
}

export function parseHebrewDate(value: string, nullable = true): string | null {
  const trimmed = value.trim();
  if (!trimmed) return nullable ? null : "";
  const match = HEBREW_DATE.exec(trimmed);
  if (!match) return null;
  const [, day, month, year] = match;
  if (!validDate(Number(year), Number(month), Number(day))) return null;
  return `${year}-${month}-${day}`;
}

export function formatIsoTimestamp(value: string | null | undefined): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  const parts = new Intl.DateTimeFormat("he-IL", {
    timeZone: "Asia/Jerusalem", day: "2-digit", month: "2-digit",
    year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(parsed);
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((item) => item.type === type)?.value ?? "";
  return `${part("day")}/${part("month")}/${part("year")} ${part("hour")}:${part("minute")}`;
}
