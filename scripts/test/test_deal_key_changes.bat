@echo off
cd /d "%~dp0"
echo ===============================================
echo TESTING DEAL_KEY CHANGES WITH PERIOD
echo ===============================================
python test_deal_key_with_period.py
echo.
echo ===============================================
echo TEST COMPLETED
echo ===============================================
pause
