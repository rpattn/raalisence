"""Main server application."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from python_raalisence.config.config import Config
from python_raalisence.database.connection import DatabaseConnection
from python_raalisence.database.migrations import run_migrations
from python_raalisence.handlers.health import health_check
from python_raalisence.handlers.license import (
    issue_license, revoke_license, validate_license, heartbeat,
    update_license, list_licenses,
    IssueRequest, ValidateRequest, LicenseKeyRequest, UpdateLicenseRequest
)
from python_raalisence.middleware.auth import AdminAuthBearer
from python_raalisence.middleware.logging import LoggingMiddleware
from python_raalisence.middleware.ratelimit import RateLimitMiddleware


# Global variables
config: Config = None
db: DatabaseConnection = None
admin_auth = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global config, db, admin_auth
    
    # Startup
    config = Config.load()
    
    # Validate keys
    try:
        config.private_key()
        config.public_key()
    except Exception as e:
        print(f"Error loading signing keys: {e}")
        sys.exit(1)
    
    # Initialize database
    db = DatabaseConnection(config)
    db.connect()
    
    # Run migrations
    run_migrations(db)
    
    # Configure admin auth
    admin_auth = AdminAuthBearer(config)
    
    print(f"raalisence listening on {config.server_addr} (driver={config.db_driver})")
    
    yield
    
    # Shutdown
    if db:
        db.close()


# Create FastAPI app
app = FastAPI(title="raalisence", lifespan=lifespan)

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Database dependency
def get_db() -> DatabaseConnection:
    """Get database connection."""
    return db


# Routes
@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return await health_check()


def get_admin_auth():
    """Get admin authentication dependency."""
    if admin_auth is None:
        raise HTTPException(status_code=500, detail="server not ready")
    return admin_auth


@app.post("/api/v1/licenses/issue")
async def issue_license_endpoint(
    request: IssueRequest,
    _: str = Depends(get_admin_auth),
    db_conn: DatabaseConnection = Depends(get_db)
):
    """Issue a new license."""
    return await issue_license(request, db_conn, config)


@app.post("/api/v1/licenses/revoke")
async def revoke_license_endpoint(
    request: LicenseKeyRequest,
    _: str = Depends(get_admin_auth),
    db_conn: DatabaseConnection = Depends(get_db)
):
    """Revoke a license."""
    return await revoke_license(request, db_conn)


@app.post("/api/v1/licenses/validate")
async def validate_license_endpoint(
    request: ValidateRequest,
    db_conn: DatabaseConnection = Depends(get_db)
):
    """Validate a license."""
    return await validate_license(request, db_conn, config)


@app.post("/api/v1/licenses/heartbeat")
async def heartbeat_endpoint(
    request: LicenseKeyRequest,
    db_conn: DatabaseConnection = Depends(get_db)
):
    """Update license heartbeat."""
    return await heartbeat(request, db_conn)


@app.post("/api/v1/licenses/update")
async def update_license_endpoint(
    request: UpdateLicenseRequest,
    _: str = Depends(get_admin_auth),
    db_conn: DatabaseConnection = Depends(get_db)
):
    """Update a license."""
    return await update_license(request, db_conn, config)


@app.get("/api/v1/licenses")
async def list_licenses_endpoint(
    _: str = Depends(get_admin_auth),
    db_conn: DatabaseConnection = Depends(get_db)
):
    """List all licenses."""
    return await list_licenses(db_conn, config)


# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Redirect to admin panel."""
    return RedirectResponse(url="/static/admin.html")


if __name__ == "__main__":
    import uvicorn
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print("Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load config for server address
    cfg = Config.load()
    host, port = cfg.server_addr.split(':') if ':' in cfg.server_addr else ('0.0.0.0', cfg.server_addr)
    
    uvicorn.run(app, host=host, port=int(port))

