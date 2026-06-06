// Same-origin API proxy. The browser calls /api/v1/* on THIS app's domain; this
// route handler forwards the request to the real backend at RUNTIME. This removes
// the need to bake a cross-origin API URL at build time and sidesteps CORS entirely.
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Real backend on Render. Overridable via BACKEND_URL (e.g. http://api:8000 locally).
const DEFAULT_BACKEND = "https://jobpilot-api-gpc1.onrender.com";

function backendBase(): string {
  // Only honor BACKEND_URL if it's a FULL http(s) URL (e.g. http://api:8000 locally).
  // Render's service-linking sets it to a bare hostname like "jobpilot-api-gpc1"
  // (no domain) which is NOT publicly resolvable — so we ignore that and use the
  // full public URL instead.
  const env = (process.env.BACKEND_URL || "").trim();
  if (/^https?:\/\//.test(env)) return env.replace(/\/+$/, "");
  return DEFAULT_BACKEND;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const base = backendBase();
  const target = `${base}/api/v1/${path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  headers.delete("accept-encoding"); // avoid upstream gzip we then re-emit incorrectly

  const init: RequestInit = { method: req.method, headers, redirect: "manual" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = Buffer.from(await req.arrayBuffer()); // Buffer is reusable across retries
  }

  // Retry to ride through backend cold-starts (503) and transient network errors.
  let lastErr = "";
  for (let attempt = 1; attempt <= 6; attempt++) {
    try {
      const resp = await fetch(target, init);
      if (resp.status === 503 || resp.status === 502) {
        lastErr = `upstream ${resp.status}`;
        await sleep(5000);
        continue;
      }
      const body = await resp.arrayBuffer();
      const out = new Headers();
      for (const h of ["content-type", "content-disposition"]) {
        const v = resp.headers.get(h);
        if (v) out.set(h, v);
      }
      return new Response(body, { status: resp.status, headers: out });
    } catch (e) {
      lastErr = e instanceof Error ? `${e.name}: ${e.message}` : String(e);
      await sleep(3000);
    }
  }

  // All attempts failed — surface the real reason and the target for diagnosis.
  return new Response(
    JSON.stringify({
      error: {
        code: "upstream_unreachable",
        message: "Backend unreachable after retries. Please retry in ~30s.",
        detail: lastErr,
        target,
      },
    }),
    { status: 502, headers: { "content-type": "application/json" } },
  );
}

type Ctx = { params: Promise<{ path: string[] }> };
const handler = async (req: NextRequest, ctx: Ctx) => proxy(req, (await ctx.params).path);

export {
  handler as GET,
  handler as POST,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
};
