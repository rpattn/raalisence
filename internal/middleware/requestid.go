// internal/middleware/requestid.go
package middleware

import (
	"context"
	"net/http"

	"github.com/google/uuid"
)

type ctxKey string

const requestIDKey ctxKey = "req-id"

// WithRequestID adds/propagates a request id.
// Reads X-Request-ID from the request if present; otherwise generates one.
// Adds X-Request-ID to the response. Use GetRequestID(r) to read it in handlers.
func WithRequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		reqID := r.Header.Get("X-Request-ID")
		if reqID == "" {
			reqID = uuid.NewString()
		}
		w.Header().Set("X-Request-ID", reqID)

		ctx := context.WithValue(r.Context(), requestIDKey, reqID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// GetRequestID returns the request id previously set by WithRequestID.
func GetRequestID(r *http.Request) string {
	if v := r.Context().Value(requestIDKey); v != nil {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}
