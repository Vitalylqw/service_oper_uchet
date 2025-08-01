@echo off
REM Reset SQLite database (clean recreation, variant A)
python %~dp0\reset_database.py %*
