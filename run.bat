@echo off
title NEST KERALA – RENTAL HOME FINDER
echo ===================================================
echo NEST KERALA - RENTAL HOME FINDER
echo BCA Third Year Mini Project
echo Website: http://127.0.0.1:5000
echo ===================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else if exist "C:\Users\Dell\Documents\nestkerala\.venv\Scripts\python.exe" (
    "C:\Users\Dell\Documents\nestkerala\.venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause
