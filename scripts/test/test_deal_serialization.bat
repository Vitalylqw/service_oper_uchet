@echo off
cd /d "%~dp0..\.."
python scripts/test/test_deal_serialization.py
pause

