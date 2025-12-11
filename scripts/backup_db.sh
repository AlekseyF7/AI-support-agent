#!/bin/bash
# Скрипт для резервного копирования PostgreSQL базы данных

set -e

# Переменные окружения
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-support_user}"
DB_NAME="${POSTGRES_DB:-support_db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"
BACKUP_FILE_COMPRESSED="${BACKUP_FILE}.gz"

# Создание директории для бэкапов
mkdir -p "${BACKUP_DIR}"

# Экспорт пароля из переменной окружения
export PGPASSWORD="${POSTGRES_PASSWORD:-support_password}"

echo "Starting backup of database ${DB_NAME}..."

# Создание бэкапа
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --clean --if-exists --create \
    -f "${BACKUP_FILE}"

# Сжатие бэкапа
gzip "${BACKUP_FILE}"

echo "Backup completed: ${BACKUP_FILE_COMPRESSED}"

# Удаление старых бэкапов (старше 7 дней)
find "${BACKUP_DIR}" -name "backup_*.sql.gz" -mtime +7 -delete

echo "Old backups cleaned up"
