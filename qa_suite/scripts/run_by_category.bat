@echo off
REM QA Suite - Run Tests by Category
REM =================================

echo ========================================
echo QA Suite - Category Test Runner
echo ========================================
echo.

cd /d "%~dp0.."

REM Check if category is provided
if "%1"=="" (
    echo Usage: run_by_category.bat CATEGORY [--clear-db]
    echo.
    echo Categories:
    echo   INSERT - Tests for adding new data
    echo   UPDATE - Tests for modifying existing data
    echo   DELETE - Tests for removing data
    echo   MIXED  - Combined operations
    echo   EDGE   - Edge cases and boundary conditions
    echo.
    exit /b 1
)

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

echo Running %1 scenarios...
echo.

python run_tests.py --category %*

exit /b %ERRORLEVEL%
