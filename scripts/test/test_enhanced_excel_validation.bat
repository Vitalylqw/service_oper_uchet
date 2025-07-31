@echo off
echo Running Enhanced Excel Validation Tests...
echo.

cd /d "%~dp0\..\.."
python scripts/test/test_enhanced_excel_validation.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Enhanced Excel validation tests completed successfully!
) else (
    echo.
    echo ❌ Enhanced Excel validation tests failed!
)

pause