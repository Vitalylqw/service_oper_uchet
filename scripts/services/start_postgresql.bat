@echo off
REM Start PostgreSQL container for Service Oper Uchet

echo Starting PostgreSQL container...

REM Change to project directory
cd /d "%~dp0\..\.."

REM Start PostgreSQL container
docker-compose -f docker-compose.db.yml up -d postgres

if %ERRORLEVEL% EQU 0 (
    echo PostgreSQL container started successfully!
    echo Waiting for container to be ready...
    
    REM Wait for container to be ready
    timeout /t 10 /nobreak > nul
    
    echo Checking container status...
    docker-compose -f docker-compose.db.yml ps postgres
    
    echo.
    echo PostgreSQL is ready!
    echo Connection details:
    echo   Host: so_pg
    echo   Port: 5432
    echo   Database: so_uchet
    echo   User: so_user
    echo   Password: so_pass
) else (
    echo Failed to start PostgreSQL container!
    pause
)
