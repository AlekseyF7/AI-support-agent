# PowerShell script to setup Ollama
Write-Host "=== Ollama Setup Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is installed
Write-Host "Checking if Ollama is installed..." -ForegroundColor Yellow
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $ollamaPath) {
    Write-Host "[ERROR] Ollama is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Ollama first:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://ollama.ai/download" -ForegroundColor White
    Write-Host "2. Download and install Ollama for Windows" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "[OK] Ollama is installed at: $($ollamaPath.Source)" -ForegroundColor Green
Write-Host ""

# Check Ollama version
Write-Host "Ollama version:" -ForegroundColor Yellow
ollama --version
Write-Host ""

# List installed models
Write-Host "Checking installed models..." -ForegroundColor Yellow
$models = ollama list 2>&1
Write-Host $models
Write-Host ""

# Ask which model to download
Write-Host "Which model would you like to download?" -ForegroundColor Cyan
Write-Host ""
Write-Host "=== POWERFUL MODELS ===" -ForegroundColor Yellow
Write-Host "1. llama2:70b (MOST POWERFUL - 40GB, needs 48GB+ RAM)" -ForegroundColor Cyan
Write-Host "2. mixtral (Very powerful - 26GB, needs 32GB+ RAM)" -ForegroundColor Cyan
Write-Host "3. llama2:13b (Powerful - 7GB, needs 16GB+ RAM)" -ForegroundColor Cyan
Write-Host ""
Write-Host "=== BALANCED MODELS ===" -ForegroundColor Yellow
Write-Host "4. mistral (Recommended - 4GB, needs 8GB RAM)" -ForegroundColor White
Write-Host "5. llama2 (Good quality - 4GB, needs 8GB RAM)" -ForegroundColor White
Write-Host ""
Write-Host "=== LIGHTWEIGHT ===" -ForegroundColor Yellow
Write-Host "6. phi (Lightweight - 2GB, needs 4GB RAM)" -ForegroundColor White
Write-Host ""
Write-Host "7. Skip (use existing models)" -ForegroundColor Gray
Write-Host ""
Write-Host "Enter choice (1-5): " -ForegroundColor Yellow -NoNewline
$choice = Read-Host

$modelToDownload = ""
switch ($choice) {
    "1" { 
        $modelToDownload = "llama2:70b"
        Write-Host ""
        Write-Host "WARNING: llama2:70b requires 48GB+ RAM and 40GB disk space!" -ForegroundColor Red
        Write-Host "Are you sure? (y/n): " -ForegroundColor Yellow -NoNewline
        $confirm = Read-Host
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "Cancelled." -ForegroundColor Gray
            exit 0
        }
    }
    "2" { 
        $modelToDownload = "mixtral"
        Write-Host ""
        Write-Host "WARNING: mixtral requires 32GB+ RAM and 26GB disk space!" -ForegroundColor Red
        Write-Host "Are you sure? (y/n): " -ForegroundColor Yellow -NoNewline
        $confirm = Read-Host
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "Cancelled." -ForegroundColor Gray
            exit 0
        }
    }
    "3" { 
        $modelToDownload = "llama2:13b"
        Write-Host ""
        Write-Host "NOTE: llama2:13b requires 16GB+ RAM and 7GB disk space." -ForegroundColor Yellow
    }
    "4" { $modelToDownload = "mistral" }
    "5" { $modelToDownload = "llama2" }
    "6" { $modelToDownload = "phi" }
    "7" { 
        Write-Host "Skipping model download." -ForegroundColor Gray
        exit 0
    }
    default { 
        Write-Host "Invalid choice. Using default: mistral" -ForegroundColor Yellow
        $modelToDownload = "mistral"
    }
}

if ($modelToDownload) {
    Write-Host ""
    Write-Host "Downloading model: $modelToDownload" -ForegroundColor Green
    Write-Host "This may take several minutes depending on your internet speed..." -ForegroundColor Yellow
    Write-Host ""
    
    ollama pull $modelToDownload
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[SUCCESS] Model $modelToDownload downloaded successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Make sure .env file has: LLM_PROVIDER=ollama" -ForegroundColor White
        Write-Host "2. Make sure .env file has: OLLAMA_MODEL=$modelToDownload" -ForegroundColor White
        Write-Host "3. Run: .\start_bot.ps1" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "[ERROR] Failed to download model. Please try again." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

