# Скрипт для установки ChromaDB с использованием Build Tools
Write-Host "Поиск Visual Studio Build Tools..." -ForegroundColor Cyan

$vsPaths = @(
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
    "${env:ProgramFiles}\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
    "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
)

$vcvarsPath = $null
foreach ($path in $vsPaths) {
    if (Test-Path $path) {
        $vcvarsPath = $path
        Write-Host "Найдено: $path" -ForegroundColor Green
        break
    }
}

if (-not $vcvarsPath) {
    Write-Host "Visual Studio Build Tools не найдены!" -ForegroundColor Red
    Write-Host "Пожалуйста, установите Microsoft Visual C++ Build Tools:" -ForegroundColor Yellow
    Write-Host "https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Или попробуйте установить через winget:" -ForegroundColor Yellow
    Write-Host "winget install Microsoft.VisualStudio.2022.BuildTools --silent --override `"--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended`"" -ForegroundColor Cyan
    exit 1
}

# Создаем временный bat файл для установки
$tempBat = "$env:TEMP\install_chromadb.bat"
$installScript = @"
@echo off
call "$vcvarsPath" >nul 2>&1
cd /d "$PWD"
call myenv312\Scripts\activate.bat
python -m pip install chromadb==0.4.22 sentence-transformers
"@

$installScript | Out-File -FilePath $tempBat -Encoding ASCII

Write-Host "Установка ChromaDB с использованием Build Tools..." -ForegroundColor Cyan
& cmd.exe /c $tempBat

if ($LASTEXITCODE -eq 0) {
    Write-Host "ChromaDB успешно установлен!" -ForegroundColor Green
    Remove-Item $tempBat -ErrorAction SilentlyContinue
} else {
    Write-Host "Ошибка установки ChromaDB. Проверьте наличие Build Tools." -ForegroundColor Red
    Remove-Item $tempBat -ErrorAction SilentlyContinue
    exit 1
}

