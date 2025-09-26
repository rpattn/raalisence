package main

import (
	"context"
	"database/sql"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
	_ "github.com/mattn/go-sqlite3"

	"github.com/rpattn/raalisence/internal/config"
	"github.com/rpattn/raalisence/internal/db/migrations_sqlite"
	"github.com/rpattn/raalisence/internal/server"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config: %v", err)
	}

	// Preflight: ensure signing keys are valid early, with clear error.
	if _, err := cfg.PrivateKey(); err != nil {
		log.Fatalf("signing private key: %v", err)
	}
	if _, err := cfg.PublicKey(); err != nil {
		log.Fatalf("signing public key: %v", err)
	}

	// choose db driver
	driver := "pgx"
	dsn := cfg.DB.DSN
	if cfg.DB.Driver == "sqlite3" {
		driver = "sqlite3"
		dsn = cfg.DB.Path
	}

	db, err := sql.Open(driver, dsn)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer db.Close()
	if err := db.Ping(); err != nil {
		log.Fatalf("ping db: %v", err)
	}

	// In-app migration for SQLite (idempotent)
	if driver == "sqlite3" {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := migrate.EnsureSQLiteSchema(ctx, db); err != nil {
			log.Fatalf("sqlite migrate: %v", err)
		}
	}

	srv := server.New(db, cfg)

	httpSrv := &http.Server{
		Addr:              cfg.Server.Addr,
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       90 * time.Second,
	}

	go func() {
		log.Printf("raalisence listening on %s (driver=%s)", cfg.Server.Addr, driver)
		if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("http server: %v", err)
		}
	}()

	// graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := httpSrv.Shutdown(ctx); err != nil {
		log.Printf("shutdown error: %v", err)
	}
	log.Println("bye")
}
