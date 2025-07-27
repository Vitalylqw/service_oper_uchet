@echo off
title Auth Debug
echo Debugging authentication...
echo.
call d:\work_d\Projects\service_oper_uchet\venv\Scripts\activate.bat
python scripts/debug_auth.py
echo.
pause 