@echo off
title Push Nest Kerala to GitHub
echo ========================================================
echo Pushing Nest Kerala to GitHub (rental-properties)
echo ========================================================

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" push_to_github.py %*
) else if exist "C:\Users\Dell\Documents\nestkerala\.venv\Scripts\python.exe" (
    "C:\Users\Dell\Documents\nestkerala\.venv\Scripts\python.exe" push_to_github.py %*
) else (
    python push_to_github.py %*
)

echo.
pause
