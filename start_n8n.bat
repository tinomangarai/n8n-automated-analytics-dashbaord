@echo off
title Alpha Vintage Analytics — n8n
cd /d "%~dp0"

echo.
echo  =========================================
echo   Alpha Vintage Analytics — n8n
echo  =========================================
echo.
echo  Starting n8n workflow automation server...
echo  Open http://localhost:5678 in your browser
echo.
echo  To import the workflow:
echo    1. Open http://localhost:5678
echo    2. Workflows ^> Import from File
echo    3. Select: n8n\workflow.json
echo.

set N8N_BASIC_AUTH_ACTIVE=false
set EXECUTIONS_DATA_SAVE_ON_ERROR=all
set EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
set ALLOW_EXEC=true

"C:\Users\User\AppData\Roaming\npm\n8n.cmd" start

pause
