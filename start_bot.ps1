# PowerShell script to start bot
# Set console output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Starting Telegram Support Bot..." -ForegroundColor Green
Write-Host ""

# Check virtual environment
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup_venv.bat first or create venv manually." -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment and start bot
& "venv\Scripts\python.exe" main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Bot stopped with error code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

