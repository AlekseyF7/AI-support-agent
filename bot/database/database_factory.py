"""
Фабрика для создания подключений к базам данных (SQLite или PostgreSQL)
"""
import os
from typing import Optional
from .sqlite_db import SQLiteTicketDatabase
from .postgres_db import PostgresTicketDatabase


class DatabaseFactory:
    """Фабрика для создания подключений к БД"""
    
    @staticmethod
    def create_database(db_type: Optional[str] = None) -> 'TicketDatabase':
        """
        Создать подключение к базе данных
        
        Args:
            db_type: Тип БД ('sqlite', 'postgresql' или None для автоопределения)
            
        Returns:
            Экземпляр базы данных
        """
        if db_type is None:
            db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "postgresql" or db_type == "postgres":
            return PostgresTicketDatabase()
        else:
            return SQLiteTicketDatabase()
    
    @staticmethod
    def get_database_url() -> Optional[str]:
        """Получить URL базы данных из переменных окружения"""
        return os.getenv("DATABASE_URL")


def get_database() -> 'TicketDatabase':
    """Получить экземпляр базы данных (singleton pattern)"""
    if not hasattr(get_database, '_instance'):
        get_database._instance = DatabaseFactory.create_database()
    return get_database._instance
