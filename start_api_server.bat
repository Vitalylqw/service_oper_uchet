@echo off
title FastAPI Server - Service Oper Uchet
echo ========================================
echo   FastAPI Server - Service Oper Uchet
echo ========================================
echo.
echo Activating virtual environment...
call d:\work_d\Projects\service_oper_uchet\venv\Scripts\activate.bat
echo.
echo Starting FastAPI server on http://localhost:8000
echo Press CTRL+C to stop server
echo.
echo Demo credentials:
echo - admin / password (Administrator)
echo - analyst / password (Analyst)  
echo - viewer / password (Viewer)
echo.
echo ========================================
python -m uvicorn src.presentation.api.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo Server stopped!
pause 