package middleware

import (
	"log"
	"net/http"
	"time"

	"github.com/rpattn/raalisence/internal/config"
)

// statusWriter captures the status code and bytes written.
type statusWriter struct {
	http.ResponseWriter
	status int
	bytes  int
}

func (w *statusWriter) WriteHeader(code int) {
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}

func (w *statusWriter) Write(b []byte) (int, error) {
	if w.status == 0 {
		w.status = http.StatusOK
	}
	n, err := w.ResponseWriter.Write(b)
	w.bytes += n
	return n, err
}

func Logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w}

		next.ServeHTTP(sw, r)

		// Timestamp in UTC, RFC3339Nano for precision.
		ts := start.UTC().Format(time.RFC3339Nano)
		reqID := GetRequestID(r)
		log.Printf(
			"ts=%s req_id=%s method=%s path=%s status=%d bytes=%d dur=%s remote=%s",
			ts, reqID, r.Method, r.URL.Path, sw.status, sw.bytes, time.Since(start), r.RemoteAddr,
		)
	})
}

// WithAdminKey requires header: Authorization: Bearer <admin_api_key>
func WithAdminKey(cfg *config.Config, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ah := r.Header.Get("Authorization")
		const pfx = "Bearer "
		if len(ah) <= len(pfx) || !cfg.AdminKeyOK(ah[len(pfx):]) {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}
