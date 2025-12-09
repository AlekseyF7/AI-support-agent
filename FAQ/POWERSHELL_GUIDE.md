# Руководство по запуску в PowerShell

## ⚠️ ВАЖНО: Синтаксис команд

В PowerShell **ВСЕГДА** используйте `.\` перед именем скрипта:

✅ **Правильно:**
```powershell
.\start_bot.ps1
.\stop_bot.ps1
```

❌ **Неправильно:**
```powershell
start_bot.ps1    # Не работает!
stop_bot.ps1     # Не работает!
```

## Проблема с кириллицей в пути

Если у вас кириллица в пути (например, имя пользователя "Тимур"), PowerShell может не найти `.bat` файлы. 

## Решения

### Вариант 1: Использовать PowerShell скрипты (рекомендуется)

**Запуск бота:**
```powershell

```

**Остановка бота:**
```powershell
.\stop_bot.ps1
```

### Вариант 2: Использовать cmd напрямую

**Запуск бота:**
```powershell
cmd /c start_bot.bat
```

**Остановка бота:**
```powershell
cmd /c stop_bot.bat
```

### Вариант 3: Запуск напрямую через Python

```powershell
.\venv\Scripts\python.exe main.py
```

### Вариант 4: Использовать полный путь

```powershell
& "C:\Users\Тимур\Desktop\ai_client_helper\start_bot.bat"
```

## Если PowerShell блокирует выполнение скриптов

Если видите ошибку "execution of scripts is disabled", выполните:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Это разрешит выполнение локальных скриптов.

## Проверка текущей директории

Если не уверены, что находитесь в правильной директории:

```powershell
Get-Location
```

Или перейдите в директорию проекта:

```powershell
cd "C:\Users\Тимур\Desktop\ai_client_helper"
```

## Альтернатива: Использовать командную строку (cmd)

Откройте командную строку (cmd) вместо PowerShell:

1. Нажмите Win+R
2. Введите `cmd` и нажмите Enter
3. Перейдите в директорию проекта:
   ```cmd
   cd C:\Users\Тимур\Desktop\ai_client_helper
   ```
4. Запустите:
   ```cmd
   start_bot.bat
   ```

