"""Authentication middleware."""

import time
import threading
from typing import Dict, Optional
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from python_raalisence.config.config import Config


class FailureState:
    """Track failure state for rate limiting."""
    
    def __init__(self):
        self.count = 0
        self.last_time = time.time()
        self.alerted = False


class FailureTracker:
    """Track authentication failures."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._states: Dict[str, FailureState] = {}
        self.failure_window = 600  # 10 minutes
        self.failure_threshold = 5
    
    def record_failure(self, key: str) -> tuple[int, bool]:
        """Record a failure and return (count, should_alert)."""
        with self._lock:
            now = time.time()
            state = self._states.get(key)
            
            if state is None or now - state.last_time > self.failure_window:
                state = FailureState()
                self._states[key] = state
            
            state.count += 1
            state.last_time = now
            
            if state.count >= self.failure_threshold and not state.alerted:
                state.alerted = True
                return state.count, True
            
            return state.count, False
    
    def reset(self, key: str):
        """Reset failure count for a key."""
        with self._lock:
            self._states.pop(key, None)


failure_tracker = FailureTracker()


def admin_failure_key(request: Request) -> str:
    """Get the key for tracking admin failures."""
    # Check X-Forwarded-For header
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # Take first IP if multiple
        return xff.split(',')[0].strip()
    
    # Fall back to client IP
    return request.client.host if request.client else "unknown"


class AdminAuthBearer(HTTPBearer):
    """Admin authentication bearer token."""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
    
    async def __call__(self, request: Request) -> str:
        """Validate admin token."""
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            key = admin_failure_key(request)
            count, alert = failure_tracker.record_failure(key)
            if alert:
                print(f"ALERT admin_auth_failure remote={key} count={count} window={self.failure_window}s")
            raise HTTPException(status_code=401, detail="unauthorized")
        
        if not self.config.admin_key_ok(credentials.credentials):
            key = admin_failure_key(request)
            count, alert = failure_tracker.record_failure(key)
            if alert:
                print(f"ALERT admin_auth_failure remote={key} count={count} window={self.failure_window}s")
            raise HTTPException(status_code=401, detail="unauthorized")
        
        # Reset failure count on success
        key = admin_failure_key(request)
        failure_tracker.reset(key)
        
        return credentials.credentials

