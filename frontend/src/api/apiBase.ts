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
