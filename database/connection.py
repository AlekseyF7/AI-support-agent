"""
Подключение к PostgreSQL
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# URL подключения к базе данных
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://support_user:support_password@localhost:5432/support_db"
)

# Создание движка
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"
)

# Сессия
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db():
    """Генератор сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
