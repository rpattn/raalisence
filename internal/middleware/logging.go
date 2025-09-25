package middleware

import (
	"log"
	"net/http"
	"time"

	"github.com/rpattn/raalisence/internal/config"
)

func Logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
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
