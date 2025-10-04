"""Tests for middleware functionality."""

import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from python_raalisence.middleware.auth import admin_failure_key, verify_admin_auth
from python_raalisence.middleware.logging import LoggingMiddleware
from python_raalisence.middleware.ratelimit import RateLimitMiddleware, RateLimiter, TokenBucket
from python_raalisence.config.config import Config


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config()
    config.admin_api_key = "test-admin-key"
    return config


class TestAdminAuth:
    """Test admin authentication middleware."""
    
    def test_admin_key_validation_valid(self, test_config):
        """Test valid admin key validation."""
        # Mock request with valid token
        request = Mock()
        request.headers = {"Authorization": "Bearer test-admin-key"}
        
        # This would normally be called by FastAPI's dependency system
        # We're testing the underlying logic
        assert test_config.admin_key_ok("test-admin-key") is True
    
    def test_admin_key_validation_invalid(self, test_config):
        """Test invalid admin key validation."""
        assert test_config.admin_key_ok("wrong-key") is False
        assert test_config.admin_key_ok("") is False
    
    def test_admin_failure_key(self):
        """Test admin failure key extraction."""
        # Test with X-Forwarded-For header
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        key = admin_failure_key(request)
        assert key == "192.168.1.1"
        
        # Test with client IP
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        key = admin_failure_key(request)
        assert key == "127.0.0.1"


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_token_bucket_allow(self):
        """Test token bucket allowing requests."""
        bucket = TokenBucket(rps=1.0, burst=2)
        
        # Should allow first request
        allowed, remaining, retry_after = bucket.allow()
        assert allowed is True
        assert remaining == 1
        assert retry_after == 0.0
        
        # Should allow second request
        allowed, remaining, retry_after = bucket.allow()
        assert allowed is True
        assert remaining == 0
        assert retry_after == 0.0
    
    def test_token_bucket_rate_limit(self):
        """Test token bucket rate limiting."""
        bucket = TokenBucket(rps=1.0, burst=1)
        
        # Should allow first request
        allowed, remaining, retry_after = bucket.allow()
        assert allowed is True
        assert remaining == 0
        
        # Should deny second request
        allowed, remaining, retry_after = bucket.allow()
        assert allowed is False
        assert retry_after > 0
    
    def test_token_bucket_refill(self):
        """Test token bucket refilling over time."""
        bucket = TokenBucket(rps=2.0, burst=1)
        
        # Use up the token
        allowed, remaining, retry_after = bucket.allow()
        assert allowed is True
        assert remaining == 0
        
        # Wait for refill (simulate)
        import time
        time.sleep(0.6)  # Should refill 1.2 tokens, capped at burst of 1
        
        allowed, remaining, retry_after = bucket.allow()
        assert allowed is True
    
    def test_rate_limiter_different_keys(self):
        """Test rate limiter with different keys."""
        limiter = RateLimiter(rps=1.0, burst=1)
        
        # Different keys should have separate buckets
        allowed1, _, _ = limiter.allow("key1")
        allowed2, _, _ = limiter.allow("key2")
        
        assert allowed1 is True
        assert allowed2 is True  # Different key, separate bucket
    
    def test_rate_limiter_same_key(self):
        """Test rate limiter with same key."""
        limiter = RateLimiter(rps=1.0, burst=1)
        
        # Same key should be rate limited
        allowed1, _, _ = limiter.allow("key1")
        allowed2, _, _ = limiter.allow("key1")
        
        assert allowed1 is True
        assert allowed2 is False  # Same key, rate limited


class TestLogging:
    """Test logging middleware."""
    
    def test_logging_middleware(self):
        """Test logging middleware functionality."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        # Add logging middleware
        app.add_middleware(LoggingMiddleware)
        
        client = TestClient(app)
        
        # Mock the print function to capture logs
        with patch('builtins.print') as mock_print:
            response = client.get("/test")
            assert response.status_code == 200
            
            # Verify that logging was called
            mock_print.assert_called()
            
            # Check that the log contains expected fields
            log_call = mock_print.call_args[0][0]
            assert "method=GET" in log_call
            assert "path=/test" in log_call
            assert "status=200" in log_call
            assert "req_id=" in log_call


class TestIntegration:
    """Integration tests for middleware."""
    
    def test_rate_limiting_integration(self, test_config):
        """Test rate limiting with FastAPI integration."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Add rate limiting middleware
        app.add_middleware(RateLimitMiddleware)

        # Mock the global config for the middleware
        with patch('python_raalisence.server.config', test_config):
            client = TestClient(app)

            # Make requests quickly to trigger rate limiting
            responses = []
            for _ in range(50):  # Much more than the default limit (burst=5, rps=2.0)
                response = client.get("/test")
                responses.append(response.status_code)

            # Should have some 429 responses due to rate limiting
            # Note: The default limiter allows 2 rps with burst of 5, so 50 requests should definitely trigger limiting
            assert 429 in responses
            assert 200 in responses  # Some should still be allowed
