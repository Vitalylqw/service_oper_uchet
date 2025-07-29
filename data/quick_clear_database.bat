@echo off
echo ========================================
echo Quick Database Cleanup (Auto-confirm)
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

echo Running quick database cleanup with backup...
python database_cleanup\clear_database.py --confirm

REM Check if the script completed successfully
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Quick cleanup completed successfully!
) else (
    echo.
    echo ❌ Quick cleanup failed!
    echo Check the log file: database_cleanup.log
)

echo.
echo Press any key to exit...
pause >nul