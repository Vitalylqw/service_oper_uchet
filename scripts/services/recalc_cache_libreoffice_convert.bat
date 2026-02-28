@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

python "%SCRIPT_DIR%recalc_cache_libreoffice_convert.py" %*
set EXITCODE=%ERRORLEVEL%
if not %EXITCODE%==0 (
    echo LibreOffice pre-calculation failed with code %EXITCODE%
    exit /b %EXITCODE%
)

endlocal
