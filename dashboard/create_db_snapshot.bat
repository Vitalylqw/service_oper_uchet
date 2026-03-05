@echo off
cd /d "%~dp0.."
python dashboard/create_db_snapshot.py %*
pause
