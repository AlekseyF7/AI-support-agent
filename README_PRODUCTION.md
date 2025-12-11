# Production Deployment Guide

## Обзор

Это руководство по развертыванию AI Support Agent в production-окружении.

## Архитектура

Система состоит из следующих компонентов:

- **PostgreSQL** - база данных для тикетов и логов
- **Qdrant** - векторное хранилище для RAG системы
- **FastAPI** - REST API бэкенд
- **Telegram Bot** - чат-бот для поддержки
- **Prometheus** - сбор метрик
- **Grafana** - визуализация метрик
- **ELK Stack** - логирование (Elasticsearch, Logstash, Kibana)

## Требования

- Docker и Docker Compose
- Минимум 4GB RAM
- 20GB свободного места на диске
- Доступ к интернету для загрузки образов

## Быстрый старт

1. **Клонирование репозитория**
```bash
git clone <repository-url>
cd AI-support-agent
```

2. **Настройка переменных окружения**

Создайте файл `.env`:
```bash
cp env.example .env
# Отредактируйте .env и добавьте ваши токены и пароли
```

3. **Запуск всех сервисов**
```bash
docker-compose up -d
```

4. **Применение миграций**
```bash
docker-compose exec api alembic upgrade head
```

5. **Загрузка базы знаний в Qdrant**
```bash
docker-compose exec api python -c "from vector_store import QdrantVectorStore; vs = QdrantVectorStore(); vs.load_knowledge_base()"
```

## Доступ к сервисам

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Kibana**: http://localhost:5601
- **PostgreSQL**: localhost:5432
- **Qdrant**: http://localhost:6333

## Мониторинг

### Prometheus метрики

Метрики доступны по адресу: http://localhost:8000/metrics

Основные метрики:
- `http_requests_total` - количество HTTP запросов
- `http_request_duration_seconds` - длительность запросов
- `active_tickets_total` - активные тикеты

### Grafana дашборды

Импортируйте дашборды из `config/grafana/dashboards/`

## Логирование

Логи отправляются в ELK Stack:
- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601

Индексы:
- `ai-support-logs-YYYY.MM.DD` - логи приложения
- `ai-support-raw-YYYY.MM.DD` - сырые логи

## Резервное копирование

### Автоматическое резервное копирование

Настроено через GitHub Actions (`.github/workflows/backup.yml`)

### Ручное резервное копирование

**PostgreSQL:**
```bash
./scripts/backup_db.sh
```

**Полный бэкап:**
```bash
./scripts/backup_all.sh
```

**Восстановление:**
```bash
./scripts/restore_db.sh backups/backup_support_db_YYYYMMDD_HHMMSS.sql.gz
```

## Масштабирование

### Горизонтальное масштабирование API

```yaml
# В docker-compose.yml
api:
  deploy:
    replicas: 3
```

### Настройка пула соединений PostgreSQL

В `database/connection.py`:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40
)
```

## Безопасность

1. **Измените все пароли по умолчанию**
2. **Настройте firewall** для ограничения доступа
3. **Используйте HTTPS** в production (через nginx/traefik)
4. **Регулярно обновляйте** Docker образы
5. **Мониторьте логи** на предмет подозрительной активности

## Обновление

1. **Остановите сервисы:**
```bash
docker-compose down
```

2. **Создайте бэкап:**
```bash
./scripts/backup_all.sh
```

3. **Обновите код:**
```bash
git pull
```

4. **Пересоберите образы:**
```bash
docker-compose build
```

5. **Запустите сервисы:**
```bash
docker-compose up -d
```

6. **Примените миграции:**
```bash
docker-compose exec api alembic upgrade head
```

## Troubleshooting

### Проблемы с подключением к базе данных

Проверьте логи:
```bash
docker-compose logs postgres
```

### Проблемы с Qdrant

Проверьте статус:
```bash
curl http://localhost:6333/health
```

### Проблемы с логированием

Проверьте Elasticsearch:
```bash
curl http://localhost:9200/_cluster/health
```

## Production чеклист

- [ ] Изменены все пароли по умолчанию
- [ ] Настроен SSL/TLS
- [ ] Настроен мониторинг и алерты
- [ ] Настроено автоматическое резервное копирование
- [ ] Настроен CI/CD pipeline
- [ ] Проведено нагрузочное тестирование
- [ ] Настроен disaster recovery план
- [ ] Документированы процедуры обновления
