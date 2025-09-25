package handlers

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/rpattn/raalisence/internal/config"
	"github.com/rpattn/raalisence/internal/crypto"
)

type IssueRequest struct {
	Customer  string         `json:"customer"`
	MachineID string         `json:"machine_id"`
	ExpiresAt time.Time      `json:"expires_at"`
	Features  map[string]any `json:"features"`
}

type LicenseFile struct {
	Customer   string         `json:"customer"`
	MachineID  string         `json:"machine_id"`
	LicenseKey string         `json:"license_key"`
	ExpiresAt  time.Time      `json:"expires_at"`
	Features   map[string]any `json:"features"`
	IssuedAt   time.Time      `json:"issued_at"`
	Signature  string         `json:"signature"`
	PublicKey  string         `json:"public_key_pem"`
}

type ValidateRequest struct {
	LicenseKey string `json:"license_key"`
	MachineID  string `json:"machine_id"`
}

type ValidateResponse struct {
	Valid     bool      `json:"valid"`
	Revoked   bool      `json:"revoked"`
	ExpiresAt time.Time `json:"expires_at"`
	Reason    string    `json:"reason,omitempty"`
}

func IssueLicense(db *sql.DB, cfg *config.Config) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req IssueRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		if req.Customer == "" || req.MachineID == "" || req.ExpiresAt.IsZero() {
			http.Error(w, "customer, machine_id, expires_at required", http.StatusBadRequest)
			return
		}

		ctx := r.Context()
		licenseKey := uuid.NewString()
		now := time.Now().UTC()

		// insert
		const insert = `insert into licenses (id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at)
values ($1,$2,$3,$4,$5,$6,false,null,now(),now())`
		featuresJSON, _ := json.Marshal(req.Features)
		_, err := db.ExecContext(ctx, insert, uuid.New(), licenseKey, req.Customer, req.MachineID, string(featuresJSON), req.ExpiresAt.UTC())
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		priv, err := cfg.PrivateKey()
		if err != nil {
			http.Error(w, "signing key error", http.StatusInternalServerError)
			return
		}

		payload := map[string]any{
			"customer":    req.Customer,
			"machine_id":  req.MachineID,
			"license_key": licenseKey,
			"expires_at":  req.ExpiresAt.UTC().Format(time.RFC3339Nano),
			"issued_at":   now.Format(time.RFC3339Nano),
			"features":    req.Features,
		}
		sig, err := crypto.SignJSON(priv, payload)
		if err != nil {
			http.Error(w, "sign error", http.StatusInternalServerError)
			return
		}

		pubPEM := cfg.Signing.PublicKeyPEM
		lf := LicenseFile{
			Customer:   req.Customer,
			MachineID:  req.MachineID,
			LicenseKey: licenseKey,
			ExpiresAt:  req.ExpiresAt.UTC(),
			Features:   req.Features,
			IssuedAt:   now,
			Signature:  sig,
			PublicKey:  pubPEM,
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(lf)
	})
}

func RevokeLicense(db *sql.DB) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req ValidateRequest // re-use with license_key
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		if req.LicenseKey == "" {
			http.Error(w, "license_key required", http.StatusBadRequest)
			return
		}
		ctx := r.Context()
		res, err := db.ExecContext(ctx, `update licenses set revoked=true, updated_at=now() where license_key=$1`, req.LicenseKey)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		if n, _ := res.RowsAffected(); n == 0 {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"ok":true}`))
	})
}

func ValidateLicense(db *sql.DB, cfg *config.Config) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req ValidateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		if req.LicenseKey == "" || req.MachineID == "" {
			http.Error(w, "license_key and machine_id required", http.StatusBadRequest)
			return
		}

		ctx := r.Context()
		var revoked bool
		var expires time.Time
		var machine string
		err := db.QueryRowContext(ctx, `select revoked, expires_at, machine_id from licenses where license_key=$1`, req.LicenseKey).Scan(&revoked, &expires, &machine)
		if errors.Is(err, sql.ErrNoRows) {
			writeJSON(w, http.StatusOK, ValidateResponse{Valid: false, Reason: "unknown license"})
			return
		}
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		if machine != req.MachineID {
			writeJSON(w, http.StatusOK, ValidateResponse{Valid: false, Reason: "machine mismatch"})
			return
		}
		if revoked {
			writeJSON(w, http.StatusOK, ValidateResponse{Valid: false, Revoked: true, ExpiresAt: expires, Reason: "revoked"})
			return
		}
		if time.Now().After(expires) {
			writeJSON(w, http.StatusOK, ValidateResponse{Valid: false, ExpiresAt: expires, Reason: "expired"})
			return
		}
		writeJSON(w, http.StatusOK, ValidateResponse{Valid: true, Revoked: false, ExpiresAt: expires})
	})
}

func Heartbeat(db *sql.DB) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req ValidateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		if req.LicenseKey == "" {
			http.Error(w, "license_key required", http.StatusBadRequest)
			return
		}
		ctx := r.Context()
		res, err := db.ExecContext(ctx, `update licenses set last_seen_at=now(), updated_at=now() where license_key=$1`, req.LicenseKey)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		if n, _ := res.RowsAffected(); n == 0 {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"ok":true}`))
	})
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}
