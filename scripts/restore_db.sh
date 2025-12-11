#!/bin/bash
# Скрипт для восстановления PostgreSQL базы данных

set -e

# Переменные окружения
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-support_user}"
DB_NAME="${POSTGRES_DB:-support_db}"
BACKUP_FILE="${1}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file ${BACKUP_FILE} not found"
    exit 1
fi

# Экспорт пароля
export PGPASSWORD="${POSTGRES_PASSWORD:-support_password}"

echo "Starting restore from ${BACKUP_FILE}..."

# Распаковка если нужно
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    echo "Decompressing backup..."
    gunzip -c "${BACKUP_FILE}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres
else
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres < "${BACKUP_FILE}"
fi

echo "Restore completed successfully"
