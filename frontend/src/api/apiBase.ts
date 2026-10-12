interface ApiEnvironment {
  MODE?: string;
  VITE_API_BASE_URL?: string;
}

const DEFAULT_LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api";
const TEST_API_BASE_URL = "/api";

export function resolveApiBaseUrl(env: ApiEnvironment = import.meta.env): string {
  const configuredBaseUrl = env.VITE_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/$/, "");
  }

  return env.MODE === "test" ? TEST_API_BASE_URL : DEFAULT_LOCAL_API_BASE_URL;
}

export function buildApiUrl(path: string): string {
  return `${resolveApiBaseUrl()}${path}`;
}

let csrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function configureAuthenticatedApi(token: string | null, onUnauthorized?: () => void): void {
  csrfToken = token;
  unauthorizedHandler = onUnauthorized ?? null;
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  let headers = init.headers ? new Headers(init.headers) : undefined;
  const method = (init.method ?? "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method) && csrfToken) {
    headers ??= new Headers();
    headers.set("X-RTDIR-CSRF", csrfToken);
  }
  const response = await fetch(input, {...init, headers, credentials: "include"});
  if (response.status === 401) unauthorizedHandler?.();
  return response;
}
