@echo off
echo Scripts Manager
echo ===============

echo 1. Debug Scripts
echo 2. Test Scripts
echo 3. Service Scripts
echo 4. Database Scripts
echo 5. Git Operations

set /p choice="Select category (1-5): "

if "%choice%"=="1" (
    echo Starting Debug Scripts...
    cd debug
    call run_debug.bat
    cd ..
) else if "%choice%"=="2" (
    echo Starting Test Scripts...
    cd test
    call run_tests.bat
    cd ..
) else if "%choice%"=="3" (
    echo Starting Service Scripts...
    cd services
    call run_services.bat
    cd ..
) else if "%choice%"=="4" (
    echo Starting Database Scripts...
    cd database
    call run_database.bat
    cd ..
) else if "%choice%"=="5" (
    echo Git Operations:
    echo 1. Push to GitHub
    echo 2. Simple Push
    echo 3. Check Last Commit
    echo 4. Add and Commit
    echo 5. Check Git Status
    echo 6. Init DB Quick
    echo 7. Check Data Direct
    echo 8. Cleanup Temp Files
    
    set /p git_choice="Select git operation (1-8): "
    
    if "%git_choice%"=="1" (
        cd git
        call push_to_github.bat
        cd ..
    ) else if "%git_choice%"=="2" (
        cd git
        call simple_push.bat
        cd ..
    ) else if "%git_choice%"=="3" (
        cd git
        call check_last_commit.bat
        cd ..
    ) else if "%git_choice%"=="4" (
        cd git
        call add_and_commit.bat
        cd ..
    ) else if "%git_choice%"=="5" (
        cd git
        call check_git_status.bat
        cd ..
    ) else if "%git_choice%"=="6" (
        cd git
        call init_db_quick.bat
        cd ..
    ) else if "%git_choice%"=="7" (
        cd git
        call check_data_direct.bat
        cd ..
    ) else if "%git_choice%"=="8" (
        cd git
        call cleanup_temp.bat
        cd ..
    ) else (
        echo Invalid git operation choice!
    )
) else (
    echo Invalid choice!
)

pause 