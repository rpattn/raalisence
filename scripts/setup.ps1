# Setup script for Python raalisence

Write-Host "Setting up Python raalisence..." -ForegroundColor Green

# Check if Python is available
try {
    python --version | Out-Null
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.9 or higher from https://python.org" -ForegroundColor Yellow
    exit 1
}

Write-Host "Python found. Installing dependencies..." -ForegroundColor Green

# Install dependencies
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install dependencies" -ForegroundColor Red
    Write-Host "Try running: pip install --upgrade pip" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Generate signing keys: scripts\gen_keys.ps1" -ForegroundColor White
Write-Host "2. Create config file: copy config.example.yaml config.yaml" -ForegroundColor White
Write-Host "3. Edit config.yaml with your keys" -ForegroundColor White
Write-Host "4. Run the server: scripts\run.ps1" -ForegroundColor White
