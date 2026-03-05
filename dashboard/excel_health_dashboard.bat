@echo off
REM Excel Health Dashboard
REM Runs health check and Excel vs DB comparison, saves HTML report to dashboard/reports/
REM
REM Usage examples:
REM   excel_health_dashboard.bat
REM   excel_health_dashboard.bat --periods "Январь 2025" "Февраль 2025"
REM   excel_health_dashboard.bat --excel-path path\to\file.xlsx --no-browser

cd /d "%~dp0.."

python dashboard\excel_health_dashboard.py %*

if errorlevel 1 (
    echo.
    echo ERROR: Report generation failed. Check logs above.
    pause
) else (
    echo.
    echo Done.
)
