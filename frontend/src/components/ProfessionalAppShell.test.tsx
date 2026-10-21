import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ProfessionalAppShell } from "./ProfessionalAppShell";

function renderShell(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ProfessionalAppShell>
        <p>תוכן מקצועי לבדיקה</p>
      </ProfessionalAppShell>
    </MemoryRouter>,
  );
}

describe("ProfessionalAppShell", () => {
  it("keeps the case navigation scoped to the actual client and highlights the active screen", () => {
    renderShell("/clients/42/pension-products");

    const pension = screen.getByRole("link", { name: "התיק הפנסיוני" });
    expect(pension).toHaveAttribute("href", "/clients/42/pension-products");
    expect(pension).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "מענקים היסטוריים" }))
      .toHaveAttribute("href", "/clients/42/grants");
    expect(screen.getByRole("link", { name: "תיק לקוח #42" }))
      .toHaveAttribute("href", "/clients/42");
    expect(screen.getByText("תרחישים והשוואה").closest("[aria-disabled='true']"))
      .toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "תרחישים והשוואה" }))
      .not.toBeInTheDocument();
    expect(screen.getByText("תוכן מקצועי לבדיקה")).toBeInTheDocument();
  });

  it("does not invent client navigation when no client was selected", () => {
    renderShell("/clients");

    expect(screen.getByRole("link", { name: "רשימת לקוחות" })).toHaveAttribute("href", "/clients");
    expect(screen.getByRole("link", { name: "פתיחת לקוח חדש" }))
      .toHaveAttribute("href", "/clients/new");
    expect(screen.queryByRole("link", { name: "התיק הפנסיוני" })).not.toBeInTheDocument();
    expect(screen.getByText("התיק הפנסיוני").closest("[aria-disabled='true']")).toBeInTheDocument();
  });

  it("supports keyboard-accessible menu disclosure and closes it on request", () => {
    renderShell("/clients/5");
    const open = screen.getByRole("button", { name: "פתיחת תפריט" });
    expect(open).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(open);
    const close = screen.getByRole("button", { name: "סגירת תפריט" });
    expect(close).toHaveAttribute("aria-expanded", "true");
    fireEvent.keyDown(document, { key: "Escape" });
    const reopened = screen.getByRole("button", { name: "פתיחת תפריט" });
    expect(reopened).toHaveAttribute("aria-expanded", "false");
    expect(reopened).toHaveFocus();

    fireEvent.click(reopened);
    fireEvent.click(screen.getByRole("button", { name: "סגירת תפריט" }));
    expect(screen.getByRole("button", { name: "פתיחת תפריט" })).toHaveAttribute("aria-expanded", "false");
  });
});
