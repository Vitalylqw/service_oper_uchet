# Sync Integration Test Runner
Write-Host "Sync Integration Test Runner" -ForegroundColor Green
Write-Host ""

if ($args.Count -eq 0) {
    Write-Host "Running full sync (default) without debug logs..." -ForegroundColor Yellow
    python testing/scripts/test_sync_integration.py --log-level INFO
}
elseif ($args[0] -eq "interactive") {
    Write-Host "Starting interactive mode..." -ForegroundColor Yellow
    python testing/scripts/test_sync_integration.py --interactive
}
elseif ($args[0] -eq "full") {
    if ($args.Count -gt 1 -and $args[1] -eq "debug") {
        Write-Host "Running full sync with debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type full --log-level DEBUG
    }
    else {
        Write-Host "Running full sync without debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type full --log-level INFO
    }
}
elseif ($args[0] -eq "incremental") {
    if ($args.Count -eq 1) {
        Write-Host "Running incremental sync with 12 months period (default) without debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months 12 --log-level INFO
    }
    elseif ($args.Count -eq 2 -and $args[1] -eq "debug") {
        Write-Host "Running incremental sync with 12 months period with debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months 12 --log-level DEBUG
    }
    elseif ($args.Count -eq 2) {
        Write-Host "Running incremental sync with $($args[1]) months period without debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months $args[1] --log-level INFO
    }
    elseif ($args.Count -eq 3 -and $args[2] -eq "debug") {
        Write-Host "Running incremental sync with $($args[1]) months period with debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months $args[1] --log-level DEBUG
    }
    else {
        Write-Host "Running incremental sync with $($args[1]) months period without debug logs..." -ForegroundColor Yellow
        python testing/scripts/test_sync_integration.py --sync-type incremental --period-months $args[1] --log-level INFO
    }
}
elseif ($args[0] -eq "debug") {
    Write-Host "Running full sync with debug logs..." -ForegroundColor Yellow
    python testing/scripts/test_sync_integration.py --log-level DEBUG
}
else {
    Write-Host "Usage examples:" -ForegroundColor Cyan
    Write-Host "  .\test_sync_integration.ps1                    - Full sync without debug logs (default)" -ForegroundColor White
    Write-Host "  .\test_sync_integration.ps1 interactive        - Interactive mode" -ForegroundColor White
    Write-Host "  .\test_sync_integration.ps1 full              - Full sync without debug logs" -ForegroundColor White
    Write-Host "  .\test_sync_integration.ps1 full debug        - Full sync with debug logs" -ForegroundColor White
    Write-Host "  .\test_sync_integration.ps1 debug             - Full sync with debug logs" -ForegroundColor White
    Write-Host "  .\test_sync_integration.ps1 incremental 6     - Incremental sync for 6 months without debug logs" -ForegroundColor White
    Write-Host "  .\test_sync_integration.ps1 incremental 6 debug - Incremental sync for 6 months with debug logs" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to continue"