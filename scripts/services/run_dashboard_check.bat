@echo off
cd /d "%~dp0..\.."
python scripts/services/run_dashboard_check.py %*
pause
