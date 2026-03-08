@echo off
cd /d "%~dp0\..\.."
python scripts/test/test_excel_parsing.py %*
