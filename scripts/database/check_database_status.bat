@echo off
echo ========================================
echo Database Status Check
echo ========================================
echo.

REM Change to the project root directory
cd /d "%~dp0..\.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the database status check script
echo Checking database status...
python scripts\database\check_database_status.py

echo.
pause 