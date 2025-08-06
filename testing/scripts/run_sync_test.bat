@echo off
REM Run sync integration test with proper Python path

echo Starting sync integration test...

REM Change to project root directory
cd /d "%~dp0..\.."

REM Set PYTHONPATH to include src directory
set PYTHONPATH=%PYTHONPATH%;%CD%\src

REM Run the test script
python testing\scripts\test_sync_integration.py %*

echo Test completed.
pause 