@echo off
REM Test database schema and migration
echo Testing database schema...
cd /d "%~dp0\.."
python scripts/test_new_schema.py
pause







