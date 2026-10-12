import { buildApiUrl } from "./apiBase";

export interface AuthenticatedSession {
  schema_version: "RTDIR_AUTHENTICATED_SESSION_V1";
  authenticated: true;
  actor_id: string;
  expires_at: string;
  csrf_token: string;
}

async function decode(response: Response): Promise<AuthenticatedSession> {
  if (!response.ok) throw new Error("AUTHENTICATION_REQUIRED");
  return response.json() as Promise<AuthenticatedSession>;
}

export function restoreSession(signal?: AbortSignal): Promise<AuthenticatedSession> {
  return fetch(buildApiUrl("/auth/session"), {credentials: "include", signal}).then(decode);
}

export function login(username: string, password: string): Promise<AuthenticatedSession> {
  return fetch(buildApiUrl("/auth/login"), {
    method: "POST", credentials: "include", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username, password}),
  }).then(decode);
}

export async function logout(csrf: string): Promise<number> {
  const response = await fetch(buildApiUrl("/auth/logout"), {
    method: "POST", credentials: "include", headers: {"X-RTDIR-CSRF": csrf},
  });
  return response.status;
}
