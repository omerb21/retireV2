import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { apiFetch } from "../api/apiBase";
import { AuthenticationGate } from "./AuthenticationGate";

const session = {schema_version: "RTDIR_AUTHENTICATED_SESSION_V1", authenticated: true, actor_id: "planner", expires_at: "2030-01-01T00:00:00Z", csrf_token: "A".repeat(43)};

afterEach(() => vi.unstubAllGlobals());

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

test("failed logout hides client data and offers retry and session check", async () => {
  const mocked = vi.fn()
    .mockResolvedValueOnce({ok: true, json: async () => session})
    .mockResolvedValueOnce({status: 503})
    .mockResolvedValueOnce({status: 204});
  vi.stubGlobal("fetch", mocked);
  render(<AuthenticationGate enforce><p>מידע מקצועי</p></AuthenticationGate>);
  expect(await screen.findByText("מידע מקצועי")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "התנתקות"}));
  expect((await screen.findByText("אימות מצב ההתנתקות")).closest("main")).toHaveAttribute("dir", "rtl");
  expect(screen.queryByText("מידע מקצועי")).not.toBeInTheDocument();
  expect(screen.getByRole("button", {name: "ניסיון התנתקות נוסף"})).toBeInTheDocument();
  expect(screen.getByRole("button", {name: "בדיקת מצב החיבור"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "ניסיון התנתקות נוסף"}));
  await waitFor(() => expect(screen.getByRole("heading", {name: "כניסה למערכת תכנון הפרישה"})).toBeInTheDocument());
});

function StatefulWorkspace() {
  const [client] = useState("לקוח 7");
  return <section><p>{client}</p><p>יעד 12000</p><p>תוצאת השוואה</p>
    <button onClick={() => void apiFetch("/api/protected")}>בקשה מוגנת</button></section>;
}

test("401 session expiry unmounts and clears all client target and comparison state", async () => {
  const mocked = vi.fn()
    .mockResolvedValueOnce({ok: true, json: async () => session})
    .mockResolvedValueOnce({status: 401, ok: false});
  vi.stubGlobal("fetch", mocked);
  render(<AuthenticationGate enforce><StatefulWorkspace /></AuthenticationGate>);
  expect(await screen.findByText("לקוח 7")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "בקשה מוגנת"}));
  expect((await screen.findByRole("heading", {name: "כניסה למערכת תכנון הפרישה"})).closest("main")).toHaveAttribute("dir", "rtl");
  expect(screen.queryByText("לקוח 7")).not.toBeInTheDocument();
  expect(screen.queryByText("יעד 12000")).not.toBeInTheDocument();
  expect(screen.queryByText("תוצאת השוואה")).not.toBeInTheDocument();
});

test("reload remount performs a fresh session request and restores no browser client state", async () => {
  const mocked = vi.fn().mockResolvedValue({ok: true, json: async () => session});
  vi.stubGlobal("fetch", mocked);
  localStorage.setItem("unrelated", "kept");
  const first = render(<AuthenticationGate enforce><StatefulWorkspace /></AuthenticationGate>);
  expect(await screen.findByText("לקוח 7")).toBeInTheDocument();
  first.unmount();
  render(<AuthenticationGate enforce><p>מרחב חדש ללא לקוח</p></AuthenticationGate>);
  expect(await screen.findByText("מרחב חדש ללא לקוח")).toBeInTheDocument();
  expect(mocked.mock.calls.filter(([url]) => url === "/api/auth/session")).toHaveLength(2);
  expect(screen.queryByText("יעד 12000")).not.toBeInTheDocument();
  expect(localStorage.getItem("unrelated")).toBe("kept");
  localStorage.clear();
});

test("credentials session actor csrf and client DTO never enter browser persistence or URL", async () => {
  const localSet = vi.spyOn(Storage.prototype, "setItem");
  const mocked = vi.fn()
    .mockResolvedValueOnce({ok: false, status: 401, json: async () => ({code: "AUTHENTICATION_REQUIRED"})})
    .mockResolvedValueOnce({ok: true, json: async () => session});
  vi.stubGlobal("fetch", mocked);
  render(<AuthenticationGate enforce><p>לקוח סודי</p></AuthenticationGate>);
  fireEvent.change(await screen.findByLabelText("שם משתמש"), {target: {value: "planner"}});
  fireEvent.change(screen.getByLabelText("סיסמה"), {target: {value: "secret"}});
  fireEvent.click(screen.getByRole("button", {name: "כניסה"}));
  expect(await screen.findByText("לקוח סודי")).toBeInTheDocument();
  expect(localSet).not.toHaveBeenCalled();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
  expect(window.location.href).not.toMatch(/planner|secret|csrf|client/i);
  const loginBody = JSON.parse(mocked.mock.calls[1][1].body);
  expect(loginBody).toEqual({username: "planner", password: "secret"});
  localSet.mockRestore();
});

test("login loading authentication error session expiry and logout states are Hebrew RTL", async () => {
  const mocked = vi.fn()
    .mockImplementationOnce(() => new Promise(() => undefined));
  vi.stubGlobal("fetch", mocked);
  const loading = render(<AuthenticationGate enforce><StatefulWorkspace /></AuthenticationGate>);
  expect(screen.getByText("בודק חיבור מאובטח…").closest("main")).toHaveAttribute("dir", "rtl");
  loading.unmount();

  const failed = vi.fn().mockResolvedValue({ok: false, status: 401, json: async () => ({})});
  vi.stubGlobal("fetch", failed);
  render(<AuthenticationGate enforce><StatefulWorkspace /></AuthenticationGate>);
  const loginHeading = await screen.findByRole("heading", {name: "כניסה למערכת תכנון הפרישה"});
  expect(loginHeading.closest("main")).toHaveAttribute("dir", "rtl");
  fireEvent.change(screen.getByLabelText("שם משתמש"), {target: {value: "שגוי"}});
  fireEvent.change(screen.getByLabelText("סיסמה"), {target: {value: "שגויה"}});
  fireEvent.click(screen.getByRole("button", {name: "כניסה"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("ההתחברות נכשלה");
  expect(screen.getByRole("alert").closest("main")).toHaveAttribute("dir", "rtl");
});

test("successful logout clears workspace state and returns to Hebrew login", async () => {
  const mocked = vi.fn()
    .mockResolvedValueOnce({ok: true, json: async () => session})
    .mockResolvedValueOnce({status: 204});
  vi.stubGlobal("fetch", mocked);
  render(<AuthenticationGate enforce><StatefulWorkspace /></AuthenticationGate>);
  expect(await screen.findByText("לקוח 7")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "התנתקות"}));
  expect((await screen.findByRole("heading", {name: "כניסה למערכת תכנון הפרישה"})).closest("main")).toHaveAttribute("dir", "rtl");
  expect(screen.queryByText("לקוח 7")).not.toBeInTheDocument();
  expect(mocked).toHaveBeenLastCalledWith("/api/auth/logout", expect.objectContaining({
    method: "POST", credentials: "include", headers: {"X-RTDIR-CSRF": session.csrf_token},
  }));
});
