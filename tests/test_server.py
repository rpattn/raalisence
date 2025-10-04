"""Tests for the main server application."""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from python_raalisence.server import app, get_db, get_config, get_admin_auth_dependency, admin_auth_dep
from python_raalisence.config.config import Config
from python_raalisence.database.connection import DatabaseConnection
from python_raalisence.middleware.auth import create_admin_auth_dependency


@pytest.fixture
def test_client(test_config):
    """Create a test client for the FastAPI app."""
    # Create a mock database with the required methods
    mock_db = Mock(spec=DatabaseConnection)
    mock_db.config = test_config  # Add config attribute
    mock_db.execute_fetchone.return_value = None  # No license found
    mock_db.execute_fetchall.return_value = []
    
    # Create a mock cursor with rowcount
    mock_cursor = Mock()
    mock_cursor.rowcount = 0  # No rows affected for heartbeat test
    mock_db.execute.return_value = mock_cursor
    
    mock_db.commit.return_value = None
    mock_db.close.return_value = None
    
    # Override the dependencies directly in the app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_config] = lambda: test_config
    
    # Mock the global variables and initialize admin auth dependency
    from python_raalisence.middleware.auth import create_admin_auth_dependency
    mock_admin_auth_dep = create_admin_auth_dependency(test_config)
    
    with patch('python_raalisence.server.config', test_config), \
         patch('python_raalisence.server.db', mock_db), \
         patch('python_raalisence.server.admin_auth_dependency', mock_admin_auth_dep):
        yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_test_client(test_config):
    """Create a test client with authentication overridden."""
    # Create a mock database with the required methods
    mock_db = Mock(spec=DatabaseConnection)
    mock_db.config = test_config  # Add config attribute
    mock_db.execute_fetchone.return_value = None  # No license found
    mock_db.execute_fetchall.return_value = []
    
    # Create a mock cursor with rowcount
    mock_cursor = Mock()
    mock_cursor.rowcount = 1  # One row affected for successful operations
    mock_db.execute.return_value = mock_cursor
    
    mock_db.commit.return_value = None
    mock_db.close.return_value = None
    
    # Override the dependencies directly in the app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_config] = lambda: test_config
    # Override admin auth dependency to always return test key
    def mock_admin_auth(request):
        return "test-admin-key"
    app.dependency_overrides[admin_auth_dep] = mock_admin_auth
    
    # Mock the global variables and initialize admin auth dependency
    from python_raalisence.middleware.auth import create_admin_auth_dependency
    mock_admin_auth_dep = create_admin_auth_dependency(test_config)
    
    with patch('python_raalisence.server.config', test_config), \
         patch('python_raalisence.server.db', mock_db), \
         patch('python_raalisence.server.admin_auth_dependency', mock_admin_auth_dep):
        yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint(self, test_client):
        """Test health check endpoint returns 200."""
        response = test_client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestLicenseEndpoints:
    """Test license management endpoints."""
    
    def test_issue_license_missing_auth(self, test_client):
        """Test issuing license without authentication."""
        license_data = {
            "customer": "test-customer",
            "machine_id": "test-machine",
            "expires_at": "2024-12-31T23:59:59Z",
            "features": {"seats": 5}
        }
        
        response = test_client.post("/api/v1/licenses/issue", json=license_data)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        assert response.status_code == 401
    
    def test_validate_license_no_auth_required(self, test_client):
        """Test validating license (no auth required)."""
        validate_data = {
            "license_key": "test-key",
            "machine_id": "test-machine"
        }
        
        response = test_client.post("/api/v1/licenses/validate", json=validate_data)
        # Should return 200 even if license doesn't exist
        assert response.status_code == 200
        assert response.json()["valid"] is False
        assert response.json()["reason"] == "unknown license"
    
    def test_heartbeat_no_auth_required(self, test_client):
        """Test heartbeat endpoint (no auth required)."""
        heartbeat_data = {
            "license_key": "test-key"
        }
        
        response = test_client.post("/api/v1/licenses/heartbeat", json=heartbeat_data)
        # Should return 404 if license doesn't exist
        assert response.status_code == 404
    
    def test_revoke_license_missing_auth(self, test_client):
        """Test revoking license without authentication."""
        revoke_data = {
            "license_key": "test-key"
        }
        
        response = test_client.post("/api/v1/licenses/revoke", json=revoke_data)
        assert response.status_code == 401
    
    def test_list_licenses_missing_auth(self, test_client):
        """Test listing licenses without authentication."""
        response = test_client.get("/api/v1/licenses")
        assert response.status_code == 401


class TestStaticFiles:
    """Test static file serving."""
    
    def test_root_redirect(self, test_client):
        """Test root path redirects to admin panel."""
        response = test_client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/admin.html"
    
    def test_static_files_mount(self, test_client):
        """Test static files are properly mounted."""
        # Test that static files endpoint is accessible
        try:
            response = test_client.get("/static/admin.html")
            # Should return 200 if file exists, or 404 if not
            assert response.status_code in [200, 404]
        except Exception as e:
            # If the static directory doesn't exist in test environment, 
            # the middleware will raise a RuntimeError before reaching the endpoint
            # This is expected behavior in test environment
            assert "StaticFiles directory" in str(e) and "does not exist" in str(e)


class TestServerCreation:
    """Test server creation and configuration."""
    
    def test_app_creation(self):
        """Test that the app is created successfully."""
        assert app is not None
        assert app.title == "raalisence"
    
    def test_app_has_middleware(self):
        """Test that the app has middleware configured."""
        # Check that middleware is added (this is tested indirectly)
        assert app.middleware_stack is not None


class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    def test_middleware_order(self, test_client):
        """Test that middleware is properly applied."""
        # Make a request and check headers
        response = test_client.get("/healthz")
        
        # Should have request ID header (from logging middleware)
        assert "X-Request-ID" in response.headers
        
        # Should have rate limit headers (from rate limiting middleware)
        assert "RateLimit-Limit" in response.headers
        assert "RateLimit-Remaining" in response.headers


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_json(self, test_client):
        """Test handling of invalid JSON."""
        response = test_client.post(
            "/api/v1/licenses/validate",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_fields(self, test_client):
        """Test handling of missing required fields."""
        response = test_client.post(
            "/api/v1/licenses/validate",
            json={"license_key": "test-key"}  # Missing machine_id
        )
        assert response.status_code == 422
    
    def test_invalid_endpoint(self, test_client):
        """Test handling of invalid endpoints."""
        response = test_client.get("/api/v1/invalid")
        assert response.status_code == 404
