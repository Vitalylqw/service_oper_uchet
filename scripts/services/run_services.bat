@echo off
echo Service Scripts Runner
echo =====================

echo 1. Check Data
echo 2. Check Swagger
echo 3. Fix Read Model Builder
echo 4. Build Read Models
echo 5. Final Check
echo 6. Check API
echo 7. Run Sync Once
echo 8. Simple API Test
echo 9. Simple Connection Test
echo 10. Simple DB Init
echo 11. Check Environment

set /p choice="Select service (1-11): "

if "%choice%"=="1" (
    echo Running check_data.py...
    python check_data.py
) else if "%choice%"=="2" (
    echo Running check_swagger.py...
    python check_swagger.py
) else if "%choice%"=="3" (
    echo Running fix_read_model_builder.py...
    python fix_read_model_builder.py
) else if "%choice%"=="4" (
    echo Running build_read_models.py...
    python build_read_models.py
) else if "%choice%"=="5" (
    echo Running final_check.py...
    python final_check.py
) else if "%choice%"=="6" (
    echo Running check_api.py...
    python check_api.py
) else if "%choice%"=="7" (
    echo Running run_sync_once.py...
    python run_sync_once.py
) else if "%choice%"=="8" (
    echo Running simple_api_test.py...
    python simple_api_test.py
) else if "%choice%"=="9" (
    echo Running simple_connection_test.py...
    python simple_connection_test.py
) else if "%choice%"=="10" (
    echo Running simple_db_init.py...
    python simple_db_init.py
) else if "%choice%"=="11" (
    echo Running check_environment.py...
    python check_environment.py
) else (
    echo Invalid choice!
)

pause 