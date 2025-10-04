"""Test configuration and fixtures."""

import pytest
import tempfile
import os
from python_raalisence.config.config import Config


@pytest.fixture(scope="session")
def test_keys():
    """Generate test signing keys for all tests."""
    from python_raalisence.crypto.sign import generate_pem_keys
    
    private_pem, public_pem = generate_pem_keys()
    return private_pem, public_pem


@pytest.fixture
def test_config(test_keys):
    """Create a test configuration."""
    private_pem, public_pem = test_keys
    
    config = Config()
    config.server_addr = ":8080"
    config.admin_api_key = "test-admin-key"
    config.db_driver = "sqlite3"
    config.db_path = ":memory:"  # Use in-memory database for tests
    config.signing_private_key_pem = private_pem
    config.signing_public_key_pem = public_pem
    return config


@pytest.fixture
def temp_config_file(test_keys):
    """Create a temporary config file for testing."""
    private_pem, public_pem = test_keys
    
    config_content = f"""
server:
  addr: ":8080"
  admin_api_key: "test-admin-key"

db:
  driver: "sqlite3"
  path: ":memory:"

signing:
  private_key_pem: |
{private_pem}
  public_key_pem: |
{public_pem}
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        f.flush()
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def mock_database(test_config):
    """Create a mock database connection."""
    from unittest.mock import Mock
    db = Mock()
    db.config = test_config  # Add config attribute
    db.execute = Mock()
    db.execute_fetchone = Mock()
    db.execute_fetchall = Mock()
    db.commit = Mock()
    db.close = Mock()
    db.connection = Mock()
    return db
