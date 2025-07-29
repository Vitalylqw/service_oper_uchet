# PowerShell script for database cleanup
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Enhanced Database Cleanup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if database exists
if (-not (Test-Path "service_oper_uchet.sqlite")) {
    Write-Host "ERROR: Database file not found!" -ForegroundColor Red
    Write-Host "Expected: service_oper_uchet.sqlite" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Activate virtual environment if it exists
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "..\venv\Scripts\Activate.ps1"
}

Write-Host ""
Write-Host "Available options:" -ForegroundColor Green
Write-Host "1. Show database statistics only" -ForegroundColor White
Write-Host "2. Clean database with backup (default)" -ForegroundColor White
Write-Host "3. Clean database without backup" -ForegroundColor White
Write-Host "4. Clean database with auto-confirm (no prompts)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Select option (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Running database statistics..." -ForegroundColor Yellow
        python database_cleanup\clear_database.py --stats-only
    }
    "2" {
        Write-Host ""
        Write-Host "Running database cleanup with backup..." -ForegroundColor Yellow
        python database_cleanup\clear_database.py
    }
    "3" {
        Write-Host ""
        Write-Host "Running database cleanup without backup..." -ForegroundColor Yellow
        python database_cleanup\clear_database.py --no-backup
    }
    "4" {
        Write-Host ""
        Write-Host "Running database cleanup with auto-confirm..." -ForegroundColor Yellow
        python database_cleanup\clear_database.py --confirm
    }
    default {
        Write-Host "Invalid choice. Using default option (with backup)..." -ForegroundColor Yellow
        python database_cleanup\clear_database.py
    }
}

# Check if the script completed successfully
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Database operation completed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Database operation failed!" -ForegroundColor Red
    Write-Host "Check the log file: database_cleanup.log" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"