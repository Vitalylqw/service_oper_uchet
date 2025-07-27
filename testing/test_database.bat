@echo off
echo ========================================
echo    ТЕСТ БАЗЫ ДАННЫХ
echo ========================================
echo.

REM Активация виртуального окружения
if exist "venv\Scripts\Activate.ps1" (
    call venv\Scripts\Activate.ps1
) else (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    exit /b 1
)

REM Запуск теста базы данных
echo Запуск теста подключения к базе данных...
python testing\scripts\test_db_connection.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ Тест базы данных прошел успешно!
) else (
    echo.
    echo ❌ Тест базы данных не прошел!
    echo Проверьте:
    echo - Существует ли файл базы данных data\service_oper_uchet.sqlite
    echo - Правильность конфигурации в sprint_2_3_config.env
    echo - Установлены ли все зависимости
)

echo.
pause 