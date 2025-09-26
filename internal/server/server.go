package server

import (
	"database/sql"
	"net/http"

	"github.com/rpattn/raalisence/internal/config"
	"github.com/rpattn/raalisence/internal/handlers"
	"github.com/rpattn/raalisence/internal/middleware"
)

type Server struct {
	db  *sql.DB
	cfg *config.Config
}

func New(db *sql.DB, cfg *config.Config) *Server { return &Server{db: db, cfg: cfg} }

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	// health
	mux.Handle("/healthz", handlers.Health())

	// license handlers
	mux.Handle("/api/v1/licenses", middleware.WithAdminKey(s.cfg, handlers.ListLicenses(s.db, s.cfg)))
	mux.Handle("/api/v1/licenses/issue", middleware.WithAdminKey(s.cfg, handlers.IssueLicense(s.db, s.cfg)))
	mux.Handle("/api/v1/licenses/revoke", middleware.WithAdminKey(s.cfg, handlers.RevokeLicense(s.db)))
	mux.Handle("/api/v1/licenses/update", middleware.WithAdminKey(s.cfg, handlers.UpdateLicense(s.db, s.cfg)))
	mux.Handle("/api/v1/licenses/validate", handlers.ValidateLicense(s.db, s.cfg))
	mux.Handle("/api/v1/licenses/heartbeat", handlers.Heartbeat(s.db))

	// static admin panel
	fs := http.FileServer(http.Dir("static"))
	mux.Handle("/static/", http.StripPrefix("/static/", fs))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/static/admin.html", http.StatusFound)
	})

	h := middleware.WithRequestID(middleware.WithRateLimit(s.cfg, mux))

	// logging
	return middleware.Logging(h)
}
