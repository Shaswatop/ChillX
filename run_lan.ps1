$ip=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notmatch "Loopback|Virtual|Bluetooth|Docker|vEthernet"} | Select-Object -First 1).IPAddress
if(-not $ip){$ip="127.0.0.1"}
Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗"
Write-Host "║        MULTIPLAYER ARENA — LAN MODE        ║"
Write-Host "╠══════════════════════════════════════════════╣"
Write-Host "║  Your local IP: $($ip.PadRight(28))║"
Write-Host "║  Friends open:  http://$($ip):8000         ║"
Write-Host "║                                              ║"
Write-Host "║  Make sure firewall allows port 8000        ║"
Write-Host "║  All devices must be on the same network    ║"
Write-Host "╚══════════════════════════════════════════════╝"
Write-Host ""
python manage.py runserver 0.0.0.0:8000
