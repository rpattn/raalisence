# Create SQLite database for development

Write-Host "Setting up SQLite database for development..." -ForegroundColor Green

# Set environment variables for SQLite
$env:RAAL_DB_DRIVER = "sqlite3"
$env:RAAL_DB_PATH = ".\raalisence.db"

Write-Host "SQLite database configuration:" -ForegroundColor Cyan
Write-Host "Driver: $env:RAAL_DB_DRIVER" -ForegroundColor White
Write-Host "Path: $env:RAAL_DB_PATH" -ForegroundColor White
Write-Host ""
Write-Host "To run with SQLite, use these environment variables or update config.yaml" -ForegroundColor Yellow

