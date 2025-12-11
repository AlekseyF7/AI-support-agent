# Быстрое решение проблем

## Ошибка "Conflict: terminated by other getUpdates request"

Эта ошибка означает, что запущено несколько экземпляров бота одновременно.

### Решение:

1. **Остановите все экземпляры бота:**
   ```powershell
   .\stop_bot.bat
   ```
   Или в командной строке:
   ```cmd
   stop_bot.bat
   ```

2. **Подождите 2-3 секунды**

3. **Запустите бота снова:**
   ```powershell
   .\start_bot.bat
   ```
   Или:
   ```powershell
   .\venv\Scripts\activate
   python main.py
   ```

## Другие способы остановки бота

### Через диспетчер задач:
1. Откройте Диспетчер задач (Ctrl+Shift+Esc)
2. Найдите процессы `python.exe`
3. Остановите те, которые запускают `main.py`

### Через PowerShell:
```powershell
Get-Process python | Where-Object {$_.Path -like "*venv*"} | Stop-Process -Force
```

## Проверка, что бот запущен

После запуска вы должны увидеть:
```
Инициализация RAG системы...
Загрузка базы знаний...
Запуск Telegram бота...
```

Если видите эти сообщения - бот работает!

