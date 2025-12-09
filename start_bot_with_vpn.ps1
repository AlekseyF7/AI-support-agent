# PowerShell script to start bot with VPN check
# Set console output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Starting bot with VPN ===" -ForegroundColor Cyan
Write-Host ""

# VPN warning
Write-Host "IMPORTANT: Make sure VPN is connected!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Check:" -ForegroundColor White
Write-Host "  1. VPN client is running" -ForegroundColor Gray
Write-Host "  2. VPN connected to server (USA, Europe)" -ForegroundColor Gray
Write-Host "  3. IP address changed (check on whatismyipaddress.com)" -ForegroundColor Gray
Write-Host ""

# Optional IP check (requires internet)
try {
    $ipInfo = Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 5
    Write-Host "Current IP address: $($ipInfo.ip)" -ForegroundColor Cyan
    Write-Host ""
} catch {
    Write-Host "Could not check IP address (this is OK)" -ForegroundColor Gray
    Write-Host ""
}

# Confirmation
Write-Host "Is VPN connected? (y/n): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -ne "y" -and $response -ne "Y") {
    Write-Host ""
    Write-Host "Please connect VPN and run the script again." -ForegroundColor Red
    Write-Host "Or use: .\start_bot.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting bot..." -ForegroundColor Green
Write-Host ""

# Start main script
& ".\start_bot.ps1"

