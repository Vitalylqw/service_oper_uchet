@echo off
echo ========================================
echo Fix Empty Periods Migration
echo ========================================
echo.

cd /d "%~dp0\..\.."

echo Starting migration to fix events with empty periods...
python scripts/migrations/fix_empty_periods_migration.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Migration completed successfully!
) else (
    echo.
    echo ❌ Migration failed!
)

pause