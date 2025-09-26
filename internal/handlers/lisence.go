package handlers

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/rpattn/raalisence/internal/config"
	"github.com/rpattn/raalisence/internal/crypto"
)

const maxJSONBody = 64 * 1024 // 64KiB upper bound for JSON payloads

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

type LicenseSummary struct {
	ID         string         `json:"id"`
	LicenseKey string         `json:"license_key"`
	Customer   string         `json:"customer"`
	MachineID  string         `json:"machine_id"`
	ExpiresAt  string         `json:"expires_at"`
	Revoked    bool           `json:"revoked"`
	LastSeenAt *string        `json:"last_seen_at,omitempty"`
	Features   map[string]any `json:"features,omitempty"`
}

type ListLicensesResponse struct {
	Licenses []LicenseSummary `json:"licenses"`
}

type UpdateLicenseRequest struct {
	LicenseKey string         `json:"license_key"`
	ExpiresAt  *string        `json:"expires_at,omitempty"`
	Features   map[string]any `json:"features,omitempty"`
}

func IssueLicense(db *sql.DB, cfg *config.Config) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req IssueRequest
		if !decodeJSON(w, r, &req) {
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
		values ($1,$2,$3,$4,$5,$6,false,null,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)`
		featuresJSON, _ := json.Marshal(req.Features)
		expVal := any(req.ExpiresAt.UTC())
		if cfg.DB.Driver == "sqlite3" {
			expVal = req.ExpiresAt.UTC().Format(time.RFC3339Nano)
		}
		_, err := db.ExecContext(ctx, insert, uuid.New(), licenseKey, req.Customer, req.MachineID, string(featuresJSON), expVal)
		if err != nil {
			internalError(w, "issue.insert", err)
			return
		}

		priv, err := cfg.PrivateKey()
		if err != nil {
			internalError(w, "issue.private_key", err)
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
			internalError(w, "issue.sign", err)
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
		if !decodeJSON(w, r, &req) {
			return
		}
		if req.LicenseKey == "" {
			http.Error(w, "license_key required", http.StatusBadRequest)
			return
		}
		ctx := r.Context()
		res, err := db.ExecContext(ctx, `update licenses set revoked=true, updated_at=CURRENT_TIMESTAMP where license_key=$1`, req.LicenseKey)
		if err != nil {
			internalError(w, "revoke.update", err)
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
		if !decodeJSON(w, r, &req) {
			return
		}
		if req.LicenseKey == "" || req.MachineID == "" {
			http.Error(w, "license_key and machine_id required", http.StatusBadRequest)
			return
		}

		ctx := r.Context()
		var revoked bool
		var machine string
		var expires time.Time

		if cfg.DB.Driver == "sqlite3" {
			// SQLite stores expires_at as TEXT (RFC3339)
			var expStr string
			if err := db.QueryRowContext(ctx, `select revoked, expires_at, machine_id from licenses where license_key=$1`, req.LicenseKey).
				Scan(&revoked, &expStr, &machine); err != nil {
				if errors.Is(err, sql.ErrNoRows) {
					writeJSON(w, http.StatusOK, ValidateResponse{Valid: false, Reason: "unknown license"})
					return
				}
				internalError(w, "validate.lookup", err)
				return
			}
			// parse with RFC3339Nano then fall back to RFC3339
			var perr error
			expires, perr = time.Parse(time.RFC3339Nano, expStr)
			if perr != nil {
				expires, perr = time.Parse(time.RFC3339, expStr)
			}
			if perr != nil {
				http.Error(w, "bad expires_at format", http.StatusInternalServerError)
				return
			}
		} else {
			// Postgres path: timestamptz → time.Time
			if err := db.QueryRowContext(ctx, `select revoked, expires_at, machine_id from licenses where license_key=$1`, req.LicenseKey).
				Scan(&revoked, &expires, &machine); err != nil {
				if errors.Is(err, sql.ErrNoRows) {
					writeJSON(w, http.StatusOK, ValidateResponse{Valid: false, Reason: "unknown license"})
					return
				}
				internalError(w, "validate.lookup", err)
				return
			}
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
		if !decodeJSON(w, r, &req) {
			return
		}
		if req.LicenseKey == "" {
			http.Error(w, "license_key required", http.StatusBadRequest)
			return
		}
		ctx := r.Context()
		res, err := db.ExecContext(ctx, `update licenses set last_seen_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP where license_key=$1`, req.LicenseKey)
		if err != nil {
			internalError(w, "heartbeat.update", err)
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

func UpdateLicense(db *sql.DB, cfg *config.Config) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var req UpdateLicenseRequest
		if !decodeJSON(w, r, &req) {
			return
		}
		if req.LicenseKey == "" {
			http.Error(w, "license_key required", http.StatusBadRequest)
			return
		}

		ctx := r.Context()
		updates := make([]string, 0, 3)
		args := make([]any, 0, 3)

		if req.ExpiresAt != nil {
			parsed, err := time.Parse(time.RFC3339Nano, *req.ExpiresAt)
			if err != nil {
				parsed, err = time.Parse(time.RFC3339, *req.ExpiresAt)
			}
			if err != nil {
				http.Error(w, "expires_at must be RFC3339", http.StatusBadRequest)
				return
			}
			parsed = parsed.UTC()
			updates = append(updates, fmt.Sprintf("expires_at=$%d", len(args)+1))
			if cfg != nil && cfg.DB.Driver == "sqlite3" {
				args = append(args, parsed.Format(time.RFC3339Nano))
			} else {
				args = append(args, parsed)
			}
		}

		if req.Features != nil {
			featuresJSON, err := json.Marshal(req.Features)
			if err != nil {
				http.Error(w, "bad features payload", http.StatusBadRequest)
				return
			}
			clause := fmt.Sprintf("features=$%d", len(args)+1)
			if cfg != nil && cfg.DB.Driver != "sqlite3" {
				clause += "::jsonb"
			}
			updates = append(updates, clause)
			args = append(args, string(featuresJSON))
		}

		if len(updates) == 0 {
			http.Error(w, "no updates requested", http.StatusBadRequest)
			return
		}

		updates = append(updates, "updated_at=CURRENT_TIMESTAMP")
		args = append(args, req.LicenseKey)
		query := fmt.Sprintf("update licenses set %s where license_key=$%d", strings.Join(updates, ", "), len(args))

		res, err := db.ExecContext(ctx, query, args...)
		if err != nil {
			internalError(w, "license.update", err)
			return
		}
		if n, _ := res.RowsAffected(); n == 0 {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}

		writeJSON(w, http.StatusOK, map[string]any{"ok": true})
	})
}

func ListLicenses(db *sql.DB, cfg *config.Config) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		ctx := r.Context()
		rows, err := db.QueryContext(ctx, `select id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at from licenses order by created_at desc`)
		if err != nil {
			internalError(w, "licenses.list.query", err)
			return
		}
		defer rows.Close()

		resp := ListLicensesResponse{}
		for rows.Next() {
			var sum LicenseSummary
			if cfg != nil && cfg.DB.Driver == "sqlite3" {
				var features string
				var expires string
				var lastSeen sql.NullString
				if err := rows.Scan(&sum.ID, &sum.LicenseKey, &sum.Customer, &sum.MachineID, &features, &expires, &sum.Revoked, &lastSeen); err != nil {
					internalError(w, "licenses.list.scan", err)
					return
				}
				sum.ExpiresAt = expires
				if features != "" {
					var feats map[string]any
					if err := json.Unmarshal([]byte(features), &feats); err == nil {
						sum.Features = feats
					}
				}
				if lastSeen.Valid && lastSeen.String != "" {
					ls := lastSeen.String
					sum.LastSeenAt = &ls
				}
			} else {
				var features []byte
				var expires time.Time
				var lastSeen sql.NullTime
				if err := rows.Scan(&sum.ID, &sum.LicenseKey, &sum.Customer, &sum.MachineID, &features, &expires, &sum.Revoked, &lastSeen); err != nil {
					internalError(w, "licenses.list.scan", err)
					return
				}
				sum.ExpiresAt = expires.UTC().Format(time.RFC3339Nano)
				if len(features) > 0 {
					var feats map[string]any
					if err := json.Unmarshal(features, &feats); err == nil {
						sum.Features = feats
					}
				}
				if lastSeen.Valid {
					ls := lastSeen.Time.UTC().Format(time.RFC3339Nano)
					sum.LastSeenAt = &ls
				}
			}
			resp.Licenses = append(resp.Licenses, sum)
		}
		if err := rows.Err(); err != nil {
			internalError(w, "licenses.list.rows", err)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	})
}

func internalError(w http.ResponseWriter, op string, err error) {
	log.Printf("handler error op=%s err=%v", op, err)
	http.Error(w, "internal server error", http.StatusInternalServerError)
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func decodeJSON(w http.ResponseWriter, r *http.Request, v any) bool {
	limited := http.MaxBytesReader(w, r.Body, maxJSONBody)
	defer limited.Close()

	dec := json.NewDecoder(limited)
	if err := dec.Decode(v); err != nil {
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			log.Printf("request body too large path=%s remote=%s", r.URL.Path, r.RemoteAddr)
			http.Error(w, "request body too large", http.StatusRequestEntityTooLarge)
			return false
		}
		http.Error(w, "bad json", http.StatusBadRequest)
		return false
	}
	if dec.More() {
		http.Error(w, "bad json", http.StatusBadRequest)
		return false
	}
	return true
}
