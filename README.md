# RAALisence — Hybrid License Server (Go)

This project provides a small, production-ready(ish) license server that supports a hybrid model:

Local signed license files (for offline validation)

Remote validation via the server (for revocation and live expiry checks)

It uses:

Go with the standard net/http router.

PostgreSQL for persistence via sqlc-generated code.

Viper for configuration (file first, fallback to environment variables).

Minimal dependencies, clear file layout, tests, and helper scripts.

## Quick start (dev)


```bash
# 1) start postgres and migrate
./scripts/dev_db_up.sh


# 2) generate sqlc code
./scripts/gen.sh


# 3) run the server (generates temp keys if missing)
./scripts/run.sh


raalisence/
├─ cmd/raalisence/main.go
├─ internal/config/config.go
├─ internal/server/server.go
├─ internal/handlers/health.go
├─ internal/handlers/license.go
├─ internal/middleware/logging.go
├─ internal/crypto/sign.go
├─ internal/db/migrations/0001_init.sql
├─ internal/db/queries/licenses.sql
├─ sqlc.yaml
├─ config.example.yaml
├─ Dockerfile
├─ docker-compose.yml
├─ README.md
├─ scripts/
│ ├─ dev_db_up.sh
│ ├─ dev_db_down.sh
│ ├─ gen.sh
│ ├─ run.sh
│ └─ test.sh
├─ internal/crypto/sign_test.go
└─ internal/handlers/license_test.go