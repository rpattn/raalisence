@echo off
REM Generate signing keys for development

echo Generating ECDSA signing keys...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Run key generation script
python scripts\gen_keys.py

if %errorlevel% neq 0 (
    echo Error: Failed to generate keys
    exit /b 1
)

echo.
echo Keys generated successfully!
echo Copy the keys above to your config.yaml file.

