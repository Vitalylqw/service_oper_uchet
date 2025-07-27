@echo off
title Full Cycle Testing - Service Oper Uchet
echo ========================================
echo   Full Cycle Testing - Service Oper Uchet
echo ========================================
echo.
echo Этот скрипт проверит весь пайплайн:
echo - Excel файл → API → База данных → UI
echo.
echo Требования:
echo - API Server: http://localhost:8000 (start_api_server.bat)
echo - React UI: http://localhost:3000 (start_react_ui.bat)
echo - Excel файл: Data_source_excel.xlsx
echo.

echo Активация виртуального окружения...
call d:\work_d\Projects\service_oper_uchet\venv\Scripts\activate.bat
echo.

echo Проверка предварительных требований...
python scripts/test_full_cycle.py --check-only
if errorlevel 1 (
    echo.
    echo ❌ Не все требования выполнены!
    echo.
    echo 💡 Что нужно сделать:
    echo    1. Запустить API сервер: start_api_server.bat
    echo    2. Запустить React UI: start_react_ui.bat  
    echo    3. Убедиться что есть файл Data_source_excel.xlsx
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Все требования выполнены!
echo.
echo Выберите режим тестирования:
echo [1] Быстрый тест (только Excel + API)
echo [2] Полный тест (Excel + API + UI + БД)
echo [3] Только проверка окружения
echo.
set /p choice="Введите номер (1-3): "

if "%choice%"=="1" (
    echo.
    echo 🚀 Запуск быстрого тестирования...
    python scripts/test_full_cycle.py --quick --verbose
) else if "%choice%"=="2" (
    echo.
    echo 🚀 Запуск полного тестирования...
    python scripts/test_full_cycle.py --verbose
) else if "%choice%"=="3" (
    echo.
    echo 🔍 Проверка окружения завершена выше
) else (
    echo.
    echo ❌ Неверный выбор
    pause
    exit /b 1
)

echo.
if errorlevel 1 (
    echo ❌ Тестирование завершилось с ошибками!
    echo 📄 Смотрите детали в: full_cycle_test_report.json
) else (
    echo ✅ Тестирование завершилось успешно!
    echo 📄 Отчет сохранен в: full_cycle_test_report.json
)

echo.
pause 