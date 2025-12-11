#!/bin/bash
# Скрипт для резервного копирования Qdrant

set -e

QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
BACKUP_DIR="${BACKUP_DIR:-./backups/qdrant}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="qdrant_backup_${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"

echo "Starting Qdrant backup..."

# Создание snapshot через API
curl -X POST "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/knowledge_base/snapshots" \
    -H "Content-Type: application/json" \
    -d "{\"wait\": true}"

# Скачивание snapshot (если доступен)
# Примечание: В production нужно настроить доступ к файловой системе Qdrant
echo "Qdrant backup initiated. Check Qdrant data directory for snapshots."

# Удаление старых бэкапов
find "${BACKUP_DIR}" -name "qdrant_backup_*" -mtime +7 -delete

echo "Backup completed"
