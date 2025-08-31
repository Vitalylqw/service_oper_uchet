@echo off
cd /d "%~dp0"
echo Debugging Decimal serialization issue...
python debug_decimal_serialization.py
pause
