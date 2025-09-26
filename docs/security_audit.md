# Security Audit and Recommendations for raalisence

## Overview
raalisence is a Go-based licensing server that issues, validates, revokes, and tracks heartbeats for license keys stored in PostgreSQL or SQLite. The HTTP API is served directly by the Go standard library with middleware for logging, request IDs, and rate limiting. Administrative operations (issuing/revoking licenses) are guarded by a single shared admin API key. Clients can also interact with a bundled static admin panel for manual testing and operations.

## Summary of Key Findings
| ID | Severity | Title |
| --- | --- | --- |
| H1 | High | Default deployment lacks transport encryption for HTTP and database traffic |
| H2 | High | Bearer auth middleware accepts malformed headers and relies on non-constant-time comparisons - SOLVED |
| M1 | Medium | Administrative UI persists long-lived admin token in localStorage - SOLVED |
| M2 | Medium | JSON handlers accept unbounded payloads allowing request-body DoS - SOLVED |
| M3 | Medium | Detailed database errors leaked to clients - SOLVED |

## Detailed Findings

### H1. Default deployment lacks transport encryption for HTTP and database traffic - SOLVED
**Description.** The server exclusively uses `http.ListenAndServe` without TLS, and the default PostgreSQL DSN disables SSL (`sslmode=disable`). This configuration leaves both the HTTP control plane and database connections in plaintext unless operators add their own reverse proxy or change defaults.【F:cmd/raalisence/main.go†L63-L76】【F:internal/config/config.go†L54-L67】

**Impact.** An attacker with network visibility can steal the admin key or modify license traffic, resulting in full compromise of license issuance and revocation. Database credentials are also sent without encryption under the default configuration.

**Solution** Serve behind a TLS Proxy / TLS load balanacer 

### H2. Bearer auth middleware accepts malformed headers and relies on non-constant-time comparisons - SOLVED
**Description.** Administrative endpoints rely on a single shared API key compared via standard string equality, and the middleware slices off the first seven bytes without confirming they equal `Bearer `. Any header with at least seven characters can pass if the trailing substring matches the admin key, effectively bypassing the Bearer scheme requirement.【F:internal/middleware/logging.go†L49-L58】【F:internal/config/config.go†L69-L71】 Go's native string comparison is not constant time, leaking partial prefix matches that an attacker can exploit to incrementally brute-force the shared secret.

**Impact.** Attackers can iteratively guess the admin key using timing differences or by brute-forcing against the rate-limited endpoint; compromise of the shared key cannot be scoped to a single user. There is no concept of key rotation or per-user audit trails.

**Fix.** The admin middleware now verifies the `Authorization` header starts with the `Bearer ` prefix and rejects requests that omit it. The server key comparison uses configured bcrypt hashes to validate presented tokens, preventing malformed headers from bypassing the scheme and resisting brute-force timing attacks. Operators can rotate credentials by supplying multiple hashes without exposing plaintext secrets in configuration.【F:internal/middleware/admin_auth.go†L44-L70】【F:internal/config/config.go†L57-L92】【F:scripts/hash-admin-key.go†L1-L29】

**Follow-up status.**
* Replace the shared key with a stronger authentication mechanism (e.g., OAuth2 client credentials or hashed API keys) – **addressed** by switching configuration to store bcrypt-hashed admin tokens and allowing multiple hashes for rotation.【F:internal/config/config.go†L17-L45】【F:internal/config/config.go†L57-L92】【F:config.example.yaml†L1-L18】
* Implement alerting and lockouts on repeated failed admin authentication attempts – **addressed** by tracking failures per client IP and emitting a high-signal log once the threshold is exceeded within the observation window.【F:internal/middleware/admin_auth.go†L14-L43】【F:internal/middleware/admin_auth.go†L44-L70】
* Because raalisence always sits behind a terminating TLS proxy, adding in-process mTLS would duplicate trust decisions already enforced at the proxy. Operators should instead restrict direct access to the backend port and rely on the proxy’s TLS policy (including optional client cert validation) for transport authenticity – **no further action required**.

