@echo off
echo ========================================
echo    ТЕСТ ПАРСИНГА EXCEL
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
    echo.
    echo Убедитесь, что файл существует и доступен для чтения.
    pause
    exit /b 1
)

REM Запуск теста парсинга Excel
echo Запуск теста парсинга Excel файла...
python testing\scripts\test_excel_parsing.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ Тест парсинга Excel прошел успешно!
    echo.
    echo 📊 Ожидаемые результаты:
    echo    - 15 сделок извлечено
    echo    - 84 позиции товаров
    echo    - 2 листа обработано (Май 2025, Июнь 2025)
    echo    - 0 ошибок парсинга
) else (
    echo.
    echo ❌ Тест парсинга Excel не прошел!
    echo Проверьте:
    echo - Структуру Excel файла
    echo - Установлены ли pandas и openpyxl
    echo - Права доступа к файлу
)

echo.
pause 