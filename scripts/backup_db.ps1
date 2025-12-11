# PowerShell скрипт для резервного копирования PostgreSQL

param(
    [string]$BackupDir = "./backups"
)

$ErrorActionPreference = "Stop"

# Переменные окружения
$DB_HOST = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$DB_PORT = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$DB_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "support_user" }
$DB_NAME = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "support_db" }
$DB_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "support_password" }

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "backup_${DB_NAME}_${TIMESTAMP}.sql"
$BackupFileCompressed = "${BackupFile}.gz"

# Создание директории
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

Write-Host "Starting backup of database ${DB_NAME}..."

# Установка переменной окружения для пароля
$env:PGPASSWORD = $DB_PASSWORD

# Создание бэкапа
& pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME `
    --clean --if-exists --create `
    -f $BackupFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "Backup failed"
    exit 1
}

# Сжатие (требует 7-Zip или другой архиватор)
# В Windows можно использовать Compress-Archive или 7-Zip
Write-Host "Backup completed: ${BackupFile}"

# Удаление старых бэкапов (старше 7 дней)
Get-ChildItem -Path $BackupDir -Filter "backup_*.sql*" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | 
    Remove-Item -Force

Write-Host "Old backups cleaned up"
