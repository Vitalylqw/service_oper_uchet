# PowerShell script for quick database cleanup
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Quick Database Cleanup (Auto-confirm)" -ForegroundColor Cyan
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

Write-Host "Running quick database cleanup with backup..." -ForegroundColor Yellow
python database_cleanup\clear_database.py --confirm

# Check if the script completed successfully
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Quick cleanup completed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Quick cleanup failed!" -ForegroundColor Red
    Write-Host "Check the log file: database_cleanup.log" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"