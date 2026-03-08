@echo off
cd /d "%~dp0\..\.."
python scripts/test/test_postgres_connection.py %*
