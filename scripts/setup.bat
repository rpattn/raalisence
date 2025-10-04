@echo off
REM Setup script for Python raalisence

echo Setting up Python raalisence...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from https://python.org
    exit /b 1
)

echo Python found. Installing dependencies...

REM Install dependencies
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    echo Try running: pip install --upgrade pip
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo Next steps:
echo 1. Generate signing keys: scripts\gen_keys.bat
echo 2. Create config file: copy config.example.yaml config.yaml
echo 3. Edit config.yaml with your keys
echo 4. Run the server: scripts\run.bat
