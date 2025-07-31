@echo off
echo ========================================
echo Testing Hybrid Deferred Events Approach
echo ========================================
echo.

cd /d "%~dp0\..\.."

echo Starting hybrid deferred events tests...
python scripts/test/test_hybrid_deferred_events.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Hybrid deferred events tests completed successfully!
) else (
    echo.
    echo ❌ Hybrid deferred events tests failed!
)

pause