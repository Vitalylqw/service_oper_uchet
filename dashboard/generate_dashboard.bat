@echo off
cd /d "%~dp0.."
python dashboard/generate_dashboard.py %*
pause
