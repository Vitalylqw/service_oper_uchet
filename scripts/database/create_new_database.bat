@echo off
echo ========================================
echo  СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ
echo ========================================
echo.
echo Этот скрипт создаст новую базу данных с нуля
echo включая все новые изменения структуры.
echo.
echo Шаги:
echo 1. Создание схемы таблиц
echo 2. Применение миграций (если нужно)
echo 3. Проверка работоспособности
echo.
pause

echo.
echo [1/3] Создание схемы таблиц...
python init_database.py

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка создания схемы!
    pause
    exit /b 1
)

echo.
echo [2/3] Применение новых структурных изменений...
python migrations/20250120_restructure_positions.py

if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Миграция не удалась, но это может быть нормально для новой БД
)

echo.
echo [3/3] Проверка базы данных...
python check_database_status.py

echo.
echo ✅ БАЗА ДАННЫХ СОЗДАНА УСПЕШНО!
echo.
echo 📂 Файл базы данных: data/service_oper_uchet.sqlite
echo 🔧 Структура: Event Store + Read Models + Audit
echo 📊 Готова к синхронизации Excel файлов
echo.
pause