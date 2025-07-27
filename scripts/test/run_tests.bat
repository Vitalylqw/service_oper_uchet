@echo off
echo Test Scripts Runner
echo ==================

echo 1. Test Specific Deal
echo 2. Test JWT
echo 3. Test Excel Parsing
echo 4. Test Frontend
echo 5. Test Sync Integration
echo 6. Test Service Raw
echo 7. Test Stats Endpoint
echo 8. Test DB Direct
echo 9. Test Real Service Direct
echo 10. Test API Detailed
echo 11. Test API Quick
echo 12. Test Debug Endpoint
echo 13. Test Full Cycle
echo 14. Test DB Simple
echo 15. Test API Endpoints
echo 16. Test DB Connection

set /p choice="Select test (1-16): "

if "%choice%"=="1" (
    echo Running test_specific_deal.py...
    python test_specific_deal.py
) else if "%choice%"=="2" (
    echo Running test_jwt.py...
    python test_jwt.py
) else if "%choice%"=="3" (
    echo Running test_excel_parsing.py...
    python test_excel_parsing.py
) else if "%choice%"=="4" (
    echo Running test_frontend.py...
    python test_frontend.py
) else if "%choice%"=="5" (
    echo Running test_sync_integration.py...
    python test_sync_integration.py
) else if "%choice%"=="6" (
    echo Running test_service_raw.py...
    python test_service_raw.py
) else if "%choice%"=="7" (
    echo Running test_stats_endpoint.py...
    python test_stats_endpoint.py
) else if "%choice%"=="8" (
    echo Running test_db_direct.py...
    python test_db_direct.py
) else if "%choice%"=="9" (
    echo Running test_real_service_direct.py...
    python test_real_service_direct.py
) else if "%choice%"=="10" (
    echo Running test_api_detailed.py...
    python test_api_detailed.py
) else if "%choice%"=="11" (
    echo Running test_api_quick.py...
    python test_api_quick.py
) else if "%choice%"=="12" (
    echo Running test_debug_endpoint.py...
    python test_debug_endpoint.py
) else if "%choice%"=="13" (
    echo Running test_full_cycle.py...
    python test_full_cycle.py
) else if "%choice%"=="14" (
    echo Running test_db_simple.py...
    python test_db_simple.py
) else if "%choice%"=="15" (
    echo Running test_api_endpoints.py...
    python test_api_endpoints.py
) else if "%choice%"=="16" (
    echo Running test_db_connection.py...
    python test_db_connection.py
) else (
    echo Invalid choice!
)

pause 