"""Tests for license handlers."""

import pytest
from datetime import datetime, timedelta, timezone
from python_raalisence.handlers.license import (
    issue_license, validate_license, revoke_license, heartbeat,
    update_license, list_licenses,
    IssueRequest, ValidateRequest, LicenseKeyRequest, UpdateLicenseRequest
)
from python_raalisence.database.connection import DatabaseConnection
from python_raalisence.config.config import Config


@pytest.fixture
def test_config():
    """Create test configuration."""
    from python_raalisence.crypto.sign import generate_pem_keys
    
    # Generate proper test keys
    private_pem, public_pem = generate_pem_keys()
    
    config = Config()
    config.db_driver = "sqlite3"
    config.db_path = ":memory:"
    config.admin_api_key = "test-admin-key"
    config.signing_private_key_pem = private_pem
    config.signing_public_key_pem = public_pem
    return config


@pytest.fixture
def test_db(test_config):
    """Create test database connection."""
    from python_raalisence.database.migrations import run_migrations
    db = DatabaseConnection(test_config)
    db.connect()
    run_migrations(db)
    yield db
    db.close()


@pytest.mark.asyncio
async def test_issue_license(test_db, test_config):
    """Test issuing a license."""
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    assert license_file.customer == "test-customer"
    assert license_file.machine_id == "test-machine"
    assert license_file.features == {"seats": 5}
    assert license_file.license_key is not None
    assert license_file.signature is not None


@pytest.mark.asyncio
async def test_validate_license_valid(test_db, test_config):
    """Test validating a valid license."""
    # First issue a license
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    # Now validate it
    validate_request = ValidateRequest(
        license_key=license_file.license_key,
        machine_id="test-machine"
    )
    
    response = await validate_license(validate_request, test_db, test_config)
    
    assert response.valid is True
    assert response.revoked is False
    assert response.reason is None


@pytest.mark.asyncio
async def test_validate_license_expired(test_db, test_config):
    """Test validating an expired license."""
    # Issue a license that's already expired
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    # Try to validate it
    validate_request = ValidateRequest(
        license_key=license_file.license_key,
        machine_id="test-machine"
    )
    
    response = await validate_license(validate_request, test_db, test_config)
    
    assert response.valid is False
    assert response.revoked is False
    assert response.reason == "expired"


@pytest.mark.asyncio
async def test_validate_license_wrong_machine(test_db, test_config):
    """Test validating a license with wrong machine ID."""
    # Issue a license
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    # Try to validate with wrong machine ID
    validate_request = ValidateRequest(
        license_key=license_file.license_key,
        machine_id="wrong-machine"
    )
    
    response = await validate_license(validate_request, test_db, test_config)
    
    assert response.valid is False
    assert response.revoked is False
    assert response.reason == "machine mismatch"


@pytest.mark.asyncio
async def test_validate_license_unknown(test_db, test_config):
    """Test validating an unknown license."""
    validate_request = ValidateRequest(
        license_key="unknown-key",
        machine_id="test-machine"
    )
    
    response = await validate_license(validate_request, test_db, test_config)
    
    assert response.valid is False
    assert response.revoked is False
    assert response.reason == "unknown license"


@pytest.mark.asyncio
async def test_revoke_license(test_db, test_config):
    """Test revoking a license."""
    # First issue a license
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    # Now revoke it
    revoke_request = LicenseKeyRequest(license_key=license_file.license_key)
    response = await revoke_license(revoke_request, test_db, test_config)
    
    assert response["ok"] is True
    
    # Verify it's revoked
    validate_request = ValidateRequest(
        license_key=license_file.license_key,
        machine_id="test-machine"
    )
    
    validation_response = await validate_license(validate_request, test_db, test_config)
    assert validation_response.valid is False
    assert validation_response.revoked is True
    assert validation_response.reason == "revoked"


@pytest.mark.asyncio
async def test_heartbeat(test_db, test_config):
    """Test license heartbeat."""
    # First issue a license
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    # Send heartbeat
    heartbeat_request = LicenseKeyRequest(license_key=license_file.license_key)
    response = await heartbeat(heartbeat_request, test_db, test_config)
    
    assert response["ok"] is True


@pytest.mark.asyncio
async def test_update_license(test_db, test_config):
    """Test updating a license."""
    # First issue a license
    request = IssueRequest(
        customer="test-customer",
        machine_id="test-machine",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        features={"seats": 5}
    )
    
    license_file = await issue_license(request, test_db, test_config)
    
    # Update the license
    new_expires = datetime.now(timezone.utc) + timedelta(days=60)
    update_request = UpdateLicenseRequest(
        license_key=license_file.license_key,
        expires_at=new_expires.isoformat(),
        features={"seats": 10}
    )
    
    response = await update_license(update_request, test_db, test_config)
    assert response["ok"] is True


@pytest.mark.asyncio
async def test_list_licenses(test_db, test_config):
    """Test listing licenses."""
    # Issue a few licenses
    for i in range(3):
        request = IssueRequest(
            customer=f"customer-{i}",
            machine_id=f"machine-{i}",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            features={"seats": i + 1}
        )
        await issue_license(request, test_db, test_config)
    
    # List all licenses
    response = await list_licenses(test_db, test_config)
    
    assert len(response.licenses) == 3
    assert all(license.customer.startswith("customer-") for license in response.licenses)
