# Deployment

No deployment has been performed or verified as part of this build. The following describes the configuration required for deployment; verify current hosting requirements before choosing providers.

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
