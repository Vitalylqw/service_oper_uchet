@echo off
echo ========================================
echo    ТЕСТ ФРОНТЕНДА
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

REM Проверка, запущен ли React UI
echo Проверка доступности React UI...
netstat -an | findstr :3000 > nul
if %ERRORLEVEL% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] React UI не запущен на порту 3000
    echo.
    echo Запустите React UI: testing\start_react_ui.bat
    echo Или запустите все тесты: testing\run_all_tests.bat
    echo.
    pause
    exit /b 1
)

REM Запуск теста фронтенда
echo Запуск теста фронтенда...
python testing\scripts\test_frontend.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ Тест фронтенда прошел успешно!
    echo.
    echo 📊 Доступные сервисы:
    echo    - React UI: http://localhost:3000
    echo    - API сервер: http://localhost:8000
    echo    - Swagger UI: http://localhost:8000/docs
    echo.
    echo 🔐 Тестовые учетные данные:
    echo    - viewer/password
    echo    - analyst/password
    echo    - admin/password
) else (
    echo.
    echo ❌ Тест фронтенда не прошел!
    echo Проверьте:
    echo - Запущены ли API сервер и React UI
    echo - Доступность портов 8000 и 3000
    echo - Логи для детальной диагностики
)

echo.
pause 