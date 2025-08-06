@echo off
echo Running migration: Restructure read_positions table...
echo.
echo This migration will:
echo 1. Remove position_key column 
echo 2. Add position_number column
echo 3. Update indexes accordingly
echo.
python scripts/database/migrations/20250120_restructure_positions.py
echo.
echo Migration completed.
pause