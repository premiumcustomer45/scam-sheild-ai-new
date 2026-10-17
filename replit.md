# ScamShield AI

An educational phishing and scam assessment app that analyzes URL strings and message text without visiting submitted links.

## Run & Operate

- `pnpm --filter @workspace/scamshield-ai run dev` — run the React + Vite app
- `pnpm --filter @workspace/api-server run dev` — run the Express API
- `cd ml-service && uv sync --all-groups` — install the FastAPI/model dependencies
- `cd ml-service && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` — run the private ML API
- `cd ml-service && uv run python training/download_datasets.py` — download official UCI training data
- `cd ml-service && uv run python training/train_url_model.py && uv run python training/train_text_model.py` — train both models
- `cd ml-service && uv run pytest` — run ML tests
- `pnpm run typecheck` — full typecheck across all packages
- `PORT=3000 BASE_PATH=/ pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL`, `SESSION_SECRET`; optional `FRONTEND_URL`, `ML_SERVICE_URL`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `artifacts/scamshield-ai` — React + Vite product UI
- `artifacts/api-server` — Express API, auth, scans, analytics, feedback
- `ml-service` — FastAPI inference, training scripts, tests, model artifacts
- `lib/api-spec/openapi.yaml` — source of truth for application API contracts
- `lib/db/src/schema/` — PostgreSQL persistence schema
- `docs/` — architecture, API, datasets, evaluation, security, deployment, college notes

## Architecture decisions

- PostgreSQL is used for scan/account persistence because no MongoDB URI was supplied; do not claim MongoDB is connected.
- URL scanning is lexical only: never fetch, resolve, or render a submitted URL.
- The text model is trained on UCI spam-versus-ham data; it is not a phishing-labeled model.
- Model scores are not calibrated probabilities; `model_probability` remains null.
- Guest scans are not persisted; history and analytics are scoped to the authenticated user.

## Product

Users can assess URLs and messages, review evidence and limitations, and sign in to keep their own scan history, feedback, and dashboard analytics.

## User preferences

Do not store raw message bodies or original URL paths, user info, query strings, or fragments in scan history.

## Gotchas

The ML service refuses to start unless both trained model files are present under `ml-service/models/`; run both training scripts first.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
