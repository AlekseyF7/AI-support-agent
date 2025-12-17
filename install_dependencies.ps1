# Скрипт установки зависимостей для Windows
# Исправляет проблемы с установкой numpy на Python 3.14

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Установка зависимостей для AI Support Bot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка виртуального окружения
if (-not $env:VIRTUAL_ENV) {
    Write-Host "ВНИМАНИЕ: Виртуальное окружение не активировано!" -ForegroundColor Yellow
    Write-Host "Активируйте его командой: .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Продолжить установку? (y/n)"
    if ($response -ne "y") {
        exit 1
    }
}

Write-Host "Обновление pip..." -ForegroundColor Green
python -m pip install --upgrade pip setuptools wheel

Write-Host ""
Write-Host "Установка numpy с принудительным использованием wheel-файлов..." -ForegroundColor Green
# Пытаемся установить numpy только из wheel-файлов (без сборки из исходников)
pip install --only-binary :all: numpy

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ОШИБКА: Не удалось установить numpy из готовых wheel-файлов." -ForegroundColor Red
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "1. Python 3.14 слишком новый, wheel-файлов для него может не быть" -ForegroundColor Yellow
    Write-Host "2. Рекомендуется использовать Python 3.11 или 3.12" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Попытка установки последней совместимой версии numpy..." -ForegroundColor Yellow
    pip install "numpy<2.0.0" --prefer-binary
}

Write-Host ""
Write-Host "Установка остальных зависимостей..." -ForegroundColor Green
pip install -r requirements.txt --prefer-binary

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Установка завершена успешно!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ОШИБКА при установке зависимостей!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Рекомендации:" -ForegroundColor Yellow
    Write-Host "1. Убедитесь, что используете Python 3.11 или 3.12 (не 3.14)" -ForegroundColor Yellow
    Write-Host "2. Проверьте подключение к интернету" -ForegroundColor Yellow
    Write-Host "3. Попробуйте обновить pip: python -m pip install --upgrade pip" -ForegroundColor Yellow
    exit 1
}
