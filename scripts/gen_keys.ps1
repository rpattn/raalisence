# Generate signing keys for development

Write-Host "Generating ECDSA signing keys..." -ForegroundColor Green

# Check if Python is available
try {
    python --version | Out-Null
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Run key generation script
python scripts\gen_keys.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to generate keys" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Keys generated successfully!" -ForegroundColor Green
Write-Host "Copy the keys above to your config.yaml file." -ForegroundColor Yellow

