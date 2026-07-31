/**
 * The API client.
 *
 * One place that talks to the backend, for the same reason the backend has one
 * ProviderRouter: auth headers, refresh, and error shape are policy, and policy
 * implemented in fifty call sites is policy implemented fifty different ways.
 */

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * The access token lives in memory only.
 *
 * Not localStorage: anything script can read, an XSS bug can exfiltrate. The
 * refresh token is an httpOnly cookie the browser sends and script never sees,
 * so a page reload recovers the session without the access token ever having
 * been readable.
 */
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True when the server declined the credentials rather than failing. */
  get isAuthFailure(): boolean {
    return this.status === 401;
  }
}

export class OfflineError extends Error {
  constructor() {
    // frontend.md §A1 specifies this wording. Distinguishing "you are offline"
    // from "those credentials are wrong" matters: one is the user's fault and
    // one is not, and telling someone their password is wrong when the wifi
    // dropped sends them to reset a password that was fine.
    super("You're offline. Sign-in needs a connection.");
    this.name = "OfflineError";
  }
}

/**
 * The request never completed, so there is no status to report.
 *
 * `fetch` rejects with a bare TypeError for a refused connection, a DNS
 * failure and a blocked CORS preflight alike — the browser deliberately
 * withholds the detail from script. Reporting "something went wrong" for all
 * three is what made a missing CORS header take a browser session to find,
 * when the message could have pointed at the API instead.
 */
export class NetworkError extends Error {
  constructor() {
    super("Could not reach the server. Check it is running, then try again.");
    this.name = "NetworkError";
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  /** Internal. Prevents a refresh loop when the refresh call itself 401s. */
  retryOnUnauthorised?: boolean;
};

async function raw(path: string, options: RequestOptions = {}): Promise<Response> {
  const { method = "GET", body, signal } = options;

  if (typeof navigator !== "undefined" && !navigator.onLine) {
    throw new OfflineError();
  }

  // Built up rather than declared with `undefined` members: under
  // exactOptionalPropertyTypes, passing `body: undefined` is not the same as
  // omitting `body`, and fetch treats them differently for GET.
  const init: RequestInit = {
    method,
    // Sends the httpOnly refresh cookie.
    credentials: "include",
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  };
  if (body !== undefined) init.body = JSON.stringify(body);
  if (signal !== undefined) init.signal = signal;

  try {
    return await fetch(`${BASE}${path}`, init);
  } catch (caught) {
    // An AbortError is the caller cancelling on purpose, not a failure.
    if (caught instanceof DOMException && caught.name === "AbortError") throw caught;
    throw new NetworkError();
  }
}

async function toError(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const parsed = (await response.json()) as { detail?: unknown };
    if (typeof parsed.detail === "string") detail = parsed.detail;
  } catch {
    // A non-JSON error body is not itself worth reporting; the status is.
  }
  return new ApiError(response.status, detail);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { retryOnUnauthorised = true, ...rest } = options;
  let response = await raw(path, rest);

  // A 401 on a normal call usually means the 15-minute access token expired.
  // Try once to refresh, silently — a marker 40 minutes into a script should
  // not be thrown back to sign-in for a token they never knew existed.
  if (response.status === 401 && retryOnUnauthorised && path !== "/auth/refresh") {
    const refreshed = await tryRefresh();
    if (refreshed) {
      response = await raw(path, rest);
    }
  }

  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type Identity = {
  user_id: string;
  tenant_id: string;
  email: string;
  role: "ADMIN" | "LECTURER";
};

export async function login(
  email: string,
  password: string,
  rememberMe: boolean,
): Promise<Identity> {
  const pair = await request<TokenPair>("/auth/login", {
    method: "POST",
    body: { email, password, remember_me: rememberMe },
    retryOnUnauthorised: false,
  });
  setAccessToken(pair.access_token);
  return await request<Identity>("/auth/me");
}

/** Returns true when a new access token was obtained. */
export async function tryRefresh(): Promise<boolean> {
  try {
    const pair = await request<TokenPair>("/auth/refresh", {
      method: "POST",
      // The cookie carries it; the body is required by the endpoint shape.
      body: { refresh_token: "" },
      retryOnUnauthorised: false,
    });
    setAccessToken(pair.access_token);
    return true;
  } catch {
    setAccessToken(null);
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await request<void>("/auth/logout", { method: "POST", retryOnUnauthorised: false });
  } finally {
    // Cleared even if the request failed. Leaving a token in memory after the
    // user asked to leave is the wrong way to fail.
    setAccessToken(null);
  }
}

export async function me(): Promise<Identity> {
  return await request<Identity>("/auth/me");
}
