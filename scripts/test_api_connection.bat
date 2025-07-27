@echo off
title API Connection Test
echo Testing API connection...
echo.
call d:\work_d\Projects\service_oper_uchet\venv\Scripts\activate.bat
python -c "import requests; r=requests.get('http://localhost:8000/health/', timeout=5); print(f'✅ Server Status: {r.status_code}'); print(f'Response: {r.json()}')" 2>nul && echo. && echo ✅ API is working! || echo ❌ API not responding
echo.
echo Testing auth endpoint...
python -c "import requests; r=requests.post('http://localhost:8000/auth/login', json={'username': 'admin', 'password': 'password'}, timeout=5); print(f'Auth Status: {r.status_code}'); token=r.json().get('access_token',''); print(f'Token received: {len(token) > 0}')" 2>nul && echo ✅ Auth working! || echo ❌ Auth not working
echo.
pause 