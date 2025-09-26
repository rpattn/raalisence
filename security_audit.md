# Security Audit and Recommendations for raalisence

## Overview
raalisence is a Go-based licensing server that issues, validates, revokes, and tracks heartbeats for license keys stored in PostgreSQL or SQLite. The HTTP API is served directly by the Go standard library with middleware for logging, request IDs, and rate limiting. Administrative operations (issuing/revoking licenses) are guarded by a single shared admin API key. Clients can also interact with a bundled static admin panel for manual testing and operations.

## Summary of Key Findings
| ID | Severity | Title |
| --- | --- | --- |
| H1 | High | Default deployment lacks transport encryption for HTTP and database traffic |
| H2 | High | Bearer auth middleware accepts malformed headers and relies on non-constant-time comparisons |
| M1 | Medium | Administrative UI persists long-lived admin token in localStorage |
| M2 | Medium | JSON handlers accept unbounded payloads allowing request-body DoS |
| M3 | Medium | Detailed database errors leaked to clients |

## Detailed Findings

### H1. Default deployment lacks transport encryption for HTTP and database traffic - SOLVED
**Description.** The server exclusively uses `http.ListenAndServe` without TLS, and the default PostgreSQL DSN disables SSL (`sslmode=disable`). This configuration leaves both the HTTP control plane and database connections in plaintext unless operators add their own reverse proxy or change defaults.【F:cmd/raalisence/main.go†L63-L76】【F:internal/config/config.go†L54-L67】

**Impact.** An attacker with network visibility can steal the admin key or modify license traffic, resulting in full compromise of license issuance and revocation. Database credentials are also sent without encryption under the default configuration.

**Solution** Serve behind a TLS Proxy / TLS load balanacer 

### H2. Bearer auth middleware accepts malformed headers and relies on non-constant-time comparisons
**Description.** Administrative endpoints rely on a single shared API key compared via standard string equality, and the middleware slices off the first seven bytes without confirming they equal `Bearer `. Any header with at least seven characters can pass if the trailing substring matches the admin key, effectively bypassing the Bearer scheme requirement.【F:internal/middleware/logging.go†L49-L58】【F:internal/config/config.go†L69-L71】 Go's native string comparison is not constant time, leaking partial prefix matches that an attacker can exploit to incrementally brute-force the shared secret.

**Impact.** Attackers can iteratively guess the admin key using timing differences or by brute-forcing against the rate-limited endpoint; compromise of the shared key cannot be scoped to a single user. There is no concept of key rotation or per-user audit trails.

**Recommendations.**
* Replace the shared key with a stronger authentication mechanism (e.g., OAuth2 client credentials, mTLS, or at minimum hashed API keys stored and compared in constant time).
* Harden the middleware by validating the `Authorization` prefix explicitly and using `subtle.ConstantTimeCompare` to avoid timing side channels.
* Implement alerting and lockouts on repeated failed admin authentication attempts.

### M1. Administrative UI persists long-lived admin token in localStorage
**Description.** The bundled admin panel stores the administrator bearer token and base URL in `localStorage`, where it persists across browser sessions.【F:static/admin.html†L146-L154】 Any XSS vulnerability on the same origin would expose the key, and shared machines could leak the stored credentials.

**Impact.** Theft of the stored admin key yields immediate compromise of the licensing backend. Persistence beyond the active session increases the window of opportunity for attackers.

**Recommendations.**
* Avoid persisting the admin token; keep it in memory and prompt administrators each session.
* If persistence is required, scope the UI to dedicated administrative origins protected by MFA and HTTP-only storage (e.g., secure cookies with `SameSite=Strict`).
* Consider removing the admin panel from production builds or requiring additional authentication before granting access.

### M2. JSON handlers accept unbounded payloads allowing request-body DoS
**Description.** All JSON handlers decode the request body directly without wrapping it in `http.MaxBytesReader` or otherwise bounding size, allowing attackers to stream arbitrarily large bodies and exhaust memory or tie up goroutines.【F:internal/handlers/lisence.go†L51-L111】【F:internal/handlers/lisence.go†L121-L143】【F:internal/handlers/lisence.go†L145-L214】【F:internal/handlers/lisence.go†L217-L245】

**Impact.** A single client can send oversized bodies to degrade availability, bypassing the lightweight rate limiter because the request is only rejected after the server has already read and processed the large payload.

**Recommendations.**
* Wrap each handler with `http.MaxBytesReader` (or equivalent middleware) to cap request bodies to the expected size (e.g., a few kilobytes).
* Reject requests exceeding the limit with 413 responses and log the event for monitoring.

### M3. Detailed database errors leaked to clients
**Description.** When database operations fail, handlers propagate raw error messages directly to HTTP responses.【F:internal/handlers/lisence.go†L73-L76】【F:internal/handlers/lisence.go†L131-L138】【F:internal/handlers/lisence.go†L175-L198】【F:internal/handlers/lisence.go†L232-L240】 These messages may expose internal SQL, table names, or connection details.

**Impact.** Information leakage aids attackers in crafting targeted exploits (e.g., SQL injection) and reveals schema details that should remain internal.

**Recommendations.**
* Replace direct error exposure with generic responses (e.g., “internal server error”) while logging the detailed error server-side.
* Ensure logs are protected and monitored for repeated failure patterns.

## Additional Hardening Suggestions
* Enforce stricter JSON validation (`DisallowUnknownFields`, input normalization) to reduce accidental schema drift.
* Expand security logging to include admin actions (issue/revoke) for auditing and anomaly detection.【F:internal/middleware/logging.go†L32-L46】
* Document required rate limits and consider persistent storage for limiter state to survive restarts if abuse is a concern.【F:internal/middleware/ratelimit.go†L81-L127】
