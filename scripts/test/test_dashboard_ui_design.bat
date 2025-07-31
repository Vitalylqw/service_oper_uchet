@echo off
echo ==========================================
echo   ТЕСТ УЛУЧШЕННОГО ДИЗАЙНА DASHBOARD
echo ==========================================
echo.

cd /d "%~dp0..\.."
python scripts/test/test_dashboard_ui_design.py

echo.
echo Нажмите любую клавишу для выхода...
pause >nul