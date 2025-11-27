@echo off
REM Test script for sync integration
REM Usage: run_sync_test.bat [sync_type] [period_months] [log_level]

setlocal enabledelayedexpansion

REM Default values
set SYNC_TYPE=%~1
if "%SYNC_TYPE%"=="" set SYNC_TYPE=full

set PERIOD_MONTHS=%~2
if "%PERIOD_MONTHS%"=="" set PERIOD_MONTHS=12

set LOG_LEVEL=%~3
if "%LOG_LEVEL%"=="" set LOG_LEVEL=INFO

echo Running sync integration test...
echo Sync type: %SYNC_TYPE%
echo Period months: %PERIOD_MONTHS%
echo Log level: %LOG_LEVEL%
echo.

cd /d "%~dp0"
python test_sync_integration.py --sync-type %SYNC_TYPE% --period-months %PERIOD_MONTHS% --log-level %LOG_LEVEL%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Test completed successfully!
) else (
    echo.
    echo Test failed with error code: %ERRORLEVEL%
)

pause 