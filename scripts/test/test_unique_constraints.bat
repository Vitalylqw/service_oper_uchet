@echo off
echo Testing unique constraints for read_positions table
echo.

python scripts/test/test_unique_constraints.py

echo.
echo Test completed. Press any key to exit.
pause >nul