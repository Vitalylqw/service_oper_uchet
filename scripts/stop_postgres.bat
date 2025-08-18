@echo off
echo Stopping PostgreSQL container...
echo.

REM Stop PostgreSQL container
docker-compose -f docker-compose.db.yml down

echo.
echo PostgreSQL container stopped!
pause
