@echo off
echo ========================================
echo Database VACUUM Operation
echo ========================================
echo.
echo This will reclaim space from deleted data.
echo The operation may take several minutes...
echo.

REM Change to the project root directory
cd /d "%~dp0..\.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the VACUUM operation
echo Starting VACUUM operation...
python scripts\database\vacuum_database.py

REM Check if the operation completed successfully
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ VACUUM operation completed successfully!
) else (
    echo.
    echo ❌ VACUUM operation failed!
    pause
)

pause 