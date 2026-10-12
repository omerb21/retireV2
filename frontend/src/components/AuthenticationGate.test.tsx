import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { AuthenticationGate } from "./AuthenticationGate";

const session = {schema_version: "RTDIR_AUTHENTICATED_SESSION_V1", authenticated: true, actor_id: "planner", expires_at: "2030-01-01T00:00:00Z", csrf_token: "A".repeat(43)};

test("restores a server session before exposing workspace data", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ok: true, json: async () => session}));
  render(<AuthenticationGate enforce><p>מידע מקצועי</p></AuthenticationGate>);
  expect(screen.queryByText("מידע מקצועי")).not.toBeInTheDocument();
  expect(await screen.findByText("מידע מקצועי")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith("/api/auth/session", expect.objectContaining({credentials: "include"}));
});

test("keeps password only in form state and clears it after failed login", async () => {
  const mocked = vi.fn().mockResolvedValue({ok: false, json: async () => ({code: "AUTHENTICATION_FAILED"})});
  vi.stubGlobal("fetch", mocked);
  render(<AuthenticationGate enforce><p>מידע מקצועי</p></AuthenticationGate>);
  const username = await screen.findByLabelText("שם משתמש");
  const password = screen.getByLabelText("סיסמה") as HTMLInputElement;
  fireEvent.change(username, {target: {value: "user"}}); fireEvent.change(password, {target: {value: "secret"}});
  fireEvent.click(screen.getByRole("button", {name: "כניסה"}));
  await waitFor(() => expect(password.value).toBe(""));
  expect(screen.getByRole("alert")).toHaveTextContent("ההתחברות נכשלה");
  expect(mocked).toHaveBeenLastCalledWith("/api/auth/login", expect.objectContaining({credentials: "include"}));
});
