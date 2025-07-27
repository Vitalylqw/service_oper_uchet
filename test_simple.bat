@echo off
echo Тест простого bat файла
echo.
echo Текущая директория: %CD%
echo.
echo Проверка виртуального окружения...
if exist "venv\Scripts\activate.bat" (
    echo Виртуальное окружение найдено
) else (
    echo Виртуальное окружение НЕ найдено
)
echo.
echo Проверка Python...
python --version
echo.
echo Тест завершен
pause 