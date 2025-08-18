@echo off
echo Checking PostgreSQL container status...
echo.

REM Check container status
docker ps | findstr so_pg

if %errorlevel% equ 0 (
    echo.
    echo PostgreSQL container is RUNNING
    echo.
    echo Container details:
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr so_pg
) else (
    echo.
    echo PostgreSQL container is NOT RUNNING
    echo.
    echo To start it, run: scripts/start_postgres.bat
)

echo.
pause
