@echo off
title Alpha Vintage Analytics — Pipeline
cd /d "%~dp0"

echo.
echo  =========================================
echo   Alpha Vintage Analytics — Full Pipeline
echo  =========================================
echo.
echo  Running: fetch ^> analyse ^> generate PDF ^> post to Slack
echo.

"C:\Users\User\AppData\Local\Programs\Python\Python314\python.exe" run_pipeline.py %*

echo.
echo  Done. Reports saved to: %~dp0reports\
pause
