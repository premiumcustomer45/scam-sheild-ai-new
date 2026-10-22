# Deployment

## Vercel (recommended)

The repository deploys as **two Vercel projects** from the same Git repo:

| Project | Root Directory | What it serves |
| --- | --- | --- |
| `scamshield-ml` | `ml-service` | FastAPI model inference (Python serverless function) |
| `scamshield` | `.` (repo root) | React frontend + Express API at `/api` (Node.js function) |

The root `vercel.json` runs `scripts/vercel-build.mjs`, which writes Vercel's Build Output API layout: the Vite build as static files and the Express app bundled into one function at `/api`. Frontend and API share an origin, so the session cookie needs no CORS setup.

### 1. Deploy the ML service

1. Vercel → **Add New Project** → import the repo → set **Root Directory** to `ml-service`.
2. Environment variable: `ML_SERVICE_TOKEN` = a long random string.
3. Deploy, then open `https://<ml-project>.vercel.app/health` — it should return `{"status":"ok"}`.

### 2. Create the database

In the main project's **Storage** tab, add a Neon (Postgres) database and connect it to the project. This sets `DATABASE_URL`. Any hosted PostgreSQL URL works too.

### 3. Deploy the web app + API

1. **Add New Project** → same repo → **Root Directory** `.` (leave framework as "Other"; `vercel.json` sets the commands).
2. Environment variables:
   - `DATABASE_URL` — set by the Neon integration, or paste your own
   - `SESSION_SECRET` — random string, at least 32 characters
   - `ML_SERVICE_URL` — `https://<ml-project>.vercel.app`
   - `ML_SERVICE_TOKEN` — same value as on the ML project
3. Deploy. The build pushes the Drizzle schema automatically when `DATABASE_URL` is available (set `SKIP_DB_PUSH=1` to disable). If the log shows a push warning, run it once locally: `DATABASE_URL=... pnpm --filter @workspace/db run push`.
4. Check `https://<app>.vercel.app/api/health` and `/api/ready`, then register an account and run a scan.

The first scan after a period of inactivity can take a few seconds while the ML function cold-starts; the API waits up to `ML_SERVICE_TIMEOUT_MS` (default 25 s).

## Other hosts

## Services and variables

| Service | Build/run | Required configuration |
| --- | --- | --- |
| React + Vite | `PORT=3000 BASE_PATH=/ pnpm --filter @workspace/scamshield-ai run build` | Same-origin `/api` path |
| Express API | `pnpm --filter @workspace/api-server run build` then `pnpm --filter @workspace/api-server run start` | `DATABASE_URL`, `SESSION_SECRET`, `ML_SERVICE_URL`, `FRONTEND_URL`, `PORT` |
| FastAPI ML | `uv sync --all-groups` then `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `ml-service/` | model artifacts, `MODEL_DIR`, `PORT` |

The React app and Express API must share a browser origin for the session cookie, or the exact frontend origin must be added to `FRONTEND_URL`. Set production `SESSION_SECRET` through the host's secret manager; use a unique random value of at least 32 characters. Do not put credentials in `.env.example`, source control, or logs.

The local project uses Replit's provisioned PostgreSQL database. The source prompt specified MongoDB, but no MongoDB URI was supplied, so PostgreSQL is the documented implementation. A MongoDB migration is not included.

The Python model files `ml-service/models/url_model.joblib` and `text_model.joblib` must be present in the ML service image. Raw training datasets are not required at inference time and are excluded from deployments.

## Suggested deployment order

1. Provision PostgreSQL and apply the Drizzle schema using the documented database flow.
2. Train both ML models and ensure the `.joblib` files are included in the ML service image.
3. Deploy FastAPI privately; confirm `/health` and `/ready`.
4. Deploy Express with `ML_SERVICE_URL` set to the private FastAPI address; confirm `/api/health` and `/api/ready`.
5. Build and deploy the React frontend on the same public origin as `/api`.
6. Register an account, submit a scan, confirm it appears in history, and verify that signed-out callers cannot access that record.

Do not expose the ML service directly to browsers. If it must cross a public network boundary, add service-to-service authentication and network restrictions before publishing.

## Health checks and failure behavior

- `/api/health` checks that Express responds.
- `/api/ready` checks PostgreSQL and the ML service.
- FastAPI refuses startup if a required model artifact is missing or incompatible.
- Express reports a scanner-unavailable response when FastAPI is down; it does not return a fabricated fallback prediction.
