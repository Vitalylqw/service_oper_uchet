@echo off
echo Checking current branch and remote...
git branch -v
echo.
git remote -v
echo.

echo Pushing to GitHub...
git push origin develop

echo.
echo Push completed successfully!
pause 