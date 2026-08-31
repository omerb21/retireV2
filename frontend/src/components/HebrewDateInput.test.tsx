import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HebrewDateInput } from "./HebrewDateInput";

describe("HebrewDateInput", () => {
  it("shows an ISO birth date as DD/MM/YYYY and emits ISO after editing", () => {
    const onChange = vi.fn();
    render(<HebrewDateInput ariaLabel="תאריך לידה" value="1965-01-01" onChange={onChange} />);
    const input = screen.getByLabelText("תאריך לידה");
    expect(input).toHaveValue("01/01/1965");
    fireEvent.change(input, { target: { value: "01/02/2026" } });
    expect(onChange).toHaveBeenLastCalledWith("2026-02-01");
  });

  it("rejects an invalid downstream statement date in Hebrew", () => {
    const onChange = vi.fn();
    render(<HebrewDateInput ariaLabel="תאריך דוח" value="" onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("תאריך דוח"), { target: { value: "31/02/2026" } });
    expect(screen.getByRole("alert")).toHaveTextContent("תאריך לא תקין");
    expect(onChange).not.toHaveBeenCalled();
  });
});
