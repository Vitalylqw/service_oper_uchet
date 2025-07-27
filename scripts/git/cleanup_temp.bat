@echo off
echo Cleaning up temporary files...

if exist "email_validator-2.0.0.dist-info" (
    echo Removing email_validator-2.0.0.dist-info...
    rmdir /s /q "email_validator-2.0.0.dist-info"
)

if exist "__pycache__" (
    echo Removing __pycache__...
    rmdir /s /q "__pycache__"
)

if exist ".ruff_cache" (
    echo Removing .ruff_cache...
    rmdir /s /q ".ruff_cache"
)

if exist ".mypy_cache" (
    echo Removing .mypy_cache...
    rmdir /s /q ".mypy_cache"
)

if exist ".pytest_cache" (
    echo Removing .pytest_cache...
    rmdir /s /q ".pytest_cache"
)

echo Cleanup completed! 