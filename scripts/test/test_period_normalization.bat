@echo off
cd /workspaces/service_oper_uchet
set PYTHONPATH=/workspaces/service_oper_uchet/src
python scripts/test/test_period_normalization.py
pause
