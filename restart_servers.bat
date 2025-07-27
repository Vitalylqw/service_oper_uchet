@echo off
title Restart All Servers - Service Oper Uchet
echo ========================================
echo   RESTART ALL SERVERS
echo ========================================
echo.

echo 1. Stop current servers (Ctrl+C in each window)
echo 2. Then run:
echo.

echo API Server:
echo    start_api_server.bat
echo.

echo React UI:
echo    start_react_ui.bat
echo.

echo After startup open:
echo    http://localhost:3000
echo.

echo Login: admin / password
echo.

echo Dashboard should show:
echo    - 15 real deals from Excel
echo    - Clients: LENTEKHSTROJ, BALTINVESTSTROJ, Rigel
echo    - Periods: May 2025, June 2025
echo    - 1 successful sync session
echo.

echo ========================================
pause 