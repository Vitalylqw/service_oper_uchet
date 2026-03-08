@echo off
cd /d "%~dp0\..\.."
python scripts/test/test_sync_integration.py %*
