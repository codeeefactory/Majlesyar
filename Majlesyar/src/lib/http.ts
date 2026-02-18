export interface AuthTokens {
  access: string;
  refresh: string;
}

const TOKENS_STORAGE_KEY = "majlesyar_admin_tokens";
const ENV_API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim();
const LOCALHOST_BASE_URL_REGEX = /^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?(?:\/.*)?$/i;
const SHOULD_IGNORE_ENV_BASE_URL =
  import.meta.env.PROD &&
  Boolean(ENV_API_BASE_URL) &&
  LOCALHOST_BASE_URL_REGEX.test(ENV_API_BASE_URL);
const API_BASE_URL =
  ENV_API_BASE_URL && !SHOULD_IGNORE_ENV_BASE_URL ? ENV_API_BASE_URL.replace(/\/+$/, "") : "";

class HttpError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.payload = payload;
  }
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (!API_BASE_URL) return normalizedPath;

  if (API_BASE_URL.endsWith("/api") && normalizedPath.startsWith("/api/")) {
    return `${API_BASE_URL}${normalizedPath.slice(4)}`;
  }
  return `${API_BASE_URL}${normalizedPath}`;
}

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payloadPart] = token.split(".");
    if (!payloadPart) return null;
    const normalized = payloadPart.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const json = atob(padded);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getAuthTokens(): AuthTokens | null {
  try {
    const raw = localStorage.getItem(TOKENS_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthTokens;
    if (!parsed.access || !parsed.refresh) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function setAuthTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKENS_STORAGE_KEY, JSON.stringify(tokens));
}

export function clearAuthTokens(): void {
  localStorage.removeItem(TOKENS_STORAGE_KEY);
}

export function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : null;
  if (!exp) return true;
  return Date.now() >= exp * 1000;
}

export function hasValidAccessToken(): boolean {
  const tokens = getAuthTokens();
  if (!tokens) return false;
  return !isTokenExpired(tokens.access);
}

async function tryRefreshAccessToken(): Promise<string | null> {
  const tokens = getAuthTokens();
  if (!tokens?.refresh || isTokenExpired(tokens.refresh)) {
    clearAuthTokens();
    return null;
  }

  try {
    const response = await fetch(buildUrl("/api/v1/auth/token/refresh/"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });

    if (!response.ok) {
      clearAuthTokens();
      return null;
    }

    const data = (await response.json()) as { access?: string };
    if (!data.access) {
      clearAuthTokens();
      return null;
    }

    const updated = { ...tokens, access: data.access };
    setAuthTokens(updated);
    return updated.access;
  } catch {
    clearAuthTokens();
    return null;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  auth?: boolean;
  body?: unknown;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (!payload) return fallback;
  if (typeof payload === "string") return payload;
  if (typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (typeof record.message === "string") return record.message;
  }
  return fallback;
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = false, body, headers, ...rest } = options;
  const url = buildUrl(path);

  const authTokens = getAuthTokens();
  let requestHeaders: HeadersInit = {
    "Content-Type": "application/json",
    ...(headers || {}),
  };
  if (auth && authTokens?.access) {
    requestHeaders = {
      ...requestHeaders,
      Authorization: `Bearer ${authTokens.access}`,
    };
  }

  const execute = async (accessToken?: string) => {
    const finalHeaders: HeadersInit = {
      ...requestHeaders,
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    };

    return fetch(url, {
      ...rest,
      headers: finalHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };

  let response = await execute();

  if (auth && response.status === 401) {
    const refreshedAccess = await tryRefreshAccessToken();
    if (refreshedAccess) {
      response = await execute(refreshedAccess);
    }
  }

  const payload = await parseResponseBody(response);
  if (!response.ok) {
    throw new HttpError(
      extractErrorMessage(payload, `Request failed with status ${response.status}`),
      response.status,
      payload,
    );
  }

  return payload as T;
}
