# Run tests for the Python license server

Write-Host "Running tests..." -ForegroundColor Green

# Check if pytest is available
try {
    python -m pytest --version | Out-Null
} catch {
    Write-Host "Error: pytest is not installed" -ForegroundColor Red
    Write-Host "Install it with: pip install pytest pytest-asyncio" -ForegroundColor Yellow
    exit 1
}

# Run tests
python -m pytest tests/ -v

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Tests failed" -ForegroundColor Red
    exit 1
}

Write-Host "Tests completed successfully!" -ForegroundColor Green

