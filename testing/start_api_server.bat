@echo off
chcp 65001 > nul
echo ========================================
echo    ЗАПУСК API СЕРВЕРА
echo ========================================
echo.

REM Активация виртуального окружения
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    echo Создайте виртуальное окружение: python -m venv venv
    pause
    exit /b 1
)

REM Проверка, не занят ли порт 8000
echo Проверка доступности порта 8000...
netstat -an | findstr :8000 > nul
if %ERRORLEVEL% equ 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Порт 8000 уже занят!
    echo Возможно, API сервер уже запущен.
    echo.
    echo Проверьте: http://localhost:8000/health/
    echo.
    pause
    exit /b 1
)

REM Запуск API сервера
echo Запуск FastAPI сервера...
echo.
echo Сервер будет доступен по адресу: http://localhost:8000
echo Swagger UI: http://localhost:8000/docs
echo Health check: http://localhost:8000/health/
echo.
echo Для остановки сервера нажмите Ctrl+C
echo.

python -m uvicorn src.presentation.api.main:app --host 127.0.0.1 --port 8000 --reload 