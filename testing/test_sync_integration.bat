@echo off
echo ========================================
echo    ТЕСТ СИНХРОНИЗАЦИИ
echo ========================================
echo.

REM Активация виртуального окружения
if exist "venv\Scripts\Activate.ps1" (
    call venv\Scripts\Activate.ps1
) else (
    echo [ОШИБКА] Виртуальное окружение не найдено!
    exit /b 1
)

REM Проверка существования Excel файла
if not exist "data\real_data_for_testing\Data_source_excel.xlsx" (
    echo [ОШИБКА] Excel файл не найден!
    echo Ожидаемый путь: data\real_data_for_testing\Data_source_excel.xlsx
    pause
    exit /b 1
)

REM Проверка существования базы данных
if not exist "data\service_oper_uchet.sqlite" (
    echo [ОШИБКА] База данных не найдена!
    echo Ожидаемый путь: data\service_oper_uchet.sqlite
    echo.
    echo Сначала запустите тест базы данных: testing\test_database.bat
    pause
    exit /b 1
)

REM Запуск теста синхронизации
echo Запуск теста полной синхронизации...
python testing\scripts\test_sync_integration.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ Тест синхронизации прошел успешно!
    echo.
    echo 📊 Ожидаемые результаты:
    echo    - 99 изменений обнаружено
    echo    - Время синхронизации: ~0.32 сек
    echo    - 0 ошибок
    echo    - События созданы в Event Store
    echo    - Read models обновлены
) else (
    echo.
    echo ❌ Тест синхронизации не прошел!
    echo Проверьте:
    echo - Состояние базы данных
    echo - Права доступа к файлам
    echo - Логи для детальной диагностики
)

echo.
pause 