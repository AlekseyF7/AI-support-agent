"""Скрипт для обновления .env файла"""
import os
import sys

def update_env_file():
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("Файл .env не найден. Создаю новый...")
        # Создаем базовый файл
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("""# Giga Chat API
GIGACHAT_CLIENT_ID=your_client_id_here
GIGACHAT_CLIENT_SECRET=019abab6-bd14-7795-9e69-7d649ba885f2
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Telegram Bot
TELEGRAM_BOT_TOKEN=7997172973:AAGua_7gStPKRwNH0JznzkaRtTcPg8E2HxQ

# Database
DATABASE_URL=sqlite:///./support.db

# RAG Settings
CHROMA_DB_PATH=./chroma_db
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
""")
        print("Файл .env создан!")
    else:
        # Читаем текущий файл
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Обновляем значения
        lines = []
        for line in content.split('\n'):
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                lines.append('TELEGRAM_BOT_TOKEN=7997172973:AAGua_7gStPKRwNH0JznzkaRtTcPg8E2HxQ')
            elif line.startswith('GIGACHAT_CLIENT_SECRET='):
                lines.append('GIGACHAT_CLIENT_SECRET=019abab6-bd14-7795-9e69-7d649ba885f2')
            else:
                lines.append(line)
        
        with open(env_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        print("Файл .env обновлен!")
    
    # Показываем текущее состояние
    print("\nТекущие настройки в .env:")
    print("-" * 60)
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if 'TOKEN' in line or 'SECRET' in line or 'ID' in line:
                    key, value = line.split('=', 1)
                    if 'your_' in value or value == '':
                        print(f"[!] {key}=[НЕ ЗАПОЛНЕНО]")
                    else:
                        # Скрываем полное значение для безопасности
                        masked = value[:10] + "..." if len(value) > 10 else value
                        print(f"[OK] {key}={masked}")
    print("-" * 60)
    print("\n[!] ВНИМАНИЕ: GIGACHAT_CLIENT_ID все еще не заполнен!")
    print("Получите его на https://developers.sber.ru/gigachat")

if __name__ == "__main__":
    update_env_file()

