@echo off
cd /d "%~dp0.."
python dashboard/run_sync_snapshot_dashboard.py %*
pause
