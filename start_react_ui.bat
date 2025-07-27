@echo off
title React UI - Service Oper Uchet
echo ========================================
echo   React UI - Service Oper Uchet  
echo ========================================
echo.
echo Changing to web directory...
cd /d "%~dp0src\presentation\web"
echo.
echo Installing dependencies (if needed)...
call npm install
echo.
echo Starting React development server...
echo UI will be available at: http://localhost:3000
echo Press CTRL+C to stop
echo.
echo ========================================
call npm run dev
echo.
echo React UI stopped!
pause 