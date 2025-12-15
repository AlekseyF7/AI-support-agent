"""Скрипт для обновления Authorization Key в .env файле"""
import os
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def update_auth_key():
    env_file = ".env"
    
    # Authorization Key
    auth_key = "MDE5YjBlZDEtOTQ1Yy03MTFmLWFkNTYtYzk0MzdjMjVmYjQxOjA1NGM3MGZmLWZiMWMtNDRlZC1hNTY1LTQxZTZlZWJlMDgzYg=="
    
    if not os.path.exists(env_file):
        print("Файл .env не найден. Создаю новый...")
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"""# Giga Chat API
GIGACHAT_AUTHORIZATION_KEY={auth_key}
GIGACHAT_CLIENT_ID=019b0ed1-945c-711f-ad56-c9437c25fb41
GIGACHAT_CLIENT_SECRET=054c70ff-fb1c-44ed-a565-41e6eebe083b
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
        updated_auth_key = False
        
        for line in content.split('\n'):
            if line.startswith('GIGACHAT_AUTHORIZATION_KEY='):
                lines.append(f'GIGACHAT_AUTHORIZATION_KEY={auth_key}')
                updated_auth_key = True
            else:
                lines.append(line)
        
        # Если переменная не найдена, добавляем её после Giga Chat API комментария
        if not updated_auth_key:
            insert_pos = -1
            for i, line in enumerate(lines):
                if line.startswith('# Giga Chat API'):
                    insert_pos = i
                    break
            if insert_pos >= 0:
                lines.insert(insert_pos + 1, f'GIGACHAT_AUTHORIZATION_KEY={auth_key}')
            else:
                # Если комментарий не найден, ищем место после других GIGACHAT_ переменных
                for i, line in enumerate(lines):
                    if line.startswith('GIGACHAT_'):
                        insert_pos = i
                        break
                if insert_pos >= 0:
                    lines.insert(insert_pos, f'GIGACHAT_AUTHORIZATION_KEY={auth_key}')
                else:
                    lines.insert(0, f'GIGACHAT_AUTHORIZATION_KEY={auth_key}')
        
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
                if 'AUTHORIZATION_KEY' in key:
                    masked = value[:30] + "..." if len(value) > 30 else value
                    print(f"[OK] {key}={masked}")
                else:
                    masked = value[:15] + "..." if len(value) > 15 else value
                    print(f"[OK] {key}={masked}")
    print("-" * 60)
    print("\n✅ Authorization Key успешно обновлен!")
    print("Теперь бот будет использовать готовый Authorization Key напрямую.")

if __name__ == "__main__":
    try:
        update_auth_key()
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

