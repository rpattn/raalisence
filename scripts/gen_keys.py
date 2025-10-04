#!/usr/bin/env python3
"""Generate ECDSA signing keys for development."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_raalisence.crypto.sign import generate_pem_keys


def main():
    """Generate and display ECDSA key pair."""
    print("Generating ECDSA P-256 key pair...")
    
    try:
        private_pem, public_pem = generate_pem_keys()
        
        print("\n=== PRIVATE KEY ===")
        print(private_pem)
        print("\n=== PUBLIC KEY ===")
        print(public_pem)
        
        print("\nKeys generated successfully!")
        print("Copy these keys to your config.yaml file.")
        
    except Exception as e:
        print(f"Error generating keys: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

