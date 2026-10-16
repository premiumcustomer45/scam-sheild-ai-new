# API reference

The public application API is mounted at `/api`. The source of truth is `lib/api-spec/openapi.yaml`; generated React Query hooks and Zod validators are in `lib/api-client-react` and `lib/api-zod`.

## Application API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Express process health |
| GET | `/api/ready` | Database and ML readiness |
| POST | `/api/auth/register` | Create an account and set session cookie |
| POST | `/api/auth/login` | Sign in and set session cookie |
| POST | `/api/auth/logout` | Clear session cookie |
| GET | `/api/auth/me` | Get the signed-in user or `{ "user": null }` |
| POST | `/api/scans/url` | Assess one URL without fetching it |
| POST | `/api/scans/text` | Assess message text |
| POST | `/api/scans/combined` | Assess message text and up to ten extracted URLs |
| GET | `/api/scans?page=1&limit=20` | Paginated history for the signed-in user |
| GET | `/api/scans/{id}` | Get an owned scan |
| DELETE | `/api/scans/{id}` | Delete an owned scan |
| GET | `/api/dashboard/stats?days=30` | Current user's counts and daily trend |
| POST | `/api/feedback` | Record feedback for an owned scan |

All scan input is validated server-side. A successful scan response includes a verdict, 0–100 model signal score, supporting indicators, recommendations, model version, limitations, and any URL assessments. The optional model probability is not exposed because calibration has not been established.

Unauthenticated scanning is allowed, but those results are not persisted. History and analytics are user-scoped.

## Private ML API

The FastAPI service listens on port 8000 locally and is not meant to be exposed publicly.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Process health |
| GET | `/ready` | Model-loaded readiness |
| POST | `/predict/url` | URL model inference |
| POST | `/predict/text` | Text model inference |
| POST | `/predict/combined` | Text and extracted URL inference |

Example URL request:

```json
{ "url": "https://example.com/account" }
```

Example response shape:

```json
{
  "verdict": "uncertain",
  "riskScore": 42,
  "model_probability": null,
  "indicators": [],
  "recommendations": [],
  "model_version": "model-version-from-artifact",
  "limitations": [],
  "urls": []
}
```

The example is a schema illustration, not a prediction. The running service returns its actual fitted-model output.
