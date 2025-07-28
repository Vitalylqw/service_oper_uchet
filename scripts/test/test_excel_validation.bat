@echo off
echo Testing Excel validation system...
echo.

cd /d "%~dp0\..\.."
python scripts/test/test_excel_validation.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Excel validation tests completed successfully!
) else (
    echo.
    echo ❌ Excel validation tests failed!
)

pause 