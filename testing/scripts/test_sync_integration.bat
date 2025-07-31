@echo off
echo Sync Integration Test Runner
echo.

if "%1"=="" (
    echo Running full sync without debug logs...
    python testing/scripts/test_sync_integration.py --log-level INFO
    goto :end
)

if "%1"=="interactive" (
    echo Starting interactive mode...
    python testing/scripts/test_sync_integration.py --interactive
    goto :end
)

if "%1"=="full" (
    if "%2"=="debug" (
        echo Running full sync with debug logs...
        python testing/scripts/test_sync_integration.py --sync-type full --log-level DEBUG
    ) else (
        echo Running full sync without debug logs...
        python testing/scripts/test_sync_integration.py --sync-type full --log-level INFO
    )
    goto :end
)

if "%1"=="incremental" (
    if "%2"=="" (
        echo Running incremental sync with 12 months without debug logs...
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months 12 --log-level INFO
    ) else if "%2"=="debug" (
        echo Running incremental sync with 12 months with debug logs...
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months 12 --log-level DEBUG
    ) else (
        if "%3"=="debug" (
            echo Running incremental sync with %2 months with debug logs...
            python testing/scripts/test_sync_integration.py --sync-type incremental --period-months %2 --log-level DEBUG
        ) else (
            echo Running incremental sync with %2 months without debug logs...
            python testing/scripts/test_sync_integration.py --sync-type incremental --period-months %2 --log-level INFO
        )
    )
    goto :end
)

if "%1"=="debug" (
    echo Running full sync with debug logs...
    python testing/scripts/test_sync_integration.py --log-level DEBUG
    goto :end
)

echo Usage examples:
echo   test_sync_integration.bat                    - Full sync without debug logs
echo   test_sync_integration.bat interactive        - Interactive mode
echo   test_sync_integration.bat full              - Full sync without debug logs
echo   test_sync_integration.bat full debug        - Full sync with debug logs
echo   test_sync_integration.bat debug             - Full sync with debug logs
echo   test_sync_integration.bat incremental 6     - Incremental sync for 6 months without debug logs
echo   test_sync_integration.bat incremental 6 debug - Incremental sync for 6 months with debug logs

:end
pause