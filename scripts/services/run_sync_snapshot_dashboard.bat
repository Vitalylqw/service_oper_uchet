@echo off
cd /d "%~dp0..\.."
python scripts/services/run_sync_snapshot_dashboard.py %*
pause
