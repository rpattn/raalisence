"""Database migrations for license server."""

import os
from pathlib import Path
from python_raalisence.database.connection import DatabaseConnection


def run_migrations(db: DatabaseConnection):
    """Run database migrations."""
    if db.config.db_driver == "sqlite3":
        run_sqlite_migrations(db)
    elif db.config.db_driver == "postgresql":
        run_postgres_migrations(db)
    else:
        raise ValueError(f"unsupported database driver: {db.config.db_driver}")


def run_sqlite_migrations(db: DatabaseConnection):
    """Run SQLite migrations."""
    # Check if licenses table exists
    cursor = db.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='licenses'
    """)
    
    if cursor.fetchone() is None:
        # Create licenses table
        db.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id TEXT PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                customer TEXT NOT NULL,
                machine_id TEXT NOT NULL,
                features TEXT NOT NULL DEFAULT '{}',
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                last_seen_at TEXT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Create index
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_licenses_license_key ON licenses(license_key)
        """)
        
        # Create trigger for updated_at
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_licenses_updated_at
            AFTER UPDATE ON licenses
            FOR EACH ROW
            BEGIN
              UPDATE licenses SET updated_at = datetime('now') WHERE id = OLD.id;
            END
        """)
        
        db.commit()


def run_postgres_migrations(db: DatabaseConnection):
    """Run PostgreSQL migrations."""
    # Check if licenses table exists
    cursor = db.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'licenses'
    """)
    
    if cursor.fetchone() is None:
        # Create licenses table
        db.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id UUID PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                customer TEXT NOT NULL,
                machine_id TEXT NOT NULL,
                features JSONB NOT NULL DEFAULT '{}',
                expires_at TIMESTAMPTZ NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE,
                last_seen_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        
        # Create index
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_licenses_license_key ON licenses(license_key)
        """)
        
        db.commit()

