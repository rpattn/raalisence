-- internal/db/queries/licenses.sql
-- name: CreateLicense :exec
INSERT INTO licenses (id, license_key, customer, machine_id, features, expires_at, revoked, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, false, now(), now());


-- name: GetLicenseByKey :one
SELECT id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at
FROM licenses WHERE license_key = $1;


-- name: RevokeLicense :execrows
UPDATE licenses SET revoked = true, updated_at = now() WHERE license_key = $1;


-- name: TouchLicense :execrows
UPDATE licenses SET last_seen_at = now(), updated_at = now() WHERE license_key = $1;