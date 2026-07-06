@echo off
cd /d "%~dp0"
title Arena Server

echo [1/3] Starting Django server...
start "Django Server" cmd /c "C:\Users\Dell\AppData\Local\Programs\Python\Python312\python.exe manage.py runserver"

echo Waiting for Django...
:wait_django
timeout /t 2 /nobreak > nul
powershell -noprofile -command "$t=New-Object System.Net.Sockets.TcpClient; try{$t.Connect('127.0.0.1',8000);exit 0}catch{exit 1}" > nul 2>&1
if errorlevel 1 goto wait_django

echo [2/3] Starting Cloudflare tunnel...
start /B "" cmd /c "cloudflared tunnel --url http://127.0.0.1:8000 > %TEMP%\cf_tunnel.log 2>&1"

echo [3/3] Waiting for tunnel URL...
:wait
timeout /t 2 /nobreak > nul
findstr /R "https://.*trycloudflare\.com" "%TEMP%\cf_tunnel.log" > nul 2>&1
if errorlevel 1 goto wait

cls

for /f "tokens=4" %%a in ('findstr /R "https://.*trycloudflare\.com" "%TEMP%\cf_tunnel.log"') do set "url=%%a"

if "%url%"=="" (
    echo Failed to get tunnel URL
    pause
    exit /b 1
)

echo %url%| clip

echo ========================================
echo   Server URL: %url%
echo ========================================
echo   ^> Copied to clipboard!
echo ========================================
echo.
echo Opening QR code for mobile access...
powershell -noprofile -command "$u='%url%';$e=[uri]::EscapeDataString($u);$q='https://api.qrserver.com/v1/create-qr-code/?size=300x300'+'&data='+$e;Start-Process $q;Write-Host ('QR code opened for: '+$u)"

echo Waiting 10s for tunnel to propagate...
timeout /t 10 /nobreak > nul

start "" "%url%"

echo.
echo ========================================
echo   Share the URL or scan the QR code!
echo   Press any key to stop server...
echo ========================================
pause > nul
taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM cloudflared.exe > nul 2>&1
echo Done.
