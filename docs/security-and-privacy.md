# Security and privacy

- Submitted URLs are parsed and classified as strings only. The app never visits URLs, resolves DNS, follows redirects, or executes remote content.
- The browser sends requests to Express, not directly to the ML service.
- Express caps JSON bodies, validates requests with generated Zod schemas, and applies rate limits to scanning and login routes.
- Helmet sets security headers. CORS accepts the current same-origin host and explicitly configured `FRONTEND_URL` origins only.
- Passwords are bcrypt-hashed. Sessions are signed with `SESSION_SECRET` and stored in `HttpOnly`, `SameSite=Lax` cookies; `Secure` is enabled in production.
- API request logs exclude query strings and bodies. Error responses do not expose stack traces or environment values.
- Message bodies are not persisted. Saved URL previews omit paths (which can carry reset tokens), user information, query strings, and fragments. Full model input is sent only to the local ML service to produce the requested prediction.
- Scan history and delete operations are filtered by owner ID. Users cannot retrieve or delete another user's scans.
- Guest scans are not saved. Signed-in users can delete individual scans; account retention/deletion policy for a public production launch still needs product/legal review.
- The ML endpoint is configured for a private local service. If hosted separately, place it behind network restrictions and service authentication before public deployment.

This is an educational project and does not provide legal, security, or accuracy guarantees.
