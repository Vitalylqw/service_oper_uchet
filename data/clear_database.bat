@echo off
echo ========================================
echo Enhanced Database Cleanup Script
echo ========================================
echo.

REM Check if database exists
if not exist "service_oper_uchet.sqlite" (
    echo ERROR: Database file not found!
    echo Expected: service_oper_uchet.sqlite
    pause
    exit /b 1
)

REM Activate virtual environment if it exists
if exist "..\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ..\venv\Scripts\activate.bat
)

echo.
echo Available options:
echo 1. Show database statistics only
echo 2. Clean database with backup (default)
echo 3. Clean database without backup
echo 4. Clean database with auto-confirm (no prompts)
echo.
set /p choice="Select option (1-4): "

if "%choice%"=="1" (
    echo.
    echo Running database statistics...
    python database_cleanup\clear_database.py --stats-only
) else if "%choice%"=="2" (
    echo.
    echo Running database cleanup with backup...
    python database_cleanup\clear_database.py
) else if "%choice%"=="3" (
    echo.
    echo Running database cleanup without backup...
    python database_cleanup\clear_database.py --no-backup
) else if "%choice%"=="4" (
    echo.
    echo Running database cleanup with auto-confirm...
    python database_cleanup\clear_database.py --confirm
) else (
    echo Invalid choice. Using default option (with backup)...
    python database_cleanup\clear_database.py
)

REM Check if the script completed successfully
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Database operation completed successfully!
) else (
    echo.
    echo ❌ Database operation failed!
    echo Check the log file: database_cleanup.log
)

echo.
echo Press any key to exit...
pause >nul