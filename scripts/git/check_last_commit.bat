@echo off
echo Last commit details:
git log --oneline -1
echo.
echo Commit details:
git show --stat --oneline -1
pause 