@echo off
REM Run tests for the Python license server

echo Running tests...

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: pytest is not installed
    echo Install it with: pip install pytest pytest-asyncio
    exit /b 1
)

REM Run tests
python -m pytest tests/ -v

if %errorlevel% neq 0 (
    echo Error: Tests failed
    exit /b 1
)

echo Tests completed successfully!

