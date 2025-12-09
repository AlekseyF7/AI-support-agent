# Решение ошибки 429 (Insufficient Quota)

## Проблема

Ошибка: `Error code: 429 - insufficient_quota`

Это означает, что у вас закончился баланс или достигнут лимит использования на аккаунте OpenAI.

## Решения

### Вариант 1: Пополнить баланс OpenAI (рекомендуется)

1. Перейдите на https://platform.openai.com/account/billing
2. Добавьте способ оплаты (если еще не добавлен)
3. Пополните баланс
4. Проверьте лимиты использования в разделе "Usage limits"

### Вариант 2: Проверить лимиты использования

1. Откройте https://platform.openai.com/account/limits
2. Проверьте:
   - Rate limits (лимиты запросов в минуту)
   - Usage limits (общий лимит использования)
   - Billing limits (лимиты биллинга)

### Вариант 3: Использовать более дешевую модель

В файлах `bot/rag_system.py` и `bot/classifier.py` можно изменить модель на более дешевую:

**Текущая модель:**
```python
self.llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
```

**Более дешевые варианты:**
- `gpt-3.5-turbo-0125` - самая дешевая версия GPT-3.5
- `gpt-4o-mini` - мини-версия GPT-4 (дешевле чем GPT-4)

### Вариант 4: Использовать альтернативные провайдеры

Можно переключиться на другие LLM провайдеры:

#### Anthropic Claude (если доступен)
```python
from langchain_anthropic import ChatAnthropic
self.llm = ChatAnthropic(model="claude-3-haiku-20240307")
```

#### Google Gemini (если доступен)
```python
from langchain_google_genai import ChatGoogleGenerativeAI
self.llm = ChatGoogleGenerativeAI(model="gemini-pro")
```

#### Локальные модели через Ollama
```python
from langchain_community.llms import Ollama
self.llm = Ollama(model="llama2")
```

### Вариант 5: Оптимизировать использование

1. **Уменьшить количество запросов:**
   - Кэшировать ответы на часто задаваемые вопросы
   - Использовать более короткие промпты

2. **Использовать более дешевые модели для простых задач:**
   - GPT-3.5-turbo для классификации
   - GPT-4 только для сложных вопросов

3. **Уменьшить размер контекста:**
   - Меньше документов в RAG поиске
   - Более короткие чанки документов

## Временное решение: Обработка ошибки в коде

Код уже обновлен для обработки ошибки 429. Бот будет показывать понятное сообщение пользователю вместо падения.

## Проверка баланса

### Через веб-интерфейс:
1. https://platform.openai.com/account/billing
2. Проверьте "Available credits" или "Usage"

### Через API:
```python
import openai
client = openai.OpenAI()
# Проверка баланса (если доступно)
```

## Планы OpenAI

### Pay-as-you-go (оплата по использованию)
- Минимальный депозит: $5
- Оплата за каждый запрос
- Гибкий тариф

### Prepaid credits
- Покупка кредитов заранее
- Может быть выгоднее для больших объемов

## Мониторинг использования

1. Настройте уведомления о лимитах:
   - https://platform.openai.com/account/limits
   - Установите предупреждения при достижении 80%, 90% лимита

2. Отслеживайте использование:
   - Регулярно проверяйте dashboard
   - Используйте API для мониторинга

## Альтернативные решения

Если OpenAI недоступен или слишком дорог:

1. **ProxyAPI** (см. `PROXY_SERVICES.md`)
   - Может предоставлять доступ к OpenAI через прокси
   - Иногда с другими тарифами

2. **Локальные модели**
   - Ollama + Llama 2/Mistral
   - Полностью бесплатно
   - Требует мощный компьютер

3. **Другие облачные провайдеры**
   - Anthropic Claude
   - Google Gemini
   - Cohere

## Быстрая проверка

1. Откройте https://platform.openai.com/account/billing
2. Проверьте баланс
3. Если баланс = 0, пополните его
4. Перезапустите бота

## После пополнения баланса

```powershell
.\stop_bot.ps1
.\start_bot.ps1
```

Или с VPN:
```powershell
.\start_bot_with_vpn.ps1
```

