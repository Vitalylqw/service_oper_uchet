@echo off
cd /d "%~dp0"
echo Testing deterministic ID generation...
python test_deterministic_ids.py
pause
