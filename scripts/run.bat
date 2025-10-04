@echo off
REM Run the Python license server

echo Starting Python raalisence server...

REM Check if config file exists
if not exist config.yaml (
    echo Warning: config.yaml not found
    echo Please create a config file or use environment variables
    echo.
)

REM Run the server
python -m python_raalisence.server

if %errorlevel% neq 0 (
    echo Error: Server failed to start
    exit /b 1
)

