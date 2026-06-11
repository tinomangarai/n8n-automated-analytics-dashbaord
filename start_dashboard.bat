@echo off
title Alpha Vintage Analytics — Dashboard
cd /d "%~dp0"

echo.
echo  =========================================
echo   Alpha Vintage Analytics — Dashboard
echo  =========================================
echo.

:: Kill any existing Streamlit process on port 8503
echo  Clearing port 8503...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8503 "') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo  Starting Streamlit dashboard...
echo  Open http://localhost:8503 in your browser
echo.

"C:\Users\User\AppData\Local\Programs\Python\Python314\python.exe" -m streamlit run dashboard/app.py ^
    --server.port 8503 ^
    --server.headless false ^
    --browser.gatherUsageStats false ^
    --theme.base dark

pause
