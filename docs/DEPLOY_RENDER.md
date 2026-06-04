# Deploy JobPilot AI to the web (Render)

This uses the [`render.yaml`](../render.yaml) blueprint to stand up the database, cache,
backend API, and frontend. **Free tier** throughout. Total time: ~15 minutes, mostly
waiting for builds.

> The only steps a human must do are the account login and two URL paste-backs — Render
> can't be driven headlessly without your credentials. Everything else is in the repo.

---

## 1. Create a Render account
Go to <https://render.com> → **Sign up with GitHub** (use the JAGHDHEEP account).

## 2. Launch the blueprint
1. Dashboard → **New +** → **Blueprint**.
2. Connect the repo **`JAGHDHEEP/jobpilot-ai`** (authorize Render to read it).
3. Render detects `render.yaml` and lists 4 resources: `jobpilot-db`, `jobpilot-redis`,
   `jobpilot-api`, `jobpilot-web`.
4. Click **Apply**. Render builds the two Docker images and provisions Postgres + Redis.
   (First Docker build takes ~5–8 min each.)

## 3. Grab the two public URLs
When the services go live you'll get URLs like:
- API: `https://jobpilot-api.onrender.com`
- Web: `https://jobpilot-web.onrender.com`

(Your exact subdomains may have a random suffix — copy the real ones from the dashboard.)

## 4. Tell the frontend where the API lives (the ONE manual env var)
The backend now auto-allows any origin (`CORS_ALLOW_ALL=true`) and auto-seeds itself, so
the only thing left is pointing the frontend at the API. Open
**jobpilot-web → Environment** → set:
```
NEXT_PUBLIC_API_URL = https://jobpilot-api.onrender.com/api/v1
```
(use your real api URL). Save → **Manual Deploy → Clear build cache & deploy** — this value
is baked in at build time, so the frontend must rebuild once.

## 5. Seeding — automatic ✅
Nothing to do. On first boot the API creates all tables and seeds the demo admin
(`admin@jobpilot.ai` / `admin12345`) plus sample jobs automatically (`AUTO_SEED=true`).
To disable later, set `AUTO_SEED=false` on jobpilot-api.

## 6. Use it
Open the web URL → register or log in with the seeded admin → upload a resume on Profile →
**Search → Ingest jobs → Match me**. Done — it's live on the internet.

---

## Turn on real AI (optional)
In **jobpilot-api → Environment**:
```
AI_PROVIDER = anthropic           # or openai
ANTHROPIC_API_KEY = sk-ant-...     # or OPENAI_API_KEY
```
Save → redeploy. Until then it runs in offline `mock` mode (still fully functional, just
templated text instead of real LLM output).

## Known free-tier limits
- **Cold starts:** free web services sleep after ~15 min idle; first request then takes
  ~30–60s to wake. Normal for free tier.
- **No background scheduler:** Celery worker/beat aren't deployed (paid on Render), so
  daily auto-recommendations don't run on a timer — use the **Refresh recommendations**
  button / `/jobs/recommendations/build` endpoint instead.
- **Vector store:** runs in-memory (resets on restart). For persistent semantic search,
  add a Chroma service or swap to pgvector (interface in `app/ai/vector_store.py`).
- **Free Postgres** expires after 90 days on Render — upgrade or recreate before then.

## Alternative: one-VM deploy
On any Linux box with Docker: `git clone`, `cp .env.example .env` (set `SECRET_KEY`),
`docker compose up -d --build`. This runs the *full* stack including worker/beat/Chroma/
Nginx. See [DEPLOYMENT.md](DEPLOYMENT.md).
