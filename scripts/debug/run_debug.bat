@echo off
echo Debug Scripts Runner
echo ===================

echo 1. Debug Deal Endpoint
echo 2. Debug Auth
echo 3. Debug Database Stats
echo 4. Debug API Deals
echo 5. Debug Events
echo 6. Debug DB Tables

set /p choice="Select script (1-6): "

if "%choice%"=="1" (
    echo Running debug_deal_endpoint.py...
    python debug_deal_endpoint.py
) else if "%choice%"=="2" (
    echo Running debug_auth.py...
    python debug_auth.py
) else if "%choice%"=="3" (
    echo Running debug_database_stats.py...
    python debug_database_stats.py
) else if "%choice%"=="4" (
    echo Running debug_api_deals.py...
    python debug_api_deals.py
) else if "%choice%"=="5" (
    echo Running debug_events.py...
    python debug_events.py
) else if "%choice%"=="6" (
    echo Running debug_db_tables.py...
    python debug_db_tables.py
) else (
    echo Invalid choice!
)

pause 