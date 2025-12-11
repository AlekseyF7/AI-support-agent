#!/bin/bash
# Скрипт для полного резервного копирования всех данных

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FULL_BACKUP_DIR="${BACKUP_DIR}/full_backup_${TIMESTAMP}"

mkdir -p "${FULL_BACKUP_DIR}"

echo "Starting full backup at $(date)..."

# Бэкап PostgreSQL
echo "Backing up PostgreSQL..."
./scripts/backup_db.sh
mv ./backups/backup_*.sql.gz "${FULL_BACKUP_DIR}/" 2>/dev/null || echo "Warning: No PostgreSQL backups found"

# Бэкап Qdrant (если доступен)
echo "Backing up Qdrant..."
./scripts/backup_qdrant.sh || echo "Warning: Qdrant backup failed"

# Бэкап конфигураций
echo "Backing up configurations..."
tar -czf "${FULL_BACKUP_DIR}/configs.tar.gz" \
    config/ \
    knowledge_base/ \
    alembic/ \
    alembic.ini \
    2>/dev/null || echo "Warning: Config backup failed"

# Создание manifest файла
cat > "${FULL_BACKUP_DIR}/MANIFEST.txt" << EOF
Full Backup Manifest
====================
Timestamp: ${TIMESTAMP}
Date: $(date)

Contents:
- PostgreSQL database backup
- Qdrant vector store backup
- Configuration files

Restore Instructions:
1. Restore PostgreSQL: ./scripts/restore_db.sh <backup_file.sql.gz>
2. Restore Qdrant: Check Qdrant documentation
3. Extract configs: tar -xzf configs.tar.gz
EOF

echo "Full backup completed: ${FULL_BACKUP_DIR}"
