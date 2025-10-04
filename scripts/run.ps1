# Run the Python license server

Write-Host "Starting Python raalisence server..." -ForegroundColor Green

# Check if config file exists
if (-not (Test-Path "config.yaml")) {
    Write-Host "Warning: config.yaml not found" -ForegroundColor Yellow
    Write-Host "Please create a config file or use environment variables" -ForegroundColor Yellow
    Write-Host ""
}

# Run the server
python -m python_raalisence.server

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Server failed to start" -ForegroundColor Red
    exit 1
}

