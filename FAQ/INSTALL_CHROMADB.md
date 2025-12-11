# Установка ChromaDB для Windows

## Проблема

ChromaDB требует компиляции `chroma-hnswlib`, для чего нужен Microsoft Visual C++ Build Tools.

## Решение 1: Установить Microsoft C++ Build Tools (рекомендуется)

1. Скачайте и установите [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. При установке выберите "C++ build tools"
3. После установки перезапустите терминал
4. Установите chromadb:
   ```bash
   .\venv\Scripts\activate
   pip install chromadb
   ```

## Решение 2: Использовать предкомпилированный wheel (если доступен)

Попробуйте установить chromadb с предкомпилированным wheel:
```bash
.\venv\Scripts\activate
pip install chromadb --only-binary :all:
```

## Решение 3: Использовать альтернативную векторную БД

Можно временно заменить ChromaDB на FAISS или другую векторную БД. Для этого нужно изменить код в `bot/rag_system.py`.

## Текущий статус

- ✅ Виртуальное окружение создано с Python 3.12
- ✅ Основные зависимости установлены (telegram, langchain, openai и т.д.)
- ❌ ChromaDB требует компиляции (нужен C++ Build Tools)

## После установки C++ Build Tools

Выполните:
```bash
.\venv\Scripts\activate
pip install chromadb
python main.py
```

