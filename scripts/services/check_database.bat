@echo off
REM Database health check script for Service Oper Uchet
REM Tests database connectivity and reports status

echo Starting database health check...

REM Change to project directory
cd /d "%~dp0\..\.."

REM Run database health check script
python scripts/services/check_database.py

if %ERRORLEVEL% EQU 0 (
    echo Database health check passed!
) else (
    echo Database health check failed!
    pause
)
