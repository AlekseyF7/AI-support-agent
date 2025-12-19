# 🏦 AI Support Agent — Platinum Edition

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-0088cc?logo=telegram&logoColor=white)
![GigaChat](https://img.shields.io/badge/GigaChat-LLM-21a038?logo=googlechat&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

**Интеллектуальный агент поддержки 1-й линии для внутренних сервисов банка**

[Быстрый старт](#-быстрый-старт) • [Технологии](#-технологический-стек) • [Архитектура](#-архитектура) • [Возможности](FEATURES.md) • [API](#-api-справочник)

</div>

---

## 📋 Описание

AI Support Agent решает задачи автоматизации 1-й линии поддержки:

- 🧠 **Определение тематики** — LLM классифицирует запрос по категории, критичности и линии поддержки
- 📚 **RAG система** — ответы на типовые вопросы из векторной базы знаний
- 🔄 **Самооценка** — агент определяет, помог ли он пользователю
- 📋 **Условная эскалация** — тикет создаётся только если ИИ не справился
- 🔀 **Маршрутизация** — автоматическое распределение на 1/2/3 линию поддержки
- 🎙️ **Мультимодальность** — текст, голос, изображения

---

## 🛠 Технологический стек

### Core
| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Язык** | Python | 3.11+ | Основной язык разработки |
| **Бот-фреймворк** | Aiogram | 3.x | Асинхронный Telegram Bot API |
| **LLM** | GigaChat | API v1 | Генерация ответов, классификация, Vision |
| **Векторная БД** | ChromaDB | 0.4+ | Хранение эмбеддингов для RAG |
| **Эмбеддинги** | SentenceTransformers | - | Локальная модель `multilingual-e5-small` |
| **SQL БД** | SQLite + aiosqlite | - | Хранение тикетов и сессий |
| **ORM** | SQLAlchemy | 2.0+ | Асинхронная работа с БД |

### Интеграции
| Сервис | Назначение |
|--------|------------|
| **Sber Salute Speech** | Распознавание голосовых сообщений (STT) |
| **2GIS Places API** | Поиск ближайших отделений банка |
| **Telegram Mini App** | Интерактивная карта (O2O) |
| **Ngrok** | HTTPS-туннель для Mini App |

### DevOps
| Инструмент | Назначение |
|------------|------------|
| **Docker** | Контейнеризация приложения |
| **Docker Compose** | Оркестрация сервисов (bot, api, ngrok) |
| **Multi-stage Build** | Оптимизация размера образа |

---

## 🏗 Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                      TELEGRAM                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Текст 📝 │  │ Голос 🎙️ │  │ Фото 📷  │  │ MiniApp 📍│     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
└───────┼─────────────┼─────────────┼─────────────┼────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌───────────────────────────────────────────────────────────────┐
│                      BOT.PY (Dispatcher)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ DbMiddleware│  │ Escalation  │  │ Handlers            │   │
│  │             │  │ Middleware  │  │ (user/admin/common) │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
        │                │                    │
        ▼                ▼                    ▼
┌───────────────┐ ┌──────────────┐ ┌────────────────────────────┐
│  SQLAlchemy   │ │ EscalationSys│ │      CLASSIFIER.PY         │
│  (Tickets DB) │ │ (ChromaDB)   │ │  ┌──────────────────────┐  │
└───────────────┘ └──────────────┘ │  │ classify() → JSON    │  │
                                   │  │ assess_response()    │  │
                                   │  └──────────────────────┘  │
                                   └─────────────┬──────────────┘
                                                 │
                                                 ▼
┌───────────────────────────────────────────────────────────────┐
│                       GIGACHAT API                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Chat/LLM    │  │ Embeddings  │  │ Vision      │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└───────────────────────────────────────────────────────────────┘
```

---

## 🚀 Быстрый старт

### 1. Клонирование
```bash
git clone https://github.com/your-repo/ai-support-agent.git
cd ai-support-agent
```

### 2. Настройка окружения
```bash
python manage.py env init
# Заполните .env своими ключами API
```

### 3. Запуск
```bash
docker compose up -d --build
```

### 4. Назначение оператора
```bash
python manage.py operators add YOUR_TELEGRAM_ID
docker compose restart bot
```

---

## 📁 Структура проекта

```
AI-support-agent/
├── bot.py                 # Точка входа, DI, lifecycle
├── config.py              # Pydantic Settings
├── models.py              # SQLAlchemy модели (Ticket, Response)
├── classifier.py          # LLM классификация + self-assessment
├── escalation.py          # Система тикетов + дедупликация
├── rag_system.py          # RAG на ChromaDB
├── gigachat_client.py     # GigaChat SDK wrapper
├── salute_speech_client.py# Sber STT клиент
├── geo_service.py         # 2GIS API интеграция
├── app_server.py          # FastAPI для Mini App
├── handlers/
│   ├── user.py            # Хендлеры пользователя
│   ├── admin.py           # Хендлеры оператора
│   └── common.py          # Общие команды
├── keyboards/
│   ├── client_kb.py       # Клавиатура пользователя
│   └── operator_kb.py     # Клавиатура оператора
├── middlewares/
│   └── db.py              # Сессии SQLAlchemy
├── sber_hunter.py          # Продвинутый парсер на Playwright
├── webapp/
│   └── index.html         # Mini App (2GIS карта)
├── Dockerfile             # Multi-stage build
├── docker-compose.yml     # 3 сервиса: bot, api, ngrok
└── manage.py              # CLI утилита
```

---

## 🔑 Переменные окружения

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен от @BotFather |
| `GIGACHAT_AUTHORIZATION_KEY` | ✅ | Ключ GigaChat API |
| `SALUTE_SPEECH_CLIENT_ID` | ❌ | ID для голосового ввода |
| `SALUTE_SPEECH_CLIENT_SECRET` | ❌ | Секрет Salute Speech |
| `DG_API_KEY` | ❌ | Ключ 2GIS для карты |
| `NGROK_AUTHTOKEN` | ❌ | Токен для HTTPS-туннеля |
| `OPERATOR_IDS` | ❌ | Telegram ID операторов (через запятую) |

---

## 📡 API справочник

### Команды пользователя
| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и главное меню |
| `/help` | Справка по функциям |
| `/clear` | Очистка контекста диалога |

### Команды оператора
| Команда | Описание |
|---------|----------|
| `/tickets` | Список активных заявок |
| `/ticket <id>` | Детали заявки |
| `/take <id>` | Взять в работу |
| `/reply <id> <text>` | Ответить пользователю |
| `/close <id>` | Закрыть заявку |
| `/stats` | Статистика по линиям |
| `/metrics` | Эффективность AI (KPI) |
| `/hunt` | Запуск Shadow Hunter (CLI) |

---

## 📄 Лицензия

MIT License © 2024
