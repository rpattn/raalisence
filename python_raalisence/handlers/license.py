"""License management HTTP handlers."""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from python_raalisence.database.connection import DatabaseConnection
from python_raalisence.config.config import Config
from python_raalisence.crypto.sign import sign_json


class IssueRequest(BaseModel):
    customer: str
    machine_id: str
    expires_at: datetime
    features: Dict[str, Any] = {}


class LicenseFile(BaseModel):
    customer: str
    machine_id: str
    license_key: str
    expires_at: datetime
    features: Dict[str, Any]
    issued_at: datetime
    signature: str
    public_key_pem: str


class ValidateRequest(BaseModel):
    license_key: str
    machine_id: str


class ValidateResponse(BaseModel):
    valid: bool
    revoked: bool = False
    expires_at: datetime
    reason: Optional[str] = None


class UpdateLicenseRequest(BaseModel):
    license_key: str
    expires_at: Optional[str] = None
    features: Optional[Dict[str, Any]] = None


class LicenseSummary(BaseModel):
    id: str
    license_key: str
    customer: str
    machine_id: str
    expires_at: str
    revoked: bool
    last_seen_at: Optional[str] = None
    features: Optional[Dict[str, Any]] = None


class ListLicensesResponse(BaseModel):
    licenses: list[LicenseSummary]


async def issue_license(request: IssueRequest, db: DatabaseConnection, config: Config) -> LicenseFile:
    """Issue a new license."""
    if not request.customer or not request.machine_id or not request.expires_at:
        raise HTTPException(status_code=400, detail="customer, machine_id, expires_at required")
    
    license_key = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Insert license into database
    features_json = json.dumps(request.features)
    
    if db.config.db_driver == "sqlite3":
        expires_str = request.expires_at.isoformat()
        db.execute("""
            INSERT INTO licenses (id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, NULL, datetime('now'), datetime('now'))
        """, (str(uuid.uuid4()), license_key, request.customer, request.machine_id, features_json, expires_str))
    else:
        db.execute("""
            INSERT INTO licenses (id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, NULL, NOW(), NOW())
        """, (str(uuid.uuid4()), license_key, request.customer, request.machine_id, features_json, request.expires_at))
    
    db.commit()
    
    # Sign the license
    private_key = config.private_key()
    
    payload = {
        "customer": request.customer,
        "machine_id": request.machine_id,
        "license_key": license_key,
        "expires_at": request.expires_at.isoformat(),
        "issued_at": now.isoformat(),
        "features": request.features,
    }
    
    signature = sign_json(private_key, payload)
    
    return LicenseFile(
        customer=request.customer,
        machine_id=request.machine_id,
        license_key=license_key,
        expires_at=request.expires_at,
        features=request.features,
        issued_at=now,
        signature=signature,
        public_key_pem=config.signing_public_key_pem
    )


async def revoke_license(request: ValidateRequest, db: DatabaseConnection) -> Dict[str, bool]:
    """Revoke a license."""
    if not request.license_key:
        raise HTTPException(status_code=400, detail="license_key required")
    
    if db.config.db_driver == "sqlite3":
        cursor = db.execute("""
            UPDATE licenses SET revoked = 1, updated_at = datetime('now') WHERE license_key = ?
        """, (request.license_key,))
    else:
        cursor = db.execute("""
            UPDATE licenses SET revoked = TRUE, updated_at = NOW() WHERE license_key = %s
        """, (request.license_key,))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="not found")
    
    db.commit()
    return {"ok": True}


