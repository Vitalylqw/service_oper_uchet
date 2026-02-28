@echo off
cd /d "%~dp0..\.."
python scripts/services/generate_dashboard.py %*
pause
