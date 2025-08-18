@echo off
echo Testing PostgreSQL connection...
cd /d "%~dp0\.."
python scripts/test_postgres_connection.py
pause
