@echo off
REM Test synchronization integration with PostgreSQL
REM Usage: test_sync_integration_postgres.bat [options]

echo Starting PostgreSQL synchronization test...

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

REM Run the test script
echo Running PostgreSQL synchronization test...
python test_sync_integration.py %*

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




