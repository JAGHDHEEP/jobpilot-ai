// Same-origin API proxy. The browser calls /api/v1/* on THIS app's domain; this
// route handler forwards the request to the real backend at RUNTIME. This removes
// the need to bake a cross-origin API URL at build time and sidesteps CORS entirely.
//
// The backend address comes from BACKEND_URL (injected automatically by Render's
// service linking — see render.yaml). Falls back to localhost for local dev.
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Real backend on Render. Overridable via BACKEND_URL (e.g. http://api:8000 in
// local docker-compose), but defaults to the deployed API so no env var is required.
const DEFAULT_BACKEND = "https://jobpilot-api-gpc1.onrender.com";

function backendBase(): string {
  const b = process.env.BACKEND_URL || process.env.BACKEND_HOST || DEFAULT_BACKEND;
  return b.startsWith("http") ? b.replace(/\/+$/, "") : `https://${b}`;
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${backendBase()}/api/v1/${path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const init: RequestInit = { method: req.method, headers, redirect: "manual" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = Buffer.from(await req.arrayBuffer());
  }

  let resp: Response;
  try {
    resp = await fetch(target, init);
  } catch {
    return new Response(
      JSON.stringify({
        error: {
          code: "upstream_unreachable",
          message: "Backend is waking up or unreachable. Please retry in ~30s.",
        },
      }),
      { status: 503, headers: { "content-type": "application/json" } },
    );
  }

  const body = await resp.arrayBuffer();
  const out = new Headers();
  for (const h of ["content-type", "content-disposition"]) {
    const v = resp.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(body, { status: resp.status, headers: out });
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
