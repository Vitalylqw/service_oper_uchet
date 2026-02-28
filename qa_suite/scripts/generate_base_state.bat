@echo off
REM QA Suite - Generate Base State Excel File
REM ==========================================

echo ========================================
echo QA Suite - Generate Base State
echo ========================================
echo.

cd /d "%~dp0.."

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

echo Generating base_state.xlsx fixture...
echo.

python -c "from pathlib import Path; from core.excel_builder import create_base_state_file; p = Path('tests/fixtures/base_state.xlsx'); create_base_state_file(p); print(f'Created: {p}')"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Failed to generate base state file.
    exit /b %ERRORLEVEL%
)

echo.
echo Base state file generated successfully.
exit /b 0
