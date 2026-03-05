@echo off
cd /d "%~dp0.."
python dashboard/run_dashboard_check.py %*
pause
