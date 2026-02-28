@echo off
REM QA Suite - Clear Test Database
REM ===============================

echo ========================================
echo QA Suite - Database Cleanup
echo ========================================
echo.

cd /d "%~dp0.."

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

echo WARNING: This will delete all test data from the database!
echo.
set /p confirm="Are you sure you want to continue? (y/N): "

if /i not "%confirm%"=="y" (
    echo Cancelled.
    exit /b 0
)

echo.
echo Clearing database...

python run_tests.py --clear-db-only

if %ERRORLEVEL% neq 0 (
    echo.
    echo Failed to clear database.
    exit /b %ERRORLEVEL%
)

echo.
echo Database cleared successfully.
exit /b 0
