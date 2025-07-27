@echo off
echo ========================================
echo    ТЕСТ API СЕРВЕРА
echo ========================================
echo.

REM Активация виртуального окружения
if exist "venv\Scripts\Activate.ps1" (
    call venv\Scripts\Activate.ps1
) else (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    exit /b 1
)

REM Проверка, запущен ли API сервер
echo Проверка доступности API сервера...
netstat -an | findstr :8000 > nul
if %ERRORLEVEL% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] API сервер не запущен на порту 8000
    echo.
    echo Запустите API сервер: testing\start_api_server.bat
    echo Или запустите все тесты: testing\run_all_tests.bat
    echo.
    pause
    exit /b 1
)

REM Запуск теста API сервера
echo Запуск теста API сервера...
python testing\scripts\test_api_quick.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ Тест API сервера прошел успешно!
    echo.
    echo 📊 Доступные endpoints:
    echo    - Health: http://localhost:8000/health/
    echo    - Auth: http://localhost:8000/auth/login
    echo    - Deals: http://localhost:8000/api/v1/deals/
    echo    - Sessions: http://localhost:8000/api/v1/sessions/
    echo    - Swagger: http://localhost:8000/docs
) else (
    echo.
    echo ❌ Тест API сервера не прошел!
    echo Проверьте:
    echo - Запущен ли API сервер
    echo - Доступность порта 8000
    echo - Логи сервера для диагностики
)

echo.
pause 