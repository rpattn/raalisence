@echo off
REM Generate admin key hash

if "%1"=="" (
    echo Usage: %0 ^<admin-key^>
    echo Example: %0 my-secret-admin-key
    exit /b 1
)

echo Generating bcrypt hash for admin key: %1

python scripts\gen.py %1

if %errorlevel% neq 0 (
    echo Error: Failed to generate hash
    exit /b 1
)

