# Реализация PB4, PB5, PB6

## Обзор

Реализованы три функциональных блока:
- **PB4**: Расширенная классификация тематики и критичности
- **PB5**: Логика обратной связи и эскалации
- **PB6**: Модель заявки и маршрутизация с БД

## PB4 - Классификация тематики и критичности

### Схема меток

**Тематика (система/сервис):**
- Доступ к системе
- Техническая проблема
- Программное обеспечение
- Оборудование
- Безопасность
- Конфигурация
- Системная проблема
- FAQ - Общие вопросы
- FAQ - Пароль
- FAQ - Антивирус
- Доступ к ресурсам
- Сетевая проблема

**Тип обращения:**
- `консультация` - Вопрос, нужна помощь, инструкция
- `инцидент` - Проблема, что-то не работает, ошибка

**Критичность:**
- `критическая` (P1) - Полная недоступность системы, утечка данных
- `высокая` (P2) - Недоступность для группы пользователей
- `средняя` (P3) - Проблемы с функциями
- `низкая` (P4) - Мелкие ошибки, FAQ

**Система/Сервис:**
- Корпоративный портал
- Почтовый сервер
- База данных
- Сетевое хранилище
- Система авторизации
- Антивирус
- Принтер/Сканер
- Wi-Fi
- VPN
- Другое

### Реализация

**Файлы:**
- `bot/ticket_models.py` - Модели данных (TicketClassification, Ticket, TicketType, TicketPriority, TicketStatus)
- `bot/classifier.py` - Обновленный классификатор с расширенной схемой меток

**Использование:**
```python
from bot.classifier import TicketClassifier
from bot.ticket_models import TicketClassification

classifier = TicketClassifier()
classification = classifier.classify("не могу войти в систему")

# classification.theme - тематика
# classification.ticket_type - тип (TicketType.CONSULTATION или TicketType.INCIDENT)
# classification.priority - критичность (TicketPriority.LOW/MEDIUM/HIGH/CRITICAL)
# classification.system_service - система/сервис
# classification.reasoning - обоснование
```

## PB5 - Логика "помог или нет" и эскалация

### Критерии успеха

**Сигналы удовлетворенности:**
- "спасибо", "благодарю", "помогло", "решило", "работает"
- "отлично", "хорошо", "понял", "ясно", "разобрался"
- "все ок", "все хорошо", "проблема решена"

**Сигналы неудовлетворенности:**
- "не помогло", "не работает", "не решило", "не понял"
- "все еще", "по-прежнему", "плохо", "неправильно"

### Цикл обратной связи

1. **Ответ бота** → Пользователь получает ответ из RAG
2. **Уточняющий вопрос** → "Помог ли вам ответ?"
3. **Анализ ответа** → Определение удовлетворенности
4. **Решение / Эскалация** → Если не удовлетворен → создание тикета

### Реализация

**Файлы:**
- `bot/feedback_system.py` - Система обратной связи

**Использование:**
```python
from bot.feedback_system import FeedbackSystem

feedback = FeedbackSystem()

# Проверка, нужно ли спрашивать обратную связь
if feedback.should_ask_feedback(user_id, has_good_answer=True, is_faq=True):
    question = feedback.get_feedback_question()
    # Отправить вопрос пользователю
    feedback.register_feedback_request(user_id, ticket_id, question)

# Анализ ответа пользователя
result = feedback.analyze_feedback(user_id, "да, помогло")
# result = "satisfied" или "not_satisfied" или None

# Определение необходимости эскалации
if feedback.should_escalate_after_feedback(result, "инцидент"):
    # Эскалировать тикет
```

## PB6 - Модель заявки и маршрутизация

### Структура обращения

