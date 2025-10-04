@echo off
REM Stop PostgreSQL database

echo Stopping PostgreSQL database...

REM Stop and remove container
docker stop raalisence-postgres >nul 2>&1
docker rm raalisence-postgres >nul 2>&1

echo PostgreSQL stopped successfully!

