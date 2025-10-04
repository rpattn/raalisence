"""Configuration management for raalisence Python server."""

import os
import re
from typing import List, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import bcrypt
import yaml
from pathlib import Path


class Config:
    """Configuration class for the license server."""
    
    def __init__(self):
        self.server_addr: str = ":8080"
        self.admin_api_key: Optional[str] = None
        self.admin_api_key_hashes: List[str] = []
        self.db_driver: str = "postgresql"
        self.db_dsn: str = "postgresql://postgres:postgres@localhost:5432/raalisence"
        self.db_path: str = "./raalisence.db"
        self.signing_private_key_pem: str = ""
        self.signing_public_key_pem: str = ""
        
        self._private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self._public_key: Optional[ec.EllipticCurvePublicKey] = None
    
    @classmethod
    def load(cls) -> "Config":
        """Load configuration from YAML file and environment variables."""
        config = cls()
        
        # Try to load from YAML file
        config_paths = [
            "config.yaml",
            "configs/config.yaml",
            "/etc/raalisence/config.yaml"
        ]
        
        for path in config_paths:
            if Path(path).exists():
                with open(path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        config._load_from_dict(yaml_config)
                break
        
        # Override with environment variables
        config._load_from_env()
        
        return config
    
    def _load_from_dict(self, data: dict):
        """Load configuration from dictionary."""
        server_config = data.get("server", {})
        self.server_addr = server_config.get("addr", self.server_addr)
        self.admin_api_key = server_config.get("admin_api_key")
        self.admin_api_key_hashes = server_config.get("admin_api_key_hashes", [])
        
        db_config = data.get("db", {})
        self.db_driver = db_config.get("driver", self.db_driver)
        self.db_dsn = db_config.get("dsn", self.db_dsn)
        self.db_path = db_config.get("path", self.db_path)
        
        signing_config = data.get("signing", {})
        self.signing_private_key_pem = signing_config.get("private_key_pem", "")
        self.signing_public_key_pem = signing_config.get("public_key_pem", "")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        self.server_addr = os.getenv("RAAL_SERVER_ADDR", self.server_addr)
        self.admin_api_key = os.getenv("RAAL_SERVER_ADMIN_API_KEY", self.admin_api_key)
        
        # Handle admin API key hashes
        hashes_env = os.getenv("RAAL_SERVER_ADMIN_API_KEY_HASHES")
        if hashes_env:
            # Split by comma, newline, semicolon
            hashes = re.split(r'[,;\n\r]+', hashes_env)
            self.admin_api_key_hashes.extend([h.strip() for h in hashes if h.strip()])
        
        self.db_driver = os.getenv("RAAL_DB_DRIVER", self.db_driver)
        self.db_dsn = os.getenv("RAAL_DB_DSN", self.db_dsn)
        self.db_path = os.getenv("RAAL_DB_PATH", self.db_path)
        
        self.signing_private_key_pem = os.getenv("RAAL_SIGNING_PRIVATE_KEY_PEM", self.signing_private_key_pem)
        self.signing_public_key_pem = os.getenv("RAAL_SIGNING_PUBLIC_KEY_PEM", self.signing_public_key_pem)
    
    def admin_key_ok(self, token: str) -> bool:
        """Check if the provided admin API key is valid."""
        # Check hashes first
        if self.admin_api_key_hashes:
            token_bytes = token.encode('utf-8')
            for hash_str in self.admin_api_key_hashes:
                if not hash_str:
                    continue
                try:
                    if bcrypt.checkpw(token_bytes, hash_str.encode('utf-8')):
                        return True
                except Exception:
                    continue
            return False
        
        # Fall back to direct comparison
        if not self.admin_api_key:
            return False
        
        # Constant-time comparison
        if len(token) != len(self.admin_api_key):
            return False
        
        result = 0
        for a, b in zip(token.encode('utf-8'), self.admin_api_key.encode('utf-8')):
            result |= a ^ b
        
        return result == 0
    
    def private_key(self) -> ec.EllipticCurvePrivateKey:
        """Get the private key for signing."""
        if self._private_key is not None:
            return self._private_key
        
        if not self.signing_private_key_pem:
            raise ValueError("missing signing.private_key_pem")
        
        try:
            self._private_key = serialization.load_pem_private_key(
                self.signing_private_key_pem.encode('utf-8'),
                password=None
            )
            return self._private_key
        except Exception as e:
            raise ValueError(f"invalid PEM private key: {e}")
    
    def public_key(self) -> ec.EllipticCurvePublicKey:
        """Get the public key for verification."""
        if self._public_key is not None:
            return self._public_key
        
        if not self.signing_public_key_pem:
            raise ValueError("missing signing.public_key_pem")
        
        try:
            self._public_key = serialization.load_pem_public_key(
                self.signing_public_key_pem.encode('utf-8')
            )
            return self._public_key
        except Exception as e:
            raise ValueError(f"invalid PEM public key: {e}")


def must_env(key: str) -> str:
    """Get environment variable or raise exception if not found."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"missing env: {key}")
    return value

