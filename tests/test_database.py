"""Tests for database functionality."""

import tempfile
import os
import pytest
from python_raalisence.database.connection import DatabaseConnection
from python_raalisence.database.migrations import run_migrations
from python_raalisence.config.config import Config


@pytest.fixture
def sqlite_config():
    """Create a temporary SQLite config for testing."""
    config = Config()
    config.db_driver = "sqlite3"
    config.db_path = ":memory:"  # Use in-memory database
    config.admin_api_key = "test-admin-key"
    return config


@pytest.fixture
def db_connection(sqlite_config):
    """Create a database connection for testing."""
    db = DatabaseConnection(sqlite_config)
    db.connect()
    run_migrations(db)
    yield db
    db.close()


def test_database_connection(db_connection):
    """Test basic database connection."""
    assert db_connection.connection is not None


def test_migrations_create_table(db_connection):
    """Test that migrations create the licenses table."""
    cursor = db_connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='licenses'")
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "licenses"


def test_migrations_create_index(db_connection):
    """Test that migrations create the license_key index."""
    cursor = db_connection.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_licenses_license_key'")
    result = cursor.fetchone()
    assert result is not None


def test_license_insert_and_query(db_connection):
    """Test inserting and querying licenses."""
    # Insert a test license
    db_connection.execute("""
        INSERT INTO licenses (id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, NULL, datetime('now'), datetime('now'))
    """, ("test-id", "test-key", "test-customer", "test-machine", '{"seats": 5}', "2024-12-31T23:59:59"))
    
    # Query the license
    row = db_connection.execute_fetchone("SELECT license_key, customer, machine_id FROM licenses WHERE license_key = ?", ("test-key",))
    assert row is not None
    assert row[0] == "test-key"
    assert row[1] == "test-customer"
    assert row[2] == "test-machine"


def test_license_update(db_connection):
    """Test updating a license."""
    # Insert a test license
    db_connection.execute("""
        INSERT INTO licenses (id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, NULL, datetime('now'), datetime('now'))
    """, ("test-id", "test-key", "test-customer", "test-machine", '{"seats": 5}', "2024-12-31T23:59:59"))
    
    # Update the license
    cursor = db_connection.execute("UPDATE licenses SET revoked = 1 WHERE license_key = ?", ("test-key",))
    assert cursor.rowcount == 1
    
    # Verify the update
    row = db_connection.execute_fetchone("SELECT revoked FROM licenses WHERE license_key = ?", ("test-key",))
    assert row[0] == 1


def test_license_delete(db_connection):
    """Test deleting a license."""
    # Insert a test license
    db_connection.execute("""
        INSERT INTO licenses (id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, NULL, datetime('now'), datetime('now'))
    """, ("test-id", "test-key", "test-customer", "test-machine", '{"seats": 5}', "2024-12-31T23:59:59"))
    
    # Delete the license
    cursor = db_connection.execute("DELETE FROM licenses WHERE license_key = ?", ("test-key",))
    assert cursor.rowcount == 1
    
    # Verify deletion
    row = db_connection.execute_fetchone("SELECT license_key FROM licenses WHERE license_key = ?", ("test-key",))
    assert row is None
