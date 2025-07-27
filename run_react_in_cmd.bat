@echo off
echo Запуск React UI в CMD для обхода проблем с PowerShell...
echo.

REM Запуск cmd с командами для React
cmd /k "echo Переход в папку web... && cd src\presentation\web && echo Установка зависимостей если нужно... && if not exist node_modules npm install && echo Запуск React UI... && npm start" 