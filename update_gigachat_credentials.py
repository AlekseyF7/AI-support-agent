"""Скрипт для обновления GigaChat учетных данных в .env файле"""
import os
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def update_gigachat_credentials():
    env_file = ".env"
    
    # Новые учетные данные
    new_client_id = "019b0ed1-945c-711f-ad56-c9437c25fb41"
    new_client_secret = "054c70ff-fb1c-44ed-a565-41e6eebe083b"
    
    if not os.path.exists(env_file):
        print("Файл .env не найден. Создаю новый...")
        # Создаем базовый файл
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"""# Giga Chat API
GIGACHAT_CLIENT_ID={new_client_id}
GIGACHAT_CLIENT_SECRET={new_client_secret}
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Telegram Bot
TELEGRAM_BOT_TOKEN=8320220590:AAEM77vO-EREFsdQEnk1Tbpocim9cxvI1lE

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
        updated_id = False
        updated_secret = False
        
        for line in content.split('\n'):
            if line.startswith('GIGACHAT_CLIENT_ID='):
                lines.append(f'GIGACHAT_CLIENT_ID={new_client_id}')
                updated_id = True
            elif line.startswith('GIGACHAT_CLIENT_SECRET='):
                lines.append(f'GIGACHAT_CLIENT_SECRET={new_client_secret}')
                updated_secret = True
            else:
                lines.append(line)
        
        # Если переменные не найдены, добавляем их
        if not updated_id:
            # Ищем место для вставки после Giga Chat API комментария
            insert_pos = -1
            for i, line in enumerate(lines):
                if line.startswith('# Giga Chat API') or line.startswith('GIGACHAT_'):
                    insert_pos = i
                    break
            if insert_pos >= 0:
                lines.insert(insert_pos + 1, f'GIGACHAT_CLIENT_ID={new_client_id}')
            else:
                lines.insert(0, f'GIGACHAT_CLIENT_ID={new_client_id}')
        
        if not updated_secret:
            # Ищем место после GIGACHAT_CLIENT_ID
            insert_pos = -1
            for i, line in enumerate(lines):
                if line.startswith('GIGACHAT_CLIENT_ID='):
                    insert_pos = i
                    break
            if insert_pos >= 0:
                lines.insert(insert_pos + 1, f'GIGACHAT_CLIENT_SECRET={new_client_secret}')
            else:
                lines.append(f'GIGACHAT_CLIENT_SECRET={new_client_secret}')
        
        with open(env_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        
        print("Файл .env обновлен!")
    
    # Показываем текущее состояние
    print("\nТекущие настройки GigaChat в .env:")
    print("-" * 60)
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and 'GIGACHAT' in line:
                key, value = line.split('=', 1)
                masked = value[:15] + "..." if len(value) > 15 else value
                print(f"[OK] {key}={masked}")
    print("-" * 60)
    print("\n✅ GigaChat учетные данные успешно обновлены!")

if __name__ == "__main__":
    try:
        update_gigachat_credentials()
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

