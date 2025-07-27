@echo off
chcp 65001 > nul
echo ========================================
echo    ЗАПУСК REACT UI
echo ========================================
echo.

REM Проверка, не занят ли порт 3000
echo Проверка доступности порта 3000...
netstat -an | findstr :3000 > nul
if %ERRORLEVEL% equ 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Порт 3000 уже занят!
    echo Возможно, React UI уже запущен.
    echo.
    echo Проверьте: http://localhost:3000
    echo.
    pause
    exit /b 1
)

REM Проверка существования папки web
if not exist "src\presentation\web" (
    echo [ОШИБКА] Папка React UI не найдена!
    echo Ожидаемый путь: src\presentation\web
    pause
    exit /b 1
)

REM Переход в папку web
cd src\presentation\web

REM Проверка установки npm зависимостей
if not exist "node_modules" (
    echo Установка npm зависимостей...
    npm install
    if %ERRORLEVEL% neq 0 (
        echo [ОШИБКА] Не удалось установить npm зависимости!
        pause
        exit /b 1
    )
)

REM Запуск React UI
echo Запуск React UI...
echo.
echo UI будет доступен по адресу: http://localhost:3000
echo.
echo Для остановки сервера нажмите Ctrl+C
echo.

npm start 