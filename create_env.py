"""Скрипт для создания файла .env"""
import os

env_content = """# Giga Chat API
# Получите эти данные на https://developers.sber.ru/gigachat
GIGACHAT_CLIENT_ID=your_client_id_here
GIGACHAT_CLIENT_SECRET=your_client_secret_here
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Telegram Bot
# Получите токен у @BotFather в Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Sber Salute Speech (SmartSpeech) для распознавания речи
# Получите Client ID / Client Secret на https://developers.sber.ru/
SALUTE_SPEECH_CLIENT_ID=your_salute_speech_client_id_here
SALUTE_SPEECH_CLIENT_SECRET=your_salute_speech_client_secret_here

# Database
DATABASE_URL=sqlite:///./support.db

# RAG Settings
CHROMA_DB_PATH=./chroma_db
EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2
"""

if __name__ == "__main__":
    if os.path.exists(".env"):
        print("Файл .env уже существует!")
        response = input("Перезаписать? (y/n): ")
        if response.lower() != "y":
            print("Отменено.")
            exit(0)
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("Файл .env создан успешно!")
    print("\nВАЖНО: Заполните следующие переменные в файле .env:")
    print("1. GIGACHAT_CLIENT_ID - получите на https://developers.sber.ru/gigachat")
    print("2. GIGACHAT_CLIENT_SECRET - получите на https://developers.sber.ru/gigachat")
    print("3. TELEGRAM_BOT_TOKEN - получите у @BotFather в Telegram")
    print("4. SALUTE_SPEECH_CLIENT_ID / SALUTE_SPEECH_CLIENT_SECRET - получите на https://developers.sber.ru/ для Salute Speech")

