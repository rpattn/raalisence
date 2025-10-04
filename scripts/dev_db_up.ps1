# Start PostgreSQL database for development

Write-Host "Starting PostgreSQL database..." -ForegroundColor Green

# Check if Docker is available
try {
    docker --version | Out-Null
} catch {
    Write-Host "Error: Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows" -ForegroundColor Yellow
    exit 1
}

# Start PostgreSQL container
$result = docker run -d `
    --name raalisence-postgres `
    -e POSTGRES_DB=raalisence `
    -e POSTGRES_USER=postgres `
    -e POSTGRES_PASSWORD=postgres `
    -p 5432:5432 `
    postgres:15

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to start PostgreSQL container" -ForegroundColor Red
    exit 1
}

Write-Host "PostgreSQL started successfully!" -ForegroundColor Green
Write-Host "Connection string: postgresql://postgres:postgres@localhost:5432/raalisence" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop the database, run: scripts\dev_db_down.ps1" -ForegroundColor Yellow

