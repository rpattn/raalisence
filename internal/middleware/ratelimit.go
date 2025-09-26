package middleware

import (
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/rpattn/raalisence/internal/config"
)

type bucket struct {
	tokens     float64
	lastRefill time.Time
}

type limiter struct {
	mu        sync.Mutex
	buckets   map[string]*bucket
	rps       float64       // tokens per second
	burst     float64       // max tokens
	ttl       time.Duration // idle bucket eviction
	lastSweep time.Time
}

func newLimiter(rps float64, burst int, ttl time.Duration) *limiter {
	return &limiter{
		buckets:   make(map[string]*bucket),
		rps:       rps,
		burst:     float64(burst),
		ttl:       ttl,
		lastSweep: time.Now(),
	}
}

func (l *limiter) allow(key string) (ok bool, remaining int, retryAfter time.Duration) {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	// periodic sweep of stale buckets
	if now.Sub(l.lastSweep) > l.ttl {
		for k, b := range l.buckets {
			if now.Sub(b.lastRefill) > l.ttl {
				delete(l.buckets, k)
			}
		}
		l.lastSweep = now
	}

	b := l.buckets[key]
	if b == nil {
		b = &bucket{tokens: l.burst, lastRefill: now}
		l.buckets[key] = b
	}

	// refill
	elapsed := now.Sub(b.lastRefill).Seconds()
	b.tokens = mathMin(l.burst, b.tokens+elapsed*l.rps)
	b.lastRefill = now

	if b.tokens >= 1.0 {
		b.tokens -= 1.0
		return true, int(b.tokens), 0
	}

	missing := 1.0 - b.tokens
	retryAfter = time.Duration(missing / l.rps * float64(time.Second))
	return false, int(b.tokens), retryAfter
}

func mathMin(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// WithRateLimit applies a simple token bucket rate limit per client.
// Keying strategy:
// - Admin endpoints (/issue, /revoke) are keyed by admin token (so two admins behind the same IP aren't unfairly throttled).
// - Other endpoints keyed by client IP (first X-Forwarded-For hop if present, else RemoteAddr).
func WithRateLimit(cfg *config.Config, next http.Handler) http.Handler {
	// Defaults (tweak as you like or expose in config)
	fast := newLimiter(5, 10, 10*time.Minute) // validate/heartbeat
	admin := newLimiter(1, 3, 10*time.Minute) // issue/revoke
	deflt := newLimiter(2, 5, 10*time.Minute) // everything else

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var l *limiter
		key := rateKey(cfg, r)
		switch r.URL.Path {
		case "/api/v1/licenses/validate", "/api/v1/licenses/heartbeat":
			l = fast
		case "/api/v1/licenses/issue", "/api/v1/licenses/revoke":
			l = admin
		default:
			l = deflt
		}

		ok, remaining, retry := l.allow(key)
		w.Header().Set("RateLimit-Limit", "1")
		w.Header().Set("RateLimit-Remaining", strconv.Itoa(remaining))
		if !ok {
			if retry < 0 {
				retry = 0
			}
			w.Header().Set("Retry-After", strconv.FormatInt(int64(retry/time.Second), 10))
			http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func rateKey(cfg *config.Config, r *http.Request) string {
	if tok := bearerToken(r.Header.Get("Authorization")); tok != "" && cfg.AdminKeyOK(tok) {
		return "admin:" + tok
	}
	if ip := clientIP(r); ip != "" {
		return "ip:" + ip
	}
	return "ip:unknown"
}

func clientIP(r *http.Request) string {
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

func bearerToken(h string) string {
	const p = "Bearer "
	if len(h) > len(p) && h[:len(p)] == p {
		return h[len(p):]
	}
	return ""
}
