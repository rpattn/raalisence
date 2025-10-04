"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path
import pytest
from python_raalisence.config.config import Config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    
    assert config.server_addr == ":8080"
    assert config.db_driver == "postgresql"
    assert config.db_dsn == "postgresql://postgres:postgres@localhost:5432/raalisence"
    assert config.db_path == "./raalisence.db"


def test_config_from_yaml():
    """Test loading configuration from YAML file."""
    yaml_content = """
server:
  addr: ":9090"
  admin_api_key: "test-key"

db:
  driver: "sqlite3"
  path: "/tmp/test.db"

signing:
  private_key_pem: "test-private"
  public_key_pem: "test-public"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        
        # Temporarily rename to config.yaml
        config_path = Path(f.name)
        config_dir = config_path.parent
        target_path = config_dir / "config.yaml"
        
        try:
            config_path.rename(target_path)
            os.chdir(config_dir)
            
            config = Config.load()
            
            assert config.server_addr == ":9090"
            assert config.admin_api_key == "test-key"
            assert config.db_driver == "sqlite3"
            assert config.db_path == "/tmp/test.db"
            assert config.signing_private_key_pem == "test-private"
            assert config.signing_public_key_pem == "test-public"
            
        finally:
            if target_path.exists():
                target_path.unlink()
            os.chdir(Path.cwd())


def test_config_from_env():
    """Test loading configuration from environment variables."""
    env_vars = {
        "RAAL_SERVER_ADDR": ":9090",
        "RAAL_SERVER_ADMIN_API_KEY": "env-key",
        "RAAL_DB_DRIVER": "sqlite3",
        "RAAL_DB_PATH": "/tmp/env.db",
        "RAAL_SIGNING_PRIVATE_KEY_PEM": "env-private",
        "RAAL_SIGNING_PUBLIC_KEY_PEM": "env-public"
    }
    
    old_env = {}
    for key, value in env_vars.items():
        old_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        config = Config.load()
        
        assert config.server_addr == ":9090"
        assert config.admin_api_key == "env-key"
        assert config.db_driver == "sqlite3"
        assert config.db_path == "/tmp/env.db"
        assert config.signing_private_key_pem == "env-private"
        assert config.signing_public_key_pem == "env-public"
        
    finally:
        for key, old_value in old_env.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def test_admin_key_validation():
    """Test admin key validation."""
    config = Config()
    config.admin_api_key = "test-key"
    
    # Valid key
    assert config.admin_key_ok("test-key") is True
    
    # Invalid key
    assert config.admin_key_ok("wrong-key") is False
    assert config.admin_key_ok("") is False
    
    # Different length
    assert config.admin_key_ok("test-key-extra") is False


def test_must_env():
    """Test must_env function."""
    from python_raalisence.config.config import must_env
    
    # Set environment variable
    os.environ["TEST_VAR"] = "test-value"
    
    try:
        assert must_env("TEST_VAR") == "test-value"
        
        # Test missing variable
        with pytest.raises(ValueError, match="missing env"):
            must_env("NONEXISTENT_VAR")
            
    finally:
        os.environ.pop("TEST_VAR", None)

