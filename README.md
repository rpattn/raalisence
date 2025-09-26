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


## Docker 

### Postgres

Build: `docker build -t your-registry/raalisence:pgx .`

Run: `docker run --rm -p 8080:8080 \
  -e RAAL_DB_DRIVER=pgx \
  -e RAAL_DB_DSN="postgres://postgres:postgres@host.docker.internal:5432/raalisence?sslmode=disable" \
  -e RAAL_SERVER_ADMIN_API_KEY="dev-admin-key" \
  -e RAAL_SIGNING_PRIVATE_KEY_PEM="$(cat priv.pem)" \
  -e RAAL_SIGNING_PUBLIC_KEY_PEM="$(cat pub.pem)" \
  your-registry/raalisence:pgx`


### SQLite

Build: `docker build -t your-registry/raalisence:sqlite .`
Run: `docker run --rm -p 8080:8080 \
  -v "$PWD/data:/data" \
  -e RAAL_DB_DRIVER=sqlite3 \
  -e RAAL_DB_PATH=/data/raalisence.db \
  -e RAAL_SERVER_ADMIN_API_KEY="dev-admin-key" \
  -e RAAL_SIGNING_PRIVATE_KEY_PEM="$(cat priv.pem)" \
  -e RAAL_SIGNING_PUBLIC_KEY_PEM="$(cat pub.pem)" \
  your-registry/raalisence:sqlite`




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
│  ├─ dev_db_up.sh
│  ├─ dev_db_down.sh
│  ├─ gen.sh
│  ├─ run.sh
│  └─ test.sh
├─ deploy/gke/
│  ├─ 00-configmap-migrations.yaml
│  ├─ 01-pvc.yaml
│  ├─ 02-secret.sample.yaml
│  ├─ 03-deployment.yaml
│  └─ 04-service.yaml
├─ internal/crypto/sign_test.go
└─ internal/handlers/license_test.go