"""Cryptographic signing and verification functionality."""

import json
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend


def sign_json(private_key: ec.EllipticCurvePrivateKey, payload: Dict[str, Any]) -> str:
    """Sign the canonical JSON encoding of payload using ECDSA P-256/SHA-256."""
    # Serialize payload to canonical JSON
    json_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    
    # Hash the JSON
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(json_bytes)
    message_hash = digest.finalize()
    
    # Sign the hash
    signature = private_key.sign(message_hash, ec.ECDSA(hashes.SHA256()))
    
    # Encode signature as base64url
    return base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')


def verify_json(public_key: ec.EllipticCurvePublicKey, payload: Dict[str, Any], signature_b64: str) -> bool:
    """Verify a signature over payload with a public key."""
    try:
        # Serialize payload to canonical JSON
        json_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        # Hash the JSON
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(json_bytes)
        message_hash = digest.finalize()
        
        # Decode signature
        signature = base64.urlsafe_b64decode(signature_b64 + '==')  # Add padding
        
        # Verify signature
        public_key.verify(signature, message_hash, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def generate_pem_keys() -> tuple[str, str]:
    """Generate a new ECDSA P-256 key pair in PEM format."""
    # Generate private key
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Serialize private key to PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key and serialize to PEM
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem


def parse_public_key(pem_str: str) -> ec.EllipticCurvePublicKey:
    """Parse public key from PEM string."""
    try:
        public_key = serialization.load_pem_public_key(
            pem_str.encode('utf-8'),
            backend=default_backend()
        )
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise ValueError("not ECDSA key")
        return public_key
    except Exception as e:
        raise ValueError(f"invalid PEM public key: {e}")

