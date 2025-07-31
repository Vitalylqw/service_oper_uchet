@echo off
echo Starting sync session...
echo.

REM Check if file path provided
if "%~1"=="" (
    echo Usage: run_sync_session.bat ^<excel_file_path^> [full^|incremental]
    echo Example: run_sync_session.bat data/excel/Data_source_excel.xlsx full
    pause
    exit /b 1
)

REM Set sync type (default: full)
set SYNC_TYPE=%~2
if "%SYNC_TYPE%"=="" set SYNC_TYPE=full

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run sync script
echo Running sync for: %~1 (type: %SYNC_TYPE%)
python scripts/services/run_sync_once.py "%~1" %SYNC_TYPE%

echo.
echo Sync session completed.
pause 