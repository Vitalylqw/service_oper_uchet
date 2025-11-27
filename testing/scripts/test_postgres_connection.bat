@echo off
REM Simple PostgreSQL connection test
REM This tests basic connectivity without running full synchronization

echo Starting PostgreSQL connection test...

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please install Python or add it to PATH
    pause
    exit /b 1
)

REM Change to script directory
cd /d "%~dp0"

REM Run the connection test
echo Running PostgreSQL connection test...
python test_postgres_connection.py

REM Check exit code
if errorlevel 1 (
    echo.
    echo Test failed with exit code %errorlevel%
    pause
    exit /b 1
) else (
    echo.
    echo Test completed successfully
)

pause