### M1. Administrative UI persists long-lived admin token in localStorage - SOLVED
**Description.** The bundled admin panel stores the administrator bearer token and base URL in `localStorage`, where it persists across browser sessions.【F:static/admin.html†L146-L154】 Any XSS vulnerability on the same origin would expose the key, and shared machines could leak the stored credentials.

**Impact.** Theft of the stored admin key yields immediate compromise of the licensing backend. Persistence beyond the active session increases the window of opportunity for attackers.

**Recommendations.**
* Avoid persisting the admin token; keep it in memory and prompt administrators each session.
* If persistence is required, scope the UI to dedicated administrative origins protected by MFA and HTTP-only storage (e.g., secure cookies with `SameSite=Strict`).
* Consider removing the admin panel from production builds or requiring additional authentication before granting access.

**Fix.** The admin panel now only persists the base URL; the bearer token field is cleared on load and never written to storage, forcing administrators to enter credentials each session. The UI also explains that the token remains in memory only, reducing exposure from shared machines or XSS persistence.【F:static/admin.html†L65-L102】

**Follow-up status.** No further action required.

### M2. JSON handlers accept unbounded payloads allowing request-body DoS - SOLVED
**Description.** All JSON handlers decode the request body directly without wrapping it in `http.MaxBytesReader` or otherwise bounding size, allowing attackers to stream arbitrarily large bodies and exhaust memory or tie up goroutines.【F:internal/handlers/lisence.go†L51-L111】【F:internal/handlers/lisence.go†L121-L143】【F:internal/handlers/lisence.go†L145-L214】【F:internal/handlers/lisence.go†L217-L245】

**Impact.** A single client can send oversized bodies to degrade availability, bypassing the lightweight rate limiter because the request is only rejected after the server has already read and processed the large payload.

**Fix.** A shared `decodeJSON` helper now wraps every JSON handler with `http.MaxBytesReader`, capping request bodies at 64KiB before decoding. Oversized payloads are rejected with 413 responses and an audit log entry that captures the request path and remote address for monitoring. The helper also enforces single-object payloads to avoid request smuggling through concatenated JSON objects.【F:internal/handlers/lisence.go†L13-L17】【F:internal/handlers/lisence.go†L39-L43】【F:internal/handlers/lisence.go†L249-L283】

**Follow-up status.** Consider tuning the limit per-endpoint if future features require larger payloads; otherwise no additional action is required.

### M3. Detailed database errors leaked to clients - SOLVED
**Description.** When database operations fail, handlers propagate raw error messages directly to HTTP responses.【F:internal/handlers/lisence.go†L73-L76】【F:internal/handlers/lisence.go†L131-L138】【F:internal/handlers/lisence.go†L175-L198】【F:internal/handlers/lisence.go†L232-L240】 These messages may expose internal SQL, table names, or connection details.

**Impact.** Information leakage aids attackers in crafting targeted exploits (e.g., SQL injection) and reveals schema details that should remain internal.

**Recommendations.**
* Replace direct error exposure with generic responses (e.g., “internal server error”) while logging the detailed error server-side.
* Ensure logs are protected and monitored for repeated failure patterns.

**Fix.** Handlers centralize error handling through an `internalError` helper that logs database and signing failures with operation context while returning a generic 500 response to clients, preventing leakage of SQL details or key material issues.【F:internal/handlers/lisence.go†L7-L158】【F:internal/handlers/lisence.go†L214-L232】

**Follow-up status.** Monitor server logs for repeated failures and ensure log storage inherits existing access controls.

## Additional Hardening Suggestions
* Enforce stricter JSON validation (`DisallowUnknownFields`, input normalization) to reduce accidental schema drift.
* Expand security logging to include admin actions (issue/revoke) for auditing and anomaly detection.【F:internal/middleware/logging.go†L32-L46】
* Document required rate limits and consider persistent storage for limiter state to survive restarts if abuse is a concern.【F:internal/middleware/ratelimit.go†L81-L127】
