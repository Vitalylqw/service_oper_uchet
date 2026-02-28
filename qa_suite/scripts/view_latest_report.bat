@echo off
REM QA Suite - View Latest Report
REM ==============================

echo ========================================
echo QA Suite - View Latest Report
echo ========================================
echo.

cd /d "%~dp0.."

set REPORT_PATH=reports\latest_report.html

if not exist "%REPORT_PATH%" (
    echo No reports found. Run tests first using run_all_tests.bat
    exit /b 1
)

echo Opening latest report in browser...
start "" "%REPORT_PATH%"

exit /b 0
