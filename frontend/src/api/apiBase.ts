interface ApiEnvironment {
  MODE?: string;
  VITE_API_BASE_URL?: string;
}

const SAME_ORIGIN_API_BASE_URL = "/api";

export function resolveApiBaseUrl(env: ApiEnvironment = import.meta.env): string {
  if (env.MODE === "production") {
    return SAME_ORIGIN_API_BASE_URL;
  }

  const configuredBaseUrl = env.VITE_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/$/, "");
  }

  return SAME_ORIGIN_API_BASE_URL;
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
