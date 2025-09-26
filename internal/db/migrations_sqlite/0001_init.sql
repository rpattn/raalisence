-- internal/db/migrations_sqlite/0001_init.sql (SQLite)
CREATE TABLE IF NOT EXISTS licenses (
    id TEXT PRIMARY KEY,
    license_key TEXT UNIQUE NOT NULL,
    customer TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    features TEXT NOT NULL DEFAULT '{}', -- store JSON as TEXT
    expires_at TEXT NOT NULL,            -- RFC3339 timestamp
    revoked INTEGER NOT NULL DEFAULT 0,  -- 0=false, 1=true
    last_seen_at TEXT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_licenses_license_key ON licenses(license_key);

-- keep updated_at fresh
CREATE TRIGGER IF NOT EXISTS trg_licenses_updated_at
AFTER UPDATE ON licenses
FOR EACH ROW
BEGIN
  UPDATE licenses SET updated_at = datetime('now') WHERE id = OLD.id;
END;
