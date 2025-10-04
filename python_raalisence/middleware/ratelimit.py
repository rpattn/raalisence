"""Rate limiting middleware."""

import time
import threading
from typing import Dict, Optional
from fastapi import HTTPException, Request
from starlette.responses import Response


class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, rps: float, burst: int, ttl: int = 600):
        self.rps = rps  # tokens per second
        self.burst = burst  # max tokens
        self.ttl = ttl  # idle bucket eviction time
        self.tokens = float(burst)
        self.last_refill = time.time()
    
    def allow(self) -> tuple[bool, int, float]:
        """Check if request is allowed. Returns (allowed, remaining_tokens, retry_after)."""
        now = time.time()
        
        # Refill tokens
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rps)
        self.last_refill = now
        
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, int(self.tokens), 0.0
        
        # Not enough tokens
        missing = 1.0 - self.tokens
        retry_after = missing / self.rps
        return False, int(self.tokens), retry_after
    
    def is_stale(self, now: float) -> bool:
        """Check if bucket is stale and should be evicted."""
        return now - self.last_refill > self.ttl


class RateLimiter:
    """Rate limiter with token bucket per client."""
    
    def __init__(self, rps: float, burst: int, ttl: int = 600):
        self.rps = rps
        self.burst = burst
        self.ttl = ttl
        self._lock = threading.Lock()
        self._buckets: Dict[str, TokenBucket] = {}
        self._last_sweep = time.time()
    
    def allow(self, key: str) -> tuple[bool, int, float]:
        """Check if request is allowed for given key."""
        with self._lock:
            now = time.time()
            
            # Periodic sweep of stale buckets
            if now - self._last_sweep > self.ttl:
                self._buckets = {
                    k: v for k, v in self._buckets.items() 
                    if not v.is_stale(now)
                }
                self._last_sweep = now
            
            # Get or create bucket
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = TokenBucket(self.rps, self.burst, self.ttl)
                self._buckets[key] = bucket
            
            return bucket.allow()


def rate_limit_key(request: Request, config) -> str:
    """Get rate limiting key for request."""
    # Check if request has valid admin token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if config.admin_key_ok(token):
            return f"admin:{token}"
    
    # Use client IP
    client_ip = request.client.host if request.client else "unknown"
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        client_ip = xff.split(',')[0].strip()
    
    return f"ip:{client_ip}"


class RateLimitMiddleware:
    """Rate limiting middleware."""
    
    def __init__(self, app, config=None):
        self.app = app
        self.config = config
        # Different limiters for different endpoints
        self.fast_limiter = RateLimiter(5.0, 10)  # validate/heartbeat
        self.admin_limiter = RateLimiter(1.0, 3)  # issue/revoke
        self.default_limiter = RateLimiter(2.0, 5)  # everything else
    
    def get_limiter(self, path: str) -> RateLimiter:
        """Get appropriate limiter for path."""
        if path in ["/api/v1/licenses/validate", "/api/v1/licenses/heartbeat"]:
            return self.fast_limiter
        elif path in ["/api/v1/licenses/issue", "/api/v1/licenses/revoke"]:
            return self.admin_limiter
        else:
            return self.default_limiter
    
    async def __call__(self, scope, receive, send):
        """Apply rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Get config from global variable if not provided
        config = self.config
        if config is None:
            from python_raalisence.server import config as global_config
            config = global_config
        
        if config is None:
            # No config available, skip rate limiting
            await self.app(scope, receive, send)
            return
        
        key = rate_limit_key(request, config)
        limiter = self.get_limiter(request.url.path)
        
        allowed, remaining, retry_after = limiter.allow(key)
        
        if not allowed:
            from starlette.responses import Response
            response = Response(
                content="rate limit exceeded",
                status_code=429,
                headers={
                    "Retry-After": str(int(retry_after)),
                    "RateLimit-Limit": "1",
                    "RateLimit-Remaining": str(remaining)
                }
            )
            await response(scope, receive, send)
            return
        
        # Add rate limit headers to response
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"ratelimit-limit"] = b"1"
                headers[b"ratelimit-remaining"] = str(remaining).encode()
                message["headers"] = list(headers.items())
            await send(message)
        
        await self.app(scope, receive, send_with_headers)

