"""Logging middleware."""

import time
import uuid
from datetime import datetime, timezone
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for request/response tracking."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()
        
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            client_ip = xff.split(',')[0].strip()
        
        # Log request
        timestamp = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat()
        print(f"ts={timestamp} req_id={request_id} method={request.method} path={request.url.path} "
              f"status={response.status_code} bytes={len(response.body) if hasattr(response, 'body') else 0} "
              f"dur={duration:.6f}s remote={client_ip}")
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response

