@echo off
echo Cleaning up duplicate positions before applying unique constraints
echo.

python scripts/database/migrations/20250120_cleanup_duplicate_positions.py

echo.
echo Cleanup completed. Press any key to exit.
pause >nul