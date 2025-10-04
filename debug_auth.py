#!/usr/bin/env python3
"""Debug authentication issue."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_raalisence'))

from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from python_raalisence.config.config import Config
from python_raalisence.middleware.auth import verify_admin_auth

def debug_auth():
    """Debug authentication."""
    config = Config.load()
    
    app = FastAPI()
    
    def admin_auth_dep(request: Request) -> str:
        print(f"DEBUG: admin_auth_dep called with headers: {dict(request.headers)}")
        return verify_admin_auth(request, config)
    
    @app.get("/test")
    async def test_endpoint(token: str = Depends(admin_auth_dep)):
        print(f"DEBUG: test_endpoint called with token: {token}")
        return {"message": "success", "token": token}
    
    client = TestClient(app)
    
    print("=== Debug Auth Test ===")
    
    # Test without auth
    print("Testing without auth...")
    response = client.get("/test")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    # Test with invalid auth
    print("Testing with invalid auth...")
    response = client.get("/test", headers={"Authorization": "Bearer invalid"})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

if __name__ == "__main__":
    debug_auth()
