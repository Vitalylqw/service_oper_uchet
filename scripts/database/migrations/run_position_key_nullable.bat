@echo off
cd /d "D:\work_d\Projects\service_oper_uchet"
echo Running migration: Make position_key nullable...
python scripts/database/migrations/20250116_make_position_key_nullable.py
pause