package migrate

import (
	"context"
	"database/sql"
	_ "embed"
	"fmt"
)

//go:embed "0001_init.sql"
var sqliteInitSQL string

// EnsureSQLiteSchema applies the idempotent SQLite schema.
func EnsureSQLiteSchema(ctx context.Context, db *sql.DB) error {
	if sqliteInitSQL == "" {
		return fmt.Errorf("embedded sqlite migration is empty")
	}
	_, err := db.ExecContext(ctx, sqliteInitSQL)
	return err
}
