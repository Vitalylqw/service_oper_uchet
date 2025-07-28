@echo off
echo ========================================
echo Database Cleanup Script
echo ========================================
echo.

REM Change to the project root directory
cd /d "%~dp0..\.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the database cleanup script
echo Running database cleanup...
python scripts\database\clear_database.py

REM Check if the script completed successfully
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Database cleanup completed successfully!
) else (
    echo.
    echo ❌ Database cleanup failed!
    pause
)

pause 