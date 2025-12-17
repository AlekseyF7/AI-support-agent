"""Конфигурация приложения"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    # Переопределяем stdout и stderr для UTF-8
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    # Устанавливаем кодовую страницу консоли в UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
        kernel32.SetConsoleCP(65001)  # UTF-8
    except:
        pass


class Settings(BaseSettings):
    # Giga Chat API
    GIGACHAT_CLIENT_ID: str = ""
    GIGACHAT_CLIENT_SECRET: str = ""
    GIGACHAT_AUTHORIZATION_KEY: str = ""  # Готовый Authorization Key (base64), имеет приоритет над client_id:client_secret
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"  # Стандартные значения: GIGACHAT_API_PERS, GIGACHAT_API_B2B, GIGACHAT_API_CORP
    GIGACHAT_WORKSPACE_ID: str = ""  # ID пространства (не используется для получения токена)
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Sber Salute Speech (SmartSpeech) for STT
    SALUTE_SPEECH_CLIENT_ID: str = ""
    SALUTE_SPEECH_CLIENT_SECRET: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./support.db"
    
    # RAG Settings
    CHROMA_DB_PATH: str = "./chroma_db"
    # Используем более надежную модель по умолчанию
    EMBEDDING_MODEL: str = "paraphrase-multilingual-mpnet-base-v2"
    
    # Operator Settings
    OPERATOR_IDS: str = ""  # Список ID операторов через запятую (например: "123456789,987654321")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def validate_settings(self):
        """Проверка обязательных настроек"""
        errors = []
        if not self.GIGACHAT_CLIENT_ID or self.GIGACHAT_CLIENT_ID == "your_client_id_here":
            errors.append("GIGACHAT_CLIENT_ID не установлен")
        if not self.GIGACHAT_CLIENT_SECRET or self.GIGACHAT_CLIENT_SECRET == "your_client_secret_here":
            errors.append("GIGACHAT_CLIENT_SECRET не установлен")
        if not self.TELEGRAM_BOT_TOKEN or self.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
        
        if errors:
            error_msg = "\n".join([f"❌ {e}" for e in errors])
            print("=" * 60)
            print("ОШИБКА КОНФИГУРАЦИИ")
            print("=" * 60)
            print(error_msg)
            print("\nДля создания файла .env выполните:")
            print("  python create_env.py")
            print("\nЗатем заполните переменные в файле .env:")
            print("1. GIGACHAT_CLIENT_ID - получите на https://developers.sber.ru/gigachat")
            print("2. GIGACHAT_CLIENT_SECRET - получите на https://developers.sber.ru/gigachat")
            print("3. TELEGRAM_BOT_TOKEN - получите у @BotFather в Telegram")
            print("=" * 60)
            raise ValueError("Не все обязательные настройки заполнены")


settings = Settings()

def get_settings():
    """Получение настроек с валидацией"""
    settings.validate_settings()
    return settings

