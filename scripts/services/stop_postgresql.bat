@echo off
REM Stop PostgreSQL container for Service Oper Uchet

echo Stopping PostgreSQL container...

REM Change to project directory
cd /d "%~dp0\..\.."

REM Stop PostgreSQL container
docker-compose -f docker-compose.db.yml stop postgres

if %ERRORLEVEL% EQU 0 (
    echo PostgreSQL container stopped successfully!
) else (
    echo Failed to stop PostgreSQL container!
    pause
)
