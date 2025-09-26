package middleware

import (
	"log"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/rpattn/raalisence/internal/config"
)

const (
	adminFailureWindow    = 10 * time.Minute
	adminFailureThreshold = 5
)

type failureState struct {
	count   int
	last    time.Time
	alerted bool
}

type failureTracker struct {
	mu    sync.Mutex
	state map[string]*failureState
}

func newFailureTracker() *failureTracker {
	return &failureTracker{state: make(map[string]*failureState)}
}

func (t *failureTracker) recordFailure(key string) (count int, shouldAlert bool) {
	now := time.Now()
	t.mu.Lock()
	defer t.mu.Unlock()

	st := t.state[key]
	if st == nil || now.Sub(st.last) > adminFailureWindow {
		st = &failureState{}
		t.state[key] = st
	}
	st.count++
	st.last = now

	if st.count >= adminFailureThreshold && !st.alerted {
		st.alerted = true
		return st.count, true
	}
	return st.count, false
}

func (t *failureTracker) reset(key string) {
	t.mu.Lock()
	defer t.mu.Unlock()
	delete(t.state, key)
}

var adminFailures = newFailureTracker()

// WithAdminKey requires header: Authorization: Bearer <admin_api_key>
func WithAdminKey(cfg *config.Config, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		key := adminFailureKey(r)
		ah := r.Header.Get("Authorization")
		const pfx = "Bearer "
		if !strings.HasPrefix(ah, pfx) {
			count, alert := adminFailures.recordFailure(key)
			if alert {
				log.Printf("ALERT admin_auth_failure remote=%s count=%d window=%v", key, count, adminFailureWindow)
			}
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}

		token := ah[len(pfx):]
		if !cfg.AdminKeyOK(token) {
			count, alert := adminFailures.recordFailure(key)
			if alert {
				log.Printf("ALERT admin_auth_failure remote=%s count=%d window=%v", key, count, adminFailureWindow)
			}
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}

		adminFailures.reset(key)
		next.ServeHTTP(w, r)
	})
}

func adminFailureKey(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		if i := strings.IndexByte(xff, ','); i >= 0 {
			return strings.TrimSpace(xff[:i])
		}
		return strings.TrimSpace(xff)
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}
