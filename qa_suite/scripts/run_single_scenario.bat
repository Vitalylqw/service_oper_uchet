@echo off
REM QA Suite - Run Single Scenario
REM ===============================

echo ========================================
echo QA Suite - Single Scenario Runner
echo ========================================
echo.

cd /d "%~dp0.."

REM Check if scenario ID is provided
if "%1"=="" (
    echo Usage: run_single_scenario.bat SCENARIO_ID [--clear-db]
    echo.
    echo Available scenarios:
    echo   INSERT: TEST_INS_01, TEST_INS_02, TEST_INS_03
    echo   UPDATE: TEST_UPD_01, TEST_UPD_02, TEST_UPD_03, TEST_UPD_04, TEST_UPD_05
    echo   DELETE: TEST_DEL_01, TEST_DEL_02, TEST_DEL_03, TEST_DEL_04
    echo   MIXED:  TEST_MIX_01, TEST_MIX_02, TEST_MIX_03
    echo   EDGE:   TEST_EDGE_01, TEST_EDGE_02, TEST_EDGE_04, TEST_EDGE_05, TEST_EDGE_06, TEST_EDGE_07
    echo.
    exit /b 1
)

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

echo Running scenario: %1
echo.

python run_tests.py --scenario %*

exit /b %ERRORLEVEL%
