@echo off
title Alpha Vintage Analytics — Pipeline Webhook Server
cd /d "%~dp0"

echo.
echo  =========================================
echo   Alpha Vintage — Pipeline Webhook Server
echo  =========================================
echo.
echo  n8n calls this server to trigger the pipeline.
echo  Keep this window open while n8n is running.
echo.
echo  Endpoint: http://localhost:8502/run
echo.

:: Kill any existing webhook processes on port 8502
"C:\Users\User\AppData\Local\Programs\Python\Python314\python.exe" -c "import subprocess; r=subprocess.run(['netstat','-ano'],capture_output=True,text=True,errors='ignore'); [subprocess.run(['taskkill','/PID',l.strip().split()[-1],'/F'],capture_output=True) for l in r.stdout.splitlines() if ':8502' in l and 'LISTENING' in l]" 2>nul
timeout /t 2 /nobreak >nul

"C:\Users\User\AppData\Local\Programs\Python\Python314\python.exe" pipeline_webhook.py

pause