**Основные поля:**
- `id` - Уникальный идентификатор
- `ticket_number` - Номер тикета (#001, #002, ...)
- `user_id` - ID пользователя Telegram
- `username` - Имя пользователя
- `title` - Заголовок (до 100 символов)
- `description` - Описание проблемы
- `classification` - Классификация (TicketClassification)
- `support_line` - Линия поддержки (1/2/3)
- `status` - Статус (NEW, IN_PROGRESS, WAITING_FOR_USER, RESOLVED, CLOSED, ESCALATED)
- `created_at` - Дата создания
- `updated_at` - Дата обновления

**Дополнительные поля:**
- `rag_answer` - Ответ из RAG
- `conversation_history` - История диалога
- `resolved` - Решено ли
- `resolution` - Решение
- `resolved_at` - Дата решения
- `tags` - Теги
- `assigned_to` - Назначено на
- `escalation_reason` - Причина эскалации
- `user_satisfaction` - Удовлетворенность пользователя

### База данных

**Технология:** SQLite (встроена в Python)

**Файл БД:** `data/tickets.db`

**Таблица `tickets`:**
- Все поля тикета
- Индексы для быстрого поиска по user_id, status, support_line, priority, created_at

### Модель очереди

**Очереди по линиям поддержки:**
- Линия 1: Service Desk (P3, P4, FAQ)
- Линия 2: Technical Support (P2, системные проблемы)
- Линия 3: Expert Support (P1, критические проблемы)

**Сортировка:**
- По приоритету (критическая → высокая → средняя → низкая)
- По дате создания (старые первыми)

### Логика маршрутизации

**Определение линии поддержки:**
1. FAQ вопросы → Линия 1
2. Критическая (P1) → Линия 3
3. Тематика в AUTO_ESCALATE_THEMES_3 → Линия 3
4. Тематика в AUTO_ESCALATE_THEMES_2 → Линия 2
5. По приоритету:
   - P1 (критическая) → Линия 3
   - P2 (высокая) → Линия 2
   - P3 (средняя) → Линия 1
   - P4 (низкая) → Линия 1

### Реализация

**Файлы:**
- `bot/ticket_models.py` - Модели данных
- `bot/ticket_database.py` - Работа с БД
- `bot/escalation_new.py` - Обновленная система эскалации

**Использование:**
```python
from bot.ticket_database import TicketDatabase
from bot.escalation_new import EscalationSystem
from bot.ticket_models import Ticket, TicketStatus

# Инициализация
db = TicketDatabase("data/tickets.db")
escalation = EscalationSystem("data/tickets.db")

# Создание тикета
ticket = escalation.create_ticket(
    user_id=123456,
    username="user",
    description="Не могу войти в систему",
    classification=classification,  # TicketClassification
    support_line=1,
    rag_answer="Ответ из RAG",
    conversation_history=["История диалога"]
)

# Получение очереди для линии поддержки
queue = escalation.get_tickets_by_line(support_line=1, status=TicketStatus.NEW)

# Обновление статуса
ticket = escalation.update_ticket_status(ticket, TicketStatus.RESOLVED, "Проблема решена")

# Эскалация
ticket = escalation.escalate_ticket(ticket, new_line=2, reason="Требуется экспертиза")
```

## Интеграция с существующим кодом

### Обновление telegram_bot.py

Для использования новых компонентов нужно обновить `bot/telegram_bot.py`:

1. Импортировать новые модули:
```python
from bot.ticket_models import Ticket, TicketStatus
from bot.feedback_system import FeedbackSystem
from bot.escalation_new import EscalationSystem
```

2. Обновить инициализацию:
```python
self.escalation = EscalationSystem()
self.feedback = FeedbackSystem()
```

3. Обновить обработку сообщений для работы с обратной связью

4. Обновить создание тикетов для использования новой модели

## Миграция данных

Если у вас уже есть тикеты в `data/tickets.json`, можно создать скрипт миграции для переноса в SQLite.

## Тестирование

Для тестирования новых функций:

1. **Классификация:**
```python
from bot.classifier import TicketClassifier
classifier = TicketClassifier()
result = classifier.classify("не могу войти в систему")
print(result.theme, result.ticket_type, result.priority)
```

2. **Обратная связь:**
```python
from bot.feedback_system import FeedbackSystem
feedback = FeedbackSystem()
result = feedback.analyze_feedback(123, "да, помогло")
print(result)  # "satisfied"
```

3. **БД:**
```python
from bot.ticket_database import TicketDatabase
db = TicketDatabase()
stats = db.get_queue_stats()
print(stats)
```

## Следующие шаги

1. Обновить `bot/telegram_bot.py` для интеграции новых компонентов
2. Протестировать все функции
3. При необходимости создать скрипт миграции данных
4. Добавить дополнительные функции (уведомления, статистика и т.д.)

