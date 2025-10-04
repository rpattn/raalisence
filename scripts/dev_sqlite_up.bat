@echo off
REM Create SQLite database for development

echo Setting up SQLite database for development...

REM Set environment variables for SQLite
set RAAL_DB_DRIVER=sqlite3
set RAAL_DB_PATH=.\raalisence.db

echo SQLite database configuration:
echo Driver: %RAAL_DB_DRIVER%
echo Path: %RAAL_DB_PATH%
echo.
echo To run with SQLite, use these environment variables or update config.yaml

