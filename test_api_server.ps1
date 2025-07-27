Write-Host "========================================" -ForegroundColor Green
Write-Host "   ТЕСТИРОВАНИЕ API СЕРВЕРА" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Проверка существования виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "[ОШИБКА] Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Создайте виртуальное окружение: python -m venv venv" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверка, не занят ли порт 8000
Write-Host "Проверка доступности порта 8000..." -ForegroundColor Yellow
$portCheck = netstat -an | Select-String ":8000"
if ($portCheck) {
    Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Порт 8000 уже занят!" -ForegroundColor Yellow
    Write-Host "Возможно, API сервер уже запущен." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Проверьте: http://localhost:8000/health/" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Запуск API сервера
Write-Host "Запуск FastAPI сервера..." -ForegroundColor Green
Write-Host ""
Write-Host "Сервер будет доступен по адресу: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Swagger UI: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:8000/health/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Для остановки сервера нажмите Ctrl+C" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn src.presentation.api.main:app --host 127.0.0.1 --port 8000 --reload 