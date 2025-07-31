@echo off
cd /d "%~dp0\..\.."
python -m pytest scripts/test/test_excel_validation.py -v
pause 