@echo off
chcp 65001 > nul
echo ========================================
echo    ТЕСТИРОВАНИЕ SERVICE_OPER_UCHET
echo ========================================
echo.

REM Проверка наличия Python
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python и добавьте его в PATH
    pause
    exit /b 1
)

echo [1/5] Тестирование базы данных...
python testing\scripts\test_db_connection.py
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Тест базы данных не прошел!
    pause
    exit /b 1
)
echo.

echo [2/5] Тестирование парсинга Excel...
python testing\scripts\test_excel_parsing.py
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Тест парсинга Excel не прошел!
    pause
    exit /b 1
)
echo.

echo [3/5] Тестирование синхронизации...
python testing\scripts\test_sync_integration.py
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Тест синхронизации не прошел!
    pause
    exit /b 1
)
echo.

echo [4/5] Запуск API сервера...
start /B testing\start_api_server.bat
echo Ожидание запуска API сервера...
timeout /t 5 /nobreak > nul

echo [4/5] Тестирование API сервера...
python testing\scripts\test_api_quick.py
if %ERRORLEVEL% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Тест API сервера не прошел!
)
echo.

echo [5/5] Запуск React UI...
start /B testing\start_react_ui.bat
echo Ожидание запуска React UI...
timeout /t 10 /nobreak > nul

echo [5/5] Тестирование фронтенда...
python testing\scripts\test_frontend.py
if %ERRORLEVEL% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Тест фронтенда не прошел!
)
echo.

echo ========================================
echo    РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ
echo ========================================
echo.
echo ✅ Все основные тесты выполнены!
echo.
echo 🌐 Доступные сервисы:
echo    - API сервер: http://localhost:8000
echo    - React UI: http://localhost:3000
echo    - Swagger UI: http://localhost:8000/docs
echo.

pause 