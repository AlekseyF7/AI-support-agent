# Решение проблем

## Проблема: ChromaDB несовместим с Python 3.14

**Ошибка:** `pydantic.v1.errors.ConfigError: unable to infer type for attribute "chroma_server_nofile"`

**Причина:** ChromaDB использует Pydantic v1, который не полностью совместим с Python 3.14.

### Решения:

#### Вариант 1: Использовать Python 3.11 или 3.12 (рекомендуется)

1. Установите Python 3.11 или 3.12
2. Создайте виртуальное окружение:
   ```bash
   python3.11 -m venv venv
   # или
   python3.12 -m venv venv
   ```
3. Активируйте окружение:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```
4. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

#### Вариант 2: Обновить ChromaDB

Попробуйте обновить chromadb до последней версии:
```bash
pip install --upgrade chromadb
```

#### Вариант 3: Использовать альтернативную векторную БД

Можно заменить ChromaDB на FAISS или другую векторную БД, совместимую с Python 3.14.

## Проблема: ModuleNotFoundError: No module named 'dotenv'

**Решение:**
```bash
pip install python-dotenv
```

## Проблема: HF_HUB_DOWNLOAD_TIMEOUT ошибка

**Ошибка:** `ValueError: invalid literal for int() with base 10: 'HF_HUB_DOWNLOAD_TIMEOUT = 1200'`

**Решение:**
Используйте `run_bot.py` вместо `main.py` - он автоматически исправляет эту проблему.

Или вручную исправьте переменную окружения:
```bash
# Windows PowerShell
$env:HF_HUB_DOWNLOAD_TIMEOUT = "1200"

# Linux/Mac
export HF_HUB_DOWNLOAD_TIMEOUT=1200
```

## Проблема: Импорты LangChain

Если возникают ошибки с импортами LangChain, убедитесь, что установлены все зависимости:
```bash
pip install langchain langchain-community langchain-openai langchain-core
```

## Рекомендации

Для стабильной работы рекомендуется:
- Python 3.11 или 3.12
- Использовать виртуальное окружение
- Регулярно обновлять зависимости

