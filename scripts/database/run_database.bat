@echo off
echo Database Scripts Runner
echo =====================

echo 1. Create Sample Excel
echo 2. Init Database
echo 3. Create Schema

set /p choice="Select database script (1-3): "

if "%choice%"=="1" (
    echo Running create_sample_excel.py...
    python create_sample_excel.py
) else if "%choice%"=="2" (
    echo Running init_database.py...
    python init_database.py
) else if "%choice%"=="3" (
    echo Running create_schema.py...
    python create_schema.py
) else (
    echo Invalid choice!
)

pause 