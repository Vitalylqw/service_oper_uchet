@echo off
cd /d "%~dp0..\.."
python scripts/services/create_db_snapshot.py %*
pause
