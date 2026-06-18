@echo off
cd /d "%~dp0"
title Arena Server

echo [1/3] Starting Django server...
start /B "" cmd /c "python manage.py runserver > nul 2>&1"

echo [2/3] Starting Cloudflare tunnel...
start /B "" cmd /c "cloudflared tunnel --url http://localhost:8000 > %TEMP%\cf_tunnel.log 2>&1"

echo [3/3] Waiting for tunnel URL (this may take 10-20s)...
:wait
timeout /t 2 /nobreak > nul
findstr "trycloudflare" "%TEMP%\cf_tunnel.log" > nul 2>&1
if errorlevel 1 goto wait

cls
for /f "tokens=4" %%a in ('findstr /C:"https://" "%TEMP%\cf_tunnel.log"') do set "url=%%a"

echo ========================================
echo   Server URL: %url%
echo   Share this link with friends!
echo ========================================
start "" "%url%"

echo [Press any key to stop server and tunnel...]
pause > nul
taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM cloudflared.exe > nul 2>&1
echo Done.
