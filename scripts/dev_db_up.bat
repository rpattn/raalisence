@echo off
REM Start PostgreSQL database for development

echo Starting PostgreSQL database...

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not installed or not in PATH
    echo Please install Docker Desktop for Windows
    exit /b 1
)

REM Start PostgreSQL container
docker run -d ^
    --name raalisence-postgres ^
    -e POSTGRES_DB=raalisence ^
    -e POSTGRES_USER=postgres ^
    -e POSTGRES_PASSWORD=postgres ^
    -p 5432:5432 ^
    postgres:15

if %errorlevel% neq 0 (
    echo Error: Failed to start PostgreSQL container
    exit /b 1
)

echo PostgreSQL started successfully!
echo Connection string: postgresql://postgres:postgres@localhost:5432/raalisence
echo.
echo To stop the database, run: scripts\dev_db_down.bat

