@echo off
echo Запуск в CMD для обхода проблем с PowerShell...
echo.

REM Запуск cmd с командами
cmd /k "echo Активация виртуального окружения... && call venv\Scripts\activate.bat && echo Запуск API сервера... && python -m uvicorn src.presentation.api.main:app --host 127.0.0.1 --port 8000 --reload" 