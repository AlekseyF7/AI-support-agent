# Установка ChromaDB с Build Tools

Поскольку Build Tools установлены по нестандартному пути, выполните следующие шаги:

## Способ 1: Использование Developer Command Prompt

1. Откройте "Developer Command Prompt for VS" или "x64 Native Tools Command Prompt"
   - Найдите в меню Пуск: "Visual Studio 2022" -> "x64 Native Tools Command Prompt"
   
2. Перейдите в директорию проекта:
   ```cmd
   cd C:\Users\Тимур\Desktop\ai_client_helper
   ```

3. Активируйте виртуальное окружение:
   ```cmd
   myenv312\Scripts\activate
   ```

4. Установите chromadb:
   ```cmd
   pip install chromadb==0.4.22 sentence-transformers
   ```

## Способ 2: Использование готового batch файла

1. Откройте Developer Command Prompt (см. способ 1)

2. Перейдите в директорию проекта и запустите:
   ```cmd
   install_chromadb.bat
   ```

## Альтернативный способ: Использование conda

Если Build Tools не работают, можно использовать conda для установки chromadb:
```bash
conda install -c conda-forge chromadb
```

