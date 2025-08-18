@echo off
echo Starting PostgreSQL container...
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if network exists
docker network ls | findstr devnet >nul 2>&1
if %errorlevel% neq 0 (
    echo Creating devnet network...
    docker network create devnet
)

REM Start PostgreSQL container
echo Starting PostgreSQL container...
docker-compose -f docker-compose.db.yml up -d

echo.
echo PostgreSQL container started!
echo Database: so_uchet
echo User: so_user
echo Password: so_pass
echo Port: 5432
echo.
echo You can now test the connection using:
echo python scripts/test_postgres_connection.py
pause
