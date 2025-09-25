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
	mux.Handle("/api/v1/licenses/issue", middleware.WithAdminKey(s.cfg, handlers.IssueLicense(s.db, s.cfg)))
	mux.Handle("/api/v1/licenses/revoke", middleware.WithAdminKey(s.cfg, handlers.RevokeLicense(s.db)))
	mux.Handle("/api/v1/licenses/validate", handlers.ValidateLicense(s.db, s.cfg))
	mux.Handle("/api/v1/licenses/heartbeat", handlers.Heartbeat(s.db))

	// logging
	return middleware.Logging(mux)
}