async def validate_license(request: ValidateRequest, db: DatabaseConnection, config: Config) -> ValidateResponse:
    """Validate a license."""
    if not request.license_key or not request.machine_id:
        raise HTTPException(status_code=400, detail="license_key and machine_id required")
    
    if db.config.db_driver == "sqlite3":
        row = db.execute_fetchone("""
            SELECT revoked, expires_at, machine_id FROM licenses WHERE license_key = ?
        """, (request.license_key,))
        
        if not row:
            return ValidateResponse(valid=False, expires_at=datetime.min, reason="unknown license")
        
        revoked = bool(row[0])
        expires_str = row[1]
        machine_id = row[2]
        
        # Parse expires_at
        try:
            expires_at = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            expires_at = expires_at.replace(tzinfo=None)  # Convert to naive
        except ValueError:
            raise HTTPException(status_code=500, detail="bad expires_at format")
    else:
        row = db.execute_fetchone("""
            SELECT revoked, expires_at, machine_id FROM licenses WHERE license_key = %s
        """, (request.license_key,))
        
        if not row:
            return ValidateResponse(valid=False, expires_at=datetime.min, reason="unknown license")
        
        revoked = bool(row[0])
        expires_at = row[1]
        machine_id = row[2]
        
        # Ensure PostgreSQL datetime is also naive
        if isinstance(expires_at, datetime) and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
    
    if machine_id != request.machine_id:
        return ValidateResponse(valid=False, expires_at=expires_at, reason="machine mismatch")
    
    if revoked:
        return ValidateResponse(valid=False, revoked=True, expires_at=expires_at, reason="revoked")
    
    # Ensure both datetimes are naive for comparison
    now = datetime.utcnow()
    if isinstance(expires_at, datetime) and expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)  # Convert to naive
    
    if now > expires_at:
        return ValidateResponse(valid=False, expires_at=expires_at, reason="expired")
    
    return ValidateResponse(valid=True, revoked=False, expires_at=expires_at)


async def heartbeat(request: ValidateRequest, db: DatabaseConnection) -> Dict[str, bool]:
    """Update license heartbeat."""
    if not request.license_key:
        raise HTTPException(status_code=400, detail="license_key required")
    
    if db.config.db_driver == "sqlite3":
        cursor = db.execute("""
            UPDATE licenses SET last_seen_at = datetime('now'), updated_at = datetime('now') WHERE license_key = ?
        """, (request.license_key,))
    else:
        cursor = db.execute("""
            UPDATE licenses SET last_seen_at = NOW(), updated_at = NOW() WHERE license_key = %s
        """, (request.license_key,))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="not found")
    
    db.commit()
    return {"ok": True}


async def update_license(request: UpdateLicenseRequest, db: DatabaseConnection, config: Config) -> Dict[str, bool]:
    """Update a license."""
    if not request.license_key:
        raise HTTPException(status_code=400, detail="license_key required")
    
    updates = []
    params = []
    
    if request.expires_at:
        try:
            parsed = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
            parsed = parsed.replace(tzinfo=None)  # Remove timezone for consistency
        except ValueError:
            raise HTTPException(status_code=400, detail="expires_at must be RFC3339")
        
        if db.config.db_driver == "sqlite3":
            updates.append("expires_at = ?")
            params.append(parsed.isoformat())
        else:
            updates.append("expires_at = %s")
            params.append(parsed)
    
    if request.features is not None:
        features_json = json.dumps(request.features)
        if db.config.db_driver == "sqlite3":
            updates.append("features = ?")
            params.append(features_json)
        else:
            updates.append("features = %s::jsonb")
            params.append(features_json)
    
    if not updates:
        raise HTTPException(status_code=400, detail="no updates requested")
    
    # Add updated_at
    if db.config.db_driver == "sqlite3":
        updates.append("updated_at = datetime('now')")
    else:
        updates.append("updated_at = NOW()")
    
    params.append(request.license_key)
    
    query = f"UPDATE licenses SET {', '.join(updates)} WHERE license_key = {'?' if db.config.db_driver == 'sqlite3' else '%s'}"
    
    cursor = db.execute(query, tuple(params))
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="not found")
    
    db.commit()
    return {"ok": True}


async def list_licenses(db: DatabaseConnection, config: Config) -> ListLicensesResponse:
    """List all licenses."""
    cursor = db.execute_fetchall("""
        SELECT id, license_key, customer, machine_id, features, expires_at, revoked, last_seen_at 
        FROM licenses ORDER BY created_at DESC
    """)
    
    licenses = []
    for row in cursor:
        if db.config.db_driver == "sqlite3":
            features = json.loads(row[4]) if row[4] else {}
            expires_at = row[5]
            last_seen_at = row[7] if row[7] else None
        else:
            features = row[4] if row[4] else {}
            expires_at = row[5].isoformat()
            last_seen_at = row[7].isoformat() if row[7] else None
        
        licenses.append(LicenseSummary(
            id=str(row[0]),
            license_key=row[1],
            customer=row[2],
            machine_id=row[3],
            expires_at=expires_at,
            revoked=bool(row[6]),
            last_seen_at=last_seen_at,
            features=features
        ))
    
    return ListLicensesResponse(licenses=licenses)
