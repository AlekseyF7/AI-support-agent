# Быстрый старт

## Текущий статус

✅ Виртуальное окружение создано с Python 3.12  
✅ Основные зависимости установлены  
✅ Файл .env настроен с токенами  
⚠️ ChromaDB требует установки (нужен C++ Build Tools)

## Установка ChromaDB

Для установки ChromaDB нужен Microsoft Visual C++ Build Tools:

1. **Скачайте и установите** [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. При установке выберите "C++ build tools"
3. После установки перезапустите терминал
4. Установите chromadb:
   ```bash
   .\venv\Scripts\activate
   pip install chromadb
   ```

## Запуск бота

### Вариант 1: Использовать скрипт (рекомендуется)

**В PowerShell:**
```powershell
.\start_bot.bat
```

**В командной строке (cmd):**
```cmd
start_bot.bat
```

### Вариант 2: Вручную
```powershell
.\venv\Scripts\activate
python main.py
```

## Остановка бота

Если нужно остановить бота:

**В PowerShell:**
```powershell
.\stop_bot.bat
```

**В командной строке (cmd):**
```cmd
stop_bot.bat
```

**Важно:** В PowerShell всегда используйте `.\` перед именем скрипта!

## Что уже готово

- ✅ Python 3.12 в виртуальном окружении
- ✅ Все основные библиотеки (telegram, langchain, openai)
- ✅ Токены настроены в .env
- ⏳ Осталось только установить ChromaDB

## Альтернатива

Если не хотите устанавливать C++ Build Tools, можно временно использовать другую векторную БД (например, FAISS) или дождаться предкомпилированных wheels для Windows.

Подробнее см. `INSTALL_CHROMADB.md`

