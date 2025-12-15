# Скрипт запуска бота
# Настройка кодировки
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Запуск Telegram бота поддержки" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Переход в директорию скрипта
Set-Location $PSScriptRoot

# Проверка наличия виртуального окружения
if (-not (Test-Path "myenv312\Scripts\python.exe")) {
    Write-Host "ОШИБКА: Виртуальное окружение myenv312 не найдено!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Создайте виртуальное окружение:" -ForegroundColor Yellow
    Write-Host "  python -m venv myenv312"
    Write-Host ""
    exit 1
}

Write-Host "Используется виртуальное окружение: myenv312" -ForegroundColor Green
Write-Host ""

# Активация окружения и запуск бота
& "myenv312\Scripts\python.exe" bot.py

