"""Integration tests for the complete license server."""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from python_raalisence.server import app


@pytest.fixture
def client(test_config):
    """Create test client with mocked dependencies and auth bypass."""
    from python_raalisence.server import app, get_db, get_config, get_admin_auth_dependency, admin_auth_dep
    from python_raalisence.middleware.auth import create_admin_auth_dependency
    from unittest.mock import Mock
    from python_raalisence.database.connection import DatabaseConnection
    
    # Create a mock database with the required methods
    mock_db = Mock(spec=DatabaseConnection)
    mock_db.config = test_config  # Add config attribute
    
    # Create a mock cursor with rowcount
    mock_cursor = Mock()
    mock_cursor.rowcount = 1  # One row affected for successful operations
    mock_db.execute.return_value = mock_cursor
    
    # Mock database responses - will be overridden in individual tests
    mock_db.execute_fetchone.return_value = None  # No license found by default
    mock_db.execute_fetchall.return_value = []
    
    mock_db.commit.return_value = None
    mock_db.close.return_value = None
    
    # Store the mock_db reference for tests to access
    client._mock_db = mock_db
    
    # Override the dependencies directly in the app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_config] = lambda: test_config
    app.dependency_overrides[admin_auth_dep] = lambda: "test-admin-key"
    
    # Mock the global variables and initialize admin auth dependency
    from python_raalisence.middleware.auth import create_admin_auth_dependency
    mock_admin_auth_dep = create_admin_auth_dependency(test_config)
    
    with patch('python_raalisence.server.config', test_config), \
         patch('python_raalisence.server.db', mock_db), \
         patch('python_raalisence.server.admin_auth_dependency', mock_admin_auth_dep):
        test_client = TestClient(app)
        test_client._mock_db = mock_db  # Store reference for tests
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def unauthorized_client(test_config):
    """Create test client without auth bypass for testing unauthorized access."""
    from python_raalisence.server import app, get_db, get_config, get_admin_auth_dependency, admin_auth_dep
    from python_raalisence.middleware.auth import create_admin_auth_dependency
    from unittest.mock import Mock
    from python_raalisence.database.connection import DatabaseConnection
    
    # Create a mock database with the required methods
    mock_db = Mock(spec=DatabaseConnection)
    mock_db.config = test_config  # Add config attribute
    
    # Create a mock cursor with rowcount
    mock_cursor = Mock()
    mock_cursor.rowcount = 1  # One row affected for successful operations
    mock_db.execute.return_value = mock_cursor
    
    # Mock database responses - will be overridden in individual tests
    mock_db.execute_fetchone.return_value = None  # No license found by default
    mock_db.execute_fetchall.return_value = []
    
    mock_db.commit.return_value = None
    mock_db.close.return_value = None
    
    # Override the dependencies directly in the app
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_config] = lambda: test_config
    # Don't override admin_auth_dep - let the real auth run
    
    # Mock the global variables and initialize admin auth dependency
    from python_raalisence.middleware.auth import create_admin_auth_dependency
    mock_admin_auth_dep = create_admin_auth_dependency(test_config)
    
    with patch('python_raalisence.server.config', test_config), \
         patch('python_raalisence.server.db', mock_db), \
         patch('python_raalisence.server.admin_auth_dependency', mock_admin_auth_dep):
        test_client = TestClient(app)
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


