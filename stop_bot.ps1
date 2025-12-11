# PowerShell script to stop bot
# Set console output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Stopping all bot instances..." -ForegroundColor Yellow
Write-Host ""

# Find and stop Python processes running main.py
$processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*venv*"
}

if ($processes) {
    Write-Host "Found $($processes.Count) Python process(es) to stop..." -ForegroundColor Cyan
    $processes | ForEach-Object {
        Write-Host "  Stopping process ID: $($_.Id)" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host ""
    Write-Host "[OK] Done. You can now start the bot with: .\start_bot.ps1" -ForegroundColor Green
} else {
    Write-Host "[INFO] No bot processes found running." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

