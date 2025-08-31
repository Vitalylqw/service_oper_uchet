@echo off
REM Database initialization script for Service Oper Uchet
REM Creates database, applies migrations, and sets up initial data

echo Starting database initialization...

REM Change to project directory
cd /d "%~dp0\..\.."

REM Run database initialization script
python scripts/services/init_database.py

if %ERRORLEVEL% EQU 0 (
    echo Database initialization completed successfully!
) else (
    echo Database initialization failed!
    pause
)
