#!/usr/bin/env python3
"""Generate bcrypt hash for admin API key."""

import sys
import bcrypt


def main():
    """Generate bcrypt hash for admin key."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/gen.py <admin-key>", file=sys.stderr)
        print("Example: python scripts/gen.py my-secret-admin-key", file=sys.stderr)
        sys.exit(1)
    
    admin_key = sys.argv[1]
    
    try:
        hash_bytes = bcrypt.hashpw(admin_key.encode('utf-8'), bcrypt.gensalt())
        hash_str = hash_bytes.decode('utf-8')
        
        print(f"Admin key: {admin_key}")
        print(f"Bcrypt hash: {hash_str}")
        print()
        print("Add this hash to your config.yaml:")
        print("admin_api_key_hashes:")
        print(f'  - "{hash_str}"')
        
    except Exception as e:
        print(f"Error generating hash: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

