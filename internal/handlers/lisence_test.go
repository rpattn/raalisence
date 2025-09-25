package handlers

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"

	"github.com/rpattn/raalisence/internal/config"
	"github.com/rpattn/raalisence/internal/crypto"
)

// Integration-ish test; requires TEST_DB_DSN env to be set.
func TestIssueValidateFlow(t *testing.T) {
	dsn := os.Getenv("TEST_DB_DSN")
	if dsn == "" {
		t.Skip("set TEST_DB_DSN to run")
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		t.Fatal(err)
	}

	// naive create table for test (ok if already exists)
	_, _ = db.Exec(`create table if not exists licenses (
		id uuid primary key,
		license_key text unique not null,
		customer text not null,
		machine_id text not null,
		features jsonb not null default '{}',
		expires_at timestamptz not null,
		revoked boolean not null default false,
		last_seen_at timestamptz null,
		created_at timestamptz not null default now(),
		updated_at timestamptz not null default now()
	)`)

	cfg := testConfig(t)

	// issue
	ir := IssueRequest{Customer: "Acme", MachineID: "MID1", ExpiresAt: time.Now().Add(24 * time.Hour)}
	b, _ := json.Marshal(ir)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/licenses/issue", bytes.NewReader(b))
	req.Header.Set("Authorization", "Bearer "+cfg.Server.AdminAPIKey)
	rw := httptest.NewRecorder()
	IssueLicense(db, cfg).ServeHTTP(rw, req)
	if rw.Code != http.StatusOK {
		t.Fatalf("issue code=%d body=%s", rw.Code, rw.Body.String())
	}
	var lf LicenseFile
	_ = json.Unmarshal(rw.Body.Bytes(), &lf)
	if lf.LicenseKey == "" {
		t.Fatal("missing license key")
	}

	// validate
	vr := ValidateRequest{LicenseKey: lf.LicenseKey, MachineID: "MID1"}
	b, _ = json.Marshal(vr)
	req = httptest.NewRequest(http.MethodPost, "/api/v1/licenses/validate", bytes.NewReader(b))
	rw = httptest.NewRecorder()
	ValidateLicense(db, cfg).ServeHTTP(rw, req)
	if rw.Code != http.StatusOK {
		t.Fatalf("validate code=%d body=%s", rw.Code, rw.Body.String())
	}
}

// minimal config with ephemeral keys for tests.
func testConfig(t *testing.T) *config.Config {
	t.Helper()
	priv, pub, err := crypto.GeneratePEM()
	if err != nil {
		t.Fatal(err)
	}
	cfg := &config.Config{}
	cfg.Server.AdminAPIKey = "test-admin"
	cfg.Server.Addr = ":0"
	cfg.Signing.PrivateKeyPEM = priv
	cfg.Signing.PublicKeyPEM = pub
	return cfg
}
