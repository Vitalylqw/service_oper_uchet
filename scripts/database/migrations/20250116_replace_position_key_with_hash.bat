@echo off
echo Running migration: Replace position_key unique constraint with hash_key
echo.

cd /d "D:\work_d\Projects\service_oper_uchet"

python scripts/database/migrations/20250116_replace_position_key_with_hash.py

echo.
echo Migration completed!
pause