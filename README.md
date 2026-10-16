# ScamShield AI

ScamShield AI is an educational web app for assessing suspicious URLs and message text. It gives a model-led risk signal and concrete supporting indicators; it does not guarantee safety and never opens the submitted URL.

## Current implementation

- React + Vite interface with dashboard, URL/text/combined scanner, saved history, scan details, feedback, account screens, and privacy/methodology information.
- Express API for account sessions, scan orchestration, history, analytics, and feedback.
- FastAPI inference service with separate URL and message models, plus a combined assessment policy.
- Real model artifacts trained from the official UCI PhiUSIIL Phishing URL dataset and the UCI SMS Spam Collection.
- Replit's provisioned PostgreSQL is used for persistence. MongoDB was requested in the source prompt, but no MongoDB URI was supplied; the existing database is used instead of pretending MongoDB is connected.

## Local setup

### 1. Install the workspace dependencies

```bash
pnpm install
```

The Replit workspace already provides its development database. For another environment, set `DATABASE_URL` to a PostgreSQL database and `SESSION_SECRET` to a random secret of at least 32 characters. See `.env.example`; never commit actual secrets.

### 2. Install the Python ML service dependencies and data

```bash
cd ml-service
uv sync --all-groups
uv run python training/download_datasets.py
uv run python training/inspect_url_dataset.py
uv run python training/train_url_model.py
uv run python training/train_text_model.py
uv run pytest
```

The downloaded datasets and evaluation reports are excluded from Git and deployment. The trained `.joblib` artifacts under `ml-service/models/` are required at runtime and are kept with the project.

### 3. Create the database tables

From the workspace root:

```bash
pnpm --filter @workspace/db run push
```

### 4. Run the three services

Start each process in its own terminal:

```bash
pnpm --filter @workspace/api-server run dev
```

```bash
cd ml-service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
pnpm --filter @workspace/scamshield-ai run dev
```

The Express API is the browser-facing API at `/api`. The ML service listens on port 8000 and should remain private; Express calls it at `ML_SERVICE_URL` (default `http://127.0.0.1:8000`).

## Verification

```bash
pnpm run typecheck
cd ml-service && uv run pytest
```

Training commands write held-out metrics to `ml-service/training/reports/`. See `docs/model-evaluation.md` for their interpretation and limitations. Do not quote metrics until those reports exist for the model artifacts being used.

## Important limitations

- PhiUSIIL contains both URL and webpage-derived fields; this project trains only from URL strings and computes matching lexical features at inference. It does not visit URLs or inspect page content.
- The text dataset is spam-versus-ham, not phishing-versus-legitimate. The UI and API preserve that limitation.
- Risk scores are model signal scores from 0 to 100, not calibrated maliciousness probabilities. `model_probability` is always null.
- The combined policy is conservative and transparent but has not been validated on a dedicated combined-message dataset.
- Guest scans are not stored. Signed-in users can retrieve and delete their own history.
- This educational tool is not a substitute for security software or independent verification.

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Datasets and labels](docs/dataset.md)
- [Model evaluation](docs/model-evaluation.md)
- [Security and privacy](docs/security-and-privacy.md)
- [Deployment](docs/deployment.md)
- [College submission and viva notes](docs/college-submission.md)
