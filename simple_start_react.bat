@echo off
echo Starting React UI...
echo.

REM Переход в папку web
cd src\presentation\web

REM Установка зависимостей если нужно
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

REM Запуск React
npm start

pause 