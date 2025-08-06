@echo off
echo Applying migration: Add position unique constraints
echo.

python scripts/database/migrations/20250120_add_position_unique_constraints.py

echo.
echo Migration completed. Press any key to exit.
pause >nul