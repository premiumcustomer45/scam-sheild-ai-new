# College submission notes

## Abstract

ScamShield AI is an educational web application for assessing potentially suspicious URLs and message text. It combines a lexical URL classifier with a TF-IDF SMS spam baseline, returns visible indicators and limitations, and supports account-scoped scan history. The scanner analyzes URL strings without visiting destinations. It communicates uncertainty and does not promise that a lower-risk result is safe.

## Problem statement and objectives

Unexpected links and messages can use urgency, account language, and misleading domain structures to pressure recipients. ScamShield AI aims to provide a repeatable educational assessment workflow: analyze URL text, analyze message text, identify embedded URLs, explain supporting signals, and make the limits of the model visible.

## Scope and existing limitations

The MVP covers URL-only lexical features, spam-versus-ham message classification, combined message/URL inspection, account sessions, history, feedback, and summary analytics. It does not inspect destination pages, use reputation feeds, block messages, or provide an assurance that a link is safe.

The text data source labels spam, not phishing. The combined decision policy has no dedicated combined-message evaluation set. Model output is not exposed as a calibrated probability.

## Architecture and data flow

See [architecture.md](architecture.md) for the service diagram, endpoints, database model, and combined-signal policy. The browser calls Express; Express calls private FastAPI; only signed-in results are stored in PostgreSQL.

## Dataset and methodology

See [dataset.md](dataset.md) for UCI sources, licenses, target mapping, feature filtering, citations, and setup. URL training compares Logistic Regression and Random Forest using only features derived by the live URL parser. Text training compares Logistic Regression and Multinomial Naive Bayes in a TF-IDF pipeline.

## Evaluation results

The fixed-seed held-out run selected Random Forest for the URL classifier and Logistic Regression + TF-IDF for text. URL test results on 31,453 records: precision 0.9991, recall 0.9913, F1 0.9952, PR-AUC 0.9975, Brier score 0.0041, confusion matrix `[[19994, 10], [100, 11349]]`. SMS spam-versus-ham results on 774 records: precision 0.9890, recall 0.9375, F1 0.9626, PR-AUC 0.9745, Brier score 0.0279, confusion matrix `[[677, 1], [6, 90]]`. These metrics describe only the chosen UCI test partitions; they are not real-world accuracy guarantees. Do not treat the SMS score as a phishing probability.

## Database, API, and implementation

The database contains users, scans, and feedback. See [api.md](api.md) for routes and request/response contracts. PostgreSQL is used because the requested MongoDB connection was not supplied; the source prompt's MongoDB stack is therefore not the implementation in this project.

## Testing

Run `pnpm run typecheck` and `cd ml-service && uv run pytest`. Tests cover URL parsing edge cases, feature contract, URL preview redaction, model-response shape, and combined evidence conflict. API integration, live deployment, and end-to-end account flows are not represented as passing unless separately run and recorded.

## Security, privacy, and future work

See [security-and-privacy.md](security-and-privacy.md). Future extensions may include a labeled phishing-message corpus, calibrated probabilities, a combined-message test set, account export/deletion policy, stronger multi-instance rate limiting, and private threat-intelligence checks with SSRF defenses.

## Viva questions

**Why not visit a submitted URL?** Visiting user-provided URLs can create server-side request forgery, redirect, DNS rebinding, and content execution risks. The MVP uses lexical features only.

**Why use a separate ML service?** It isolates Python model loading, feature extraction, and inference from Express's authentication, persistence, and public HTTP surface.

**Does the text model detect phishing?** No. Its UCI training labels distinguish SMS spam from ham. The result is presented as a spam-like signal, not a phishing verdict.

**Is a 75/100 risk score a 75% chance of fraud?** No. It is an uncalibrated model signal on a 0–100 product scale. The API returns `model_probability: null`.

**How are conflicts handled?** The system does not average model outputs. A high-risk URL is not diluted by message text; strong conflicting signals can produce `uncertain`.

**What are the main evaluation metrics?** Precision, recall, F1, confusion matrix, PR-AUC, and Brier score on a held-out test split. Actual values belong in the generated evaluation reports.
