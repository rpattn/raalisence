package handlers

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
	_ "github.com/mattn/go-sqlite3"

	"github.com/rpattn/raalisence/internal/config"
	"github.com/rpattn/raalisence/internal/crypto"
	"golang.org/x/crypto/bcrypt"
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
	req.Header.Set("Authorization", "Bearer test-admin")
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

func TestDecodeJSONBodyTooLarge(t *testing.T) {
	payload := `{"data":"` + strings.Repeat("a", int(maxJSONBody)) + `"}`
	req := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(payload))
	rr := httptest.NewRecorder()

	var dst map[string]any
	if decodeJSON(rr, req, &dst) {
		t.Fatal("expected decodeJSON to fail for oversized payload")
	}
	if rr.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("expected status %d got %d", http.StatusRequestEntityTooLarge, rr.Code)
	}
}

func TestListLicensesSQLite(t *testing.T) {
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	_, err = db.Exec(`create table licenses (
                id text primary key,
                license_key text unique not null,
                customer text not null,
                machine_id text not null,
                features text not null default '{}',
                expires_at text not null,
                revoked integer not null default 0,
                last_seen_at text null,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp
        )`)
	if err != nil {
		t.Fatal(err)
	}

	_, err = db.Exec(`insert into licenses (id, license_key, customer, machine_id, features, expires_at, revoked) values
                ('id-1', 'key-1', 'Acme', 'MID-1', '{}', '2025-01-01T00:00:00Z', 0),
                ('id-2', 'key-2', 'Beta', 'MID-2', '{}', '2026-01-01T00:00:00Z', 1)
        `)
	if err != nil {
		t.Fatal(err)
	}

	cfg := testConfig(t)
	cfg.DB.Driver = "sqlite3"

	req := httptest.NewRequest(http.MethodGet, "/api/v1/licenses", nil)
	rr := httptest.NewRecorder()
	ListLicenses(db, cfg).ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected status 200 got %d body=%s", rr.Code, rr.Body.String())
	}

	var resp ListLicensesResponse
	if err := json.Unmarshal(rr.Body.Bytes(), &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(resp.Licenses) != 2 {
		t.Fatalf("expected 2 licenses got %d", len(resp.Licenses))
	}
	if resp.Licenses[0].ID == "" || resp.Licenses[0].LicenseKey == "" {
		t.Fatal("expected license summary to include id and license_key")
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
	hash, err := bcrypt.GenerateFromPassword([]byte("test-admin"), bcrypt.DefaultCost)
	if err != nil {
		t.Fatal(err)
	}
	cfg.Server.AdminAPIKeyHashes = []string{string(hash)}
	cfg.Server.Addr = ":0"
	cfg.Signing.PrivateKeyPEM = priv
	cfg.Signing.PublicKeyPEM = pub
	return cfg
}