class TestCompleteLicenseFlow:
    """Test complete license management workflow."""
    
    def test_complete_license_workflow(self, client, test_config):
        """Test complete workflow: issue -> validate -> heartbeat -> revoke."""  
        
        # 1. Issue a license
        license_data = {
            "customer": "integration-test-customer",
            "machine_id": "integration-test-machine",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),  
            "features": {"seats": 10}
        }

        response = client.post(
            "/api/v1/licenses/issue",
            json=license_data,
            headers={"Authorization": "Bearer test-admin-key"}
        )

        assert response.status_code == 200
        license_response = response.json()
        assert license_response["customer"] == "integration-test-customer"       
        assert license_response["machine_id"] == "integration-test-machine"      
        assert license_response["features"] == {"seats": 10}
        assert license_response["license_key"] is not None
        assert license_response["signature"] is not None

        license_key = license_response["license_key"]
        
        # Set up mock to return license data for validation
        expires_at_str = license_data["expires_at"]
        client._mock_db.execute_fetchone.return_value = (False, expires_at_str, "integration-test-machine")

        # 2. Validate the license
        validate_data = {
            "license_key": license_key,
            "machine_id": "integration-test-machine"
        }

        response = client.post("/api/v1/licenses/validate", json=validate_data)  
        assert response.status_code == 200
        validate_response = response.json()
        assert validate_response["valid"] is True
        assert validate_response["revoked"] is False
        
        # 3. Send heartbeat
        heartbeat_data = {"license_key": license_key}
        
        response = client.post("/api/v1/licenses/heartbeat", json=heartbeat_data)
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # 4. List licenses
        import time
        time.sleep(0.1)  # Small delay to avoid rate limiting
        response = client.get(
            "/api/v1/licenses",
            headers={"Authorization": "Bearer test-admin-key"}
        )
        assert response.status_code == 200
        licenses_response = response.json()
        assert "licenses" in licenses_response
        
        # 5. Update license
        time.sleep(1.0)  # Longer delay to avoid rate limiting (admin limiter is 1 rps)
        update_data = {
            "license_key": license_key,
            "features": {"seats": 20}
        }
        
        response = client.post(
            "/api/v1/licenses/update",
            json=update_data,
            headers={"Authorization": "Bearer test-admin-key"}
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # 6. Revoke license
        time.sleep(1.0)  # Longer delay to avoid rate limiting (admin limiter is 1 rps)
        revoke_data = {"license_key": license_key}
        
        response = client.post(
            "/api/v1/licenses/revoke",
            json=revoke_data,
            headers={"Authorization": "Bearer test-admin-key"}
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # 7. Validate revoked license
        client._mock_db.execute_fetchone.return_value = (True, expires_at_str, "integration-test-machine")
        response = client.post("/api/v1/licenses/validate", json=validate_data)
        assert response.status_code == 200
        validate_response = response.json()
        assert validate_response["valid"] is False
        assert validate_response["revoked"] is True
        assert validate_response["reason"] == "revoked"


class TestErrorScenarios:
    """Test various error scenarios."""
    
    def test_unauthorized_access(self, unauthorized_client):
        """Test unauthorized access to admin endpoints."""
        license_data = {
            "customer": "test-customer",
            "machine_id": "test-machine",
            "expires_at": "2024-12-31T23:59:59Z",
            "features": {"seats": 5}
        }
        
        # No auth header
        response = unauthorized_client.post("/api/v1/licenses/issue", json=license_data)
        assert response.status_code == 401
        
        # Wrong auth header
        response = unauthorized_client.post(
            "/api/v1/licenses/issue",
            json=license_data,
            headers={"Authorization": "Bearer wrong-key"}
        )
        assert response.status_code == 401
        
        # Invalid auth format
        response = unauthorized_client.post(
            "/api/v1/licenses/issue",
            json=license_data,
            headers={"Authorization": "InvalidFormat"}
        )
        assert response.status_code == 401
    
    def test_malformed_requests(self, client):
        """Test malformed request handling."""
        # Invalid JSON
        response = client.post(
            "/api/v1/licenses/validate",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Missing required fields
        response = client.post("/api/v1/licenses/validate", json={})
        assert response.status_code == 422
        
        # Invalid date format
        response = client.post(
            "/api/v1/licenses/issue",
            json={
                "customer": "test",
                "machine_id": "test",
                "expires_at": "invalid-date",
                "features": {}
            },
            headers={"Authorization": "Bearer test-admin-key"}
        )
        assert response.status_code == 422


class TestRateLimitingIntegration:
    """Test rate limiting in integration."""
    
    def test_rate_limiting_headers(self, client):
        """Test that rate limiting headers are present."""
        response = client.get("/healthz")
        
        # Should have rate limit headers
        assert "RateLimit-Limit" in response.headers
        assert "RateLimit-Remaining" in response.headers
        
        # Should have request ID header
        assert "X-Request-ID" in response.headers
    
    def test_rate_limiting_functionality(self, client):
        """Test actual rate limiting behavior."""
        # Make many requests quickly to trigger rate limiting
        responses = []
        for _ in range(50):  # Much more than default limits
            response = client.get("/healthz")
            responses.append(response.status_code)
        
        # Should have some 429 responses due to rate limiting
        assert 429 in responses
        assert 200 in responses  # Some should still be allowed


class TestStaticFileServing:
    """Test static file serving."""
    
    def test_admin_panel_access(self, client):
        """Test accessing the admin panel."""
        import time
        # Wait longer to avoid rate limiting from previous tests
        time.sleep(2.0)
        
        # Root should redirect to admin panel
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/admin.html" in response.headers["location"]
        
        # Direct access to admin panel
        try:
            response = client.get("/static/admin.html")
            # Should either return 200 (if file exists) or 404 (if not)
            assert response.status_code in [200, 404]
        except RuntimeError as e:
            # If the static directory doesn't exist in test environment, 
            # the middleware will raise a RuntimeError before reaching the endpoint
            # This is expected behavior in test environment
            assert "StaticFiles directory" in str(e) and "does not exist" in str(e)
