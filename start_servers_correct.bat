@echo off
echo ========================================
echo   ЗАПУСК СЕРВЕРОВ (ПРАВИЛЬНАЯ ВЕРСИЯ)
echo ========================================
echo.

REM Активируем виртуальное окружение
call "%~dp0venv\Scripts\activate.bat"

echo Запускаем API сервер...
start "API Server" cmd /k "python -m uvicorn src.presentation.api.main:app --reload --host 0.0.0.0 --port 8000"

echo Ждем 3 секунды...
timeout /t 3 /nobreak >nul

echo Запускаем React UI...
start "React UI" cmd /k "cd src\presentation\web && npm start"

echo.
echo ✅ Серверы запущены!
echo 🌐 API: http://localhost:8000
echo 🌐 UI:  http://localhost:3000
echo.
echo Нажмите любую клавишу для выхода...
pause >nul