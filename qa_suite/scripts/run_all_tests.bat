@echo off
REM QA Suite - Run All Integration Tests
REM =====================================

echo ========================================
echo QA Suite - Integration Test Runner
echo ========================================
echo.

cd /d "%~dp0.."

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

REM Run all tests
echo Running all test scenarios...
echo.

python run_tests.py %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Tests completed with failures.
    exit /b %ERRORLEVEL%
)

echo.
echo All tests completed successfully.
exit /b 0
