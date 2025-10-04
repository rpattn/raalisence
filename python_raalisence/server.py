"""Main server application."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
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
from python_raalisence.middleware.auth import create_admin_auth_dependency
from python_raalisence.middleware.logging import LoggingMiddleware
from python_raalisence.middleware.ratelimit import RateLimitMiddleware


# Global variables
config: Config = None
db: DatabaseConnection = None
admin_auth_dependency = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global config, db, admin_auth_dependency
    
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
    admin_auth_dependency = create_admin_auth_dependency(config)
    
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
    if db is None:
        raise HTTPException(status_code=500, detail="database not initialized")
    return db


# Config dependency
def get_config() -> Config:
    """Get configuration."""
    if config is None:
        raise HTTPException(status_code=500, detail="configuration not initialized")
    return config


# Routes
@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return await health_check()


def get_admin_auth_dependency():
    """Get admin authentication dependency for FastAPI."""
    if admin_auth_dependency is None:
        raise HTTPException(status_code=500, detail="server not ready")
    return admin_auth_dependency

def admin_auth_dep(request: Request) -> str:
    """Admin authentication dependency function."""
    if admin_auth_dependency is None:
        raise HTTPException(status_code=500, detail="server not ready")
    return admin_auth_dependency(request)


@app.post("/api/v1/licenses/issue")
async def issue_license_endpoint(
    request: IssueRequest,
    _: str = Depends(admin_auth_dep),
    db_conn: DatabaseConnection = Depends(get_db),
    cfg: Config = Depends(get_config)
):
    """Issue a new license."""
    return await issue_license(request, db_conn, cfg)


@app.post("/api/v1/licenses/revoke")
async def revoke_license_endpoint(
    request: LicenseKeyRequest,
    _: str = Depends(admin_auth_dep),
    db_conn: DatabaseConnection = Depends(get_db),
    cfg: Config = Depends(get_config)
):
    """Revoke a license."""
    return await revoke_license(request, db_conn, cfg)


@app.post("/api/v1/licenses/validate")
async def validate_license_endpoint(
    request: ValidateRequest,
    db_conn: DatabaseConnection = Depends(get_db),
    cfg: Config = Depends(get_config)
):
    """Validate a license."""
    return await validate_license(request, db_conn, cfg)


@app.post("/api/v1/licenses/heartbeat")
async def heartbeat_endpoint(
    request: LicenseKeyRequest,
    db_conn: DatabaseConnection = Depends(get_db),
    cfg: Config = Depends(get_config)
):
    """Update license heartbeat."""
    return await heartbeat(request, db_conn, cfg)


@app.post("/api/v1/licenses/update")
async def update_license_endpoint(
    request: UpdateLicenseRequest,
    _: str = Depends(admin_auth_dep),
    db_conn: DatabaseConnection = Depends(get_db),
    cfg: Config = Depends(get_config)
):
    """Update a license."""
    return await update_license(request, db_conn, cfg)


@app.get("/api/v1/licenses")
async def list_licenses_endpoint(
    _: str = Depends(admin_auth_dep),
    db_conn: DatabaseConnection = Depends(get_db),
    cfg: Config = Depends(get_config)
):
    """List all licenses."""
    return await list_licenses(db_conn, cfg)


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

