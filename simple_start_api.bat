@echo off
echo Starting API Server...
echo.

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Запуск сервера
python -m uvicorn src.presentation.api.main:app --host 127.0.0.1 --port 8000 --reload

pause 