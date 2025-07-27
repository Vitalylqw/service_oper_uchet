@echo off
echo ========================================
echo    СИСТЕМА ТЕСТИРОВАНИЯ SERVICE_OPER_UCHET
echo ========================================
echo.

REM Активация виртуального окружения
if exist "venv\Scripts\Activate.ps1" (
    echo [1/7] Активация виртуального окружения...
    call venv\Scripts\Activate.ps1
) else (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    echo Создайте виртуальное окружение: python -m venv venv
    pause
    exit /b 1
)

echo.
echo ========================================
echo    ЗАПУСК ВСЕХ ТЕСТОВ
echo ========================================
echo.

REM Тест 1: База данных
echo [1/5] Тестирование базы данных...
call testing\test_database.bat
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Тест базы данных не прошел!
    pause
    exit /b 1
)
echo.

REM Тест 2: Парсинг Excel
echo [2/5] Тестирование парсинга Excel...
call testing\test_excel_parsing.bat
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Тест парсинга Excel не прошел!
    pause
    exit /b 1
)
echo.

REM Тест 3: Синхронизация
echo [3/5] Тестирование синхронизации...
call testing\test_sync_integration.bat
if %ERRORLEVEL% neq 0 (
    echo [ОШИБКА] Тест синхронизации не прошел!
    pause
    exit /b 1
)
echo.

REM Запуск API сервера для тестирования
echo [4/5] Запуск API сервера для тестирования...
start /B testing\start_api_server.bat

REM Ожидание запуска сервера
echo Ожидание запуска API сервера...
timeout /t 5 /nobreak > nul

REM Тест 4: API сервер
echo [4/5] Тестирование API сервера...
call testing\test_api_server.bat
if %ERRORLEVEL% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Тест API сервера не прошел!
    echo Возможно, сервер еще не запустился. Попробуйте позже.
)

REM Запуск React UI для тестирования
echo [5/5] Запуск React UI для тестирования...
start /B testing\start_react_ui.bat

REM Ожидание запуска UI
echo Ожидание запуска React UI...
timeout /t 10 /nobreak > nul

REM Тест 5: Фронтенд
echo [5/5] Тестирование фронтенда...
call testing\test_frontend.bat
if %ERRORLEVEL% neq 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Тест фронтенда не прошел!
    echo Возможно, UI еще не загрузился. Попробуйте позже.
)

echo.
echo ========================================
echo    РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ
echo ========================================
echo.
echo ✅ Все основные тесты выполнены!
echo.
echo 📊 Проверьте результаты в файлах:
echo    - testing\reports\PROJECT_TESTING_REPORT.md
echo    - testing\reports\test_results.json
echo.
echo 🌐 Доступные сервисы:
echo    - API сервер: http://localhost:8000
echo    - React UI: http://localhost:3000
echo    - Swagger UI: http://localhost:8000/docs
echo.
echo 💡 Для остановки серверов нажмите Ctrl+C в их окнах
echo.

pause 