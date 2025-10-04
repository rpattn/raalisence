#!/usr/bin/env python3
"""Debug server authentication issue."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python_raalisence'))

from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from python_raalisence.config.config import Config
from python_raalisence.database.connection import DatabaseConnection
from python_raalisence.database.migrations import run_migrations
from python_raalisence.middleware.auth import create_admin_auth_dependency

def debug_server():
    """Debug server authentication."""
    # Initialize everything manually
    config = Config.load()
    
    # Initialize database
    db = DatabaseConnection(config)
    db.connect()
    
    # Run migrations
    run_migrations(db)
    
    # Configure admin auth
    admin_auth_dependency = create_admin_auth_dependency(config)
    
    app = FastAPI()
    
    def admin_auth_dep(request: Request) -> str:
        print(f"DEBUG: admin_auth_dep called with headers: {dict(request.headers)}")
        return admin_auth_dependency(request)
    
    @app.get("/test")
    async def test_endpoint(token: str = Depends(admin_auth_dep)):
        print(f"DEBUG: test_endpoint called with token: {token}")
        return {"message": "success", "token": token}
    
    client = TestClient(app)
    
    print("=== Debug Server Test ===")
    print(f"admin_auth_dependency: {admin_auth_dependency}")
    print()
    
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
    
    # Cleanup
    db.close()

if __name__ == "__main__":
    debug_server()
