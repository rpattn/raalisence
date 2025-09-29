# RAALisence — Hybrid License Server (Go)

This project provides a small, production-ready(ish) license server that supports a hybrid model:

Local signed license files (for offline validation)

Remote validation via the server (for revocation and live expiry checks)

It uses:

Go with the standard net/http router.

PostgreSQL for persistence via sqlc-generated code.

Viper for configuration (file first, fallback to environment variables).

Minimal dependencies, clear file layout, tests, and helper scripts.

## How to use (v1)

All actions can be performed via the admin panel served from /

### issue lisence
pseudo code:

```
body: {Customer: "Acme", MachineID: "MID1", ExpiresAt: time.Now().Add(24 * time.Hour)}
req (http.MethodPost, "/api/v1/licenses/issue", body)
req.Header.Set("Authorization", "Bearer test-admin") #where test-admin is the admin key you set

if resp.Code != http.StatusOK {
  Fatalf("issue code=", resp.Body)
}

LicenseFile=rw.Body

if LicenseFile.LicenseKey == "" {
  Fatal("missing license key")
}
```

### validate lisence
pseudo code:

```
body: {LicenseKey: LicenseFile.LicenseKey, MachineID: "MID1"}
req (http.MethodPost, "/api/v1/licenses/validate", body)

if resp.Code != http.StatusOK {
  Fatalf("validate code=%d body=%s", resp.Code, resp.Body)
}
```


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

Run:

```bash
ADMIN_HASH="$(go run ./scripts/hash-admin-key.go dev-admin-key)"
docker run --rm -p 8080:8080 \
  -e RAAL_DB_DRIVER=pgx \
  -e RAAL_DB_DSN="postgres://postgres:postgres@host.docker.internal:5432/raalisence?sslmode=disable" \
  -e RAAL_SERVER_ADMIN_API_KEY_HASHES="$ADMIN_HASH" \
  -e RAAL_SIGNING_PRIVATE_KEY_PEM="$(cat priv.pem)" \
  -e RAAL_SIGNING_PUBLIC_KEY_PEM="$(cat pub.pem)" \
  your-registry/raalisence:pgx
```


### SQLite

Build: `docker build -t your-registry/raalisence:sqlite .`
Run:

```bash
ADMIN_HASH="$(go run ./scripts/hash-admin-key.go dev-admin-key)"
docker run --rm -p 8080:8080 \
  -v "$PWD/data:/data" \
  -e RAAL_DB_DRIVER=sqlite3 \
  -e RAAL_DB_PATH=/data/raalisence.db \
  -e RAAL_SERVER_ADMIN_API_KEY_HASHES="$ADMIN_HASH" \
  -e RAAL_SIGNING_PRIVATE_KEY_PEM="$(cat priv.pem)" \
  -e RAAL_SIGNING_PUBLIC_KEY_PEM="$(cat pub.pem)" \
  your-registry/raalisence:sqlite
```


### To Docker.io

`docker build -t docker.io/rpattn/raalisence:sqlite .`
`docker push docker.io/rpattn/raalisence:sqlite`

## Hosting

***Note: Serve the app behind a TLS proxy or similar to prevent leaking of api keys***

### SQLite 

- 1) Setup volume

e.g. with Koyeb `koyeb volume create raal-sqlite --size 5 --region fra`

- 2) Config app

e.g. with Koyeb 
```bash
koyeb service create raalisence/web \
  --image ghcr.io/you/raalisence:sqlite \
  --regions fra \
  --instance-type micro \
  --ports 8080:http --routes /:8080 \
  --env RAAL_DB_DRIVER=sqlite3 \
  --env RAAL_DB_PATH=/data/raalisence.db \
  --env RAAL_SERVER_ADDR=":8080" \
  --env RAAL_SERVER_ADMIN_API_KEY_HASHES="$(go run ./scripts/hash-admin-key.go change-me)" \
  --secret RAAL_SIGNING_PRIVATE_KEY_PEM=raal-priv \
  --secret RAAL_SIGNING_PUBLIC_KEY_PEM=raal-pub \
  --volumes raal-sqlite:/data`
```

## Structure 

```
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
```
