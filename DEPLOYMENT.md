# Руководство по развертыванию

## Быстрый старт

### 1. Подготовка окружения

```bash
# Клонирование репозитория
git clone <repository-url>
cd AI-support-agent

# Копирование примера конфигурации
cp env.example .env

# Редактирование .env файла
nano .env  # или используйте любой редактор
```

### 2. Запуск через Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### 3. Инициализация базы данных

```bash
# Применение миграций
docker-compose exec api alembic upgrade head

# Загрузка базы знаний в Qdrant
docker-compose exec api python -c "from vector_store import QdrantVectorStore; vs = QdrantVectorStore(); vs.load_knowledge_base()"
```

## Структура сервисов

### Порты

- **8000** - FastAPI API
- **5432** - PostgreSQL
- **6333** - Qdrant API
- **6334** - Qdrant gRPC
- **9090** - Prometheus
- **3000** - Grafana
- **5601** - Kibana
- **9200** - Elasticsearch
- **5044** - Logstash

### Переменные окружения

Основные переменные (см. `env.example`):

- `DATABASE_URL` - строка подключения к PostgreSQL
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `OPENAI_API_KEY` - ключ OpenAI API
- `QDRANT_URL` - URL Qdrant сервера

## Мониторинг

### Prometheus

Метрики доступны по адресу: http://localhost:9090

Эндпоинты метрик:
- `http://localhost:8000/metrics` - метрики FastAPI
- `http://localhost:6333/metrics` - метрики Qdrant

### Grafana

Вход: http://localhost:3000
- Логин: `admin` (или из переменной `GRAFANA_USER`)
- Пароль: из переменной `GRAFANA_PASSWORD`

### Kibana

Вход: http://localhost:5601

Индексы для поиска:
- `ai-support-logs-*` - логи приложения
- `ai-support-raw-*` - сырые логи

## Резервное копирование

### Автоматическое

Настроено через GitHub Actions (ежедневно в 2:00 UTC)

### Ручное

```bash
# PostgreSQL
./scripts/backup_db.sh

# Полный бэкап
./scripts/backup_all.sh

# Восстановление
./scripts/restore_db.sh backups/backup_support_db_YYYYMMDD_HHMMSS.sql.gz
```

## Обновление

```bash
# Остановка
docker-compose down

# Бэкап
./scripts/backup_all.sh

# Обновление кода
git pull

# Пересборка
docker-compose build

# Запуск
docker-compose up -d

# Миграции
docker-compose exec api alembic upgrade head
```

## Troubleshooting

### Проблемы с базой данных

```bash
# Проверка подключения
docker-compose exec postgres psql -U support_user -d support_db -c "SELECT 1"

# Просмотр логов
docker-compose logs postgres
```

### Проблемы с Qdrant

```bash
# Проверка здоровья
curl http://localhost:6333/health

# Просмотр коллекций
curl http://localhost:6333/collections
```

### Проблемы с логированием

```bash
# Проверка Elasticsearch
curl http://localhost:9200/_cluster/health

# Просмотр логов Logstash
docker-compose logs logstash
```

## Production рекомендации

1. **Измените все пароли по умолчанию**
2. **Настройте SSL/TLS** через reverse proxy (nginx/traefik)
3. **Настройте firewall** для ограничения доступа
4. **Регулярно обновляйте** Docker образы
5. **Мониторьте ресурсы** (CPU, RAM, диск)
6. **Настройте алерты** в Prometheus/Grafana
7. **Проверьте бэкапы** регулярно
