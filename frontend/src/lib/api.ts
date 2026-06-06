// Typed API client with automatic token refresh.
// Always call the backend through THIS app's own origin (/api/v1). A Next.js route
// handler (src/app/api/v1/[...path]/route.ts) proxies these to the real backend at
// runtime — so there is no cross-origin URL to configure, and no CORS.
const API_URL = "/api/v1";

export interface Tokens { access_token: string; refresh_token: string }

function getTokens(): Tokens | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("jp_tokens");
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export function setTokens(t: Tokens | null) {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem("jp_tokens", JSON.stringify(t));
  else localStorage.removeItem("jp_tokens");
}

class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function refresh(): Promise<boolean> {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return false;
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!res.ok) { setTokens(null); return false; }
  setTokens((await res.json()) as Tokens);
  return true;
}

export async function api<T = unknown>(
  path: string,
  opts: RequestInit & { auth?: boolean; retry?: boolean } = {},
): Promise<T> {
  const { auth = true, retry = true, headers, ...rest } = opts;
  const h = new Headers(headers);
  if (!h.has("Content-Type") && rest.body && !(rest.body instanceof FormData))
    h.set("Content-Type", "application/json");
  if (auth) {
    const tokens = getTokens();
    if (tokens) h.set("Authorization", `Bearer ${tokens.access_token}`);
  }

  const res = await fetch(`${API_URL}${path}`, { ...rest, headers: h });
  if (res.status === 401 && auth && retry && (await refresh()))
    return api<T>(path, { ...opts, retry: false });

  if (!res.ok) {
    let code = "error", message = res.statusText;
    try { const b = await res.json(); code = b.error?.code ?? code; message = b.error?.message ?? message; } catch { /* ignore */ }
    throw new ApiError(res.status, code, message);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  return (ct.includes("application/json") ? await res.json() : await res.blob()) as T;
}

export { ApiError, API_URL };
