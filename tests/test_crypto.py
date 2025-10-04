"""Tests for cryptographic operations."""

import pytest
from python_raalisence.crypto.sign import (
    generate_pem_keys, sign_json, verify_json, parse_public_key
)


def test_generate_pem_keys():
    """Test PEM key generation."""
    private_pem, public_pem = generate_pem_keys()
    
    assert "-----BEGIN EC PRIVATE KEY-----" in private_pem
    assert "-----END EC PRIVATE KEY-----" in private_pem
    assert "-----BEGIN PUBLIC KEY-----" in public_pem
    assert "-----END PUBLIC KEY-----" in public_pem


def test_sign_verify_json():
    """Test JSON signing and verification."""
    private_pem, public_pem = generate_pem_keys()
    
    # Parse keys
    from cryptography.hazmat.primitives import serialization
    private_key = serialization.load_pem_private_key(
        private_pem.encode('utf-8'), password=None
    )
    public_key = parse_public_key(public_pem)
    
    # Test payload
    payload = {
        "customer": "test-customer",
        "machine_id": "test-machine",
        "license_key": "test-key",
        "expires_at": "2024-12-31T23:59:59Z",
        "features": {"seats": 5}
    }
    
    # Sign
    signature = sign_json(private_key, payload)
    assert signature is not None
    assert len(signature) > 0
    
    # Verify
    assert verify_json(public_key, payload, signature) is True
    
    # Verify with modified payload
    modified_payload = payload.copy()
    modified_payload["customer"] = "different-customer"
    assert verify_json(public_key, modified_payload, signature) is False
    
    # Verify with invalid signature
    invalid_signature = "invalid-signature"
    assert verify_json(public_key, payload, invalid_signature) is False


def test_parse_public_key():
    """Test public key parsing."""
    private_pem, public_pem = generate_pem_keys()
    
    # Valid key
    public_key = parse_public_key(public_pem)
    assert public_key is not None
    
    # Invalid key
    with pytest.raises(ValueError):
        parse_public_key("invalid-pem")
    
    # Wrong key type (should be ECDSA)
    with pytest.raises(ValueError):
        parse_public_key("-----BEGIN PUBLIC KEY-----\ninvalid\n-----END PUBLIC KEY-----")

