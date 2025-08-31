@echo off
REM Interactive test script for sync integration

echo Starting interactive sync integration test...
echo.

cd /d "%~dp0"
python test_sync_integration.py --interactive

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Test completed successfully!
) else (
    echo.
    echo Test failed with error code: %ERRORLEVEL%
)

pause

