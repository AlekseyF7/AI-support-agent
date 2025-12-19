""" 
Модели данных для системы поддержки Сбербанка.
Использует асинхронный SQLAlchemy 2.0+ для работы с базой данных.
"""
import enum
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from config import settings

logger = logging.getLogger(__name__)

# Базовый класс для моделей
Base = declarative_base()

class Criticality(enum.Enum):
    """Уровни критичности обращения для приоритезации в очереди."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SupportLine(enum.Enum):
    """Линии поддержки: L1 (базовая), L2 (техническая), L3 (экспертная)."""
    LINE_1 = "line_1"
    LINE_2 = "line_2"
    LINE_3 = "line_3"

class TicketStatus(enum.Enum):
    """Жизненный цикл заявки."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"

class Category(enum.Enum):
    """Тематическая классификация обращения."""
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    FEATURE = "feature"
    BUG = "bug"
    OTHER = "other"

class Ticket(Base):
    """
    Основная модель обращения (тикета).
    Хранит информацию о пользователе, проблему, историю и текущий статус.
    """
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, doc="Заголовок тикета")
    description = Column(Text, nullable=False, doc="Полное описание проблемы")
    user_id = Column(Integer, nullable=False, index=True, doc="Telegram ID пользователя")
    user_name = Column(String(255), nullable=True, doc="Имя пользователя в Telegram")
    
    category = Column(Enum(Category), nullable=False, index=True)
    criticality = Column(Enum(Criticality), nullable=False, index=True)
    support_line = Column(Enum(SupportLine), nullable=False, index=True)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, index=True)
    
    operator_id = Column(Integer, nullable=True, index=True, doc="ID оператора, взявшего тикет")
    operator_name = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    
    conversation_history = Column(Text, default="", doc="JSON-дамп истории диалога с ИИ")
    
    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, title='{self.title[:20]}...', status={self.status.value})>"

class TicketResponse(Base):
    """
    Модель ответа оператора или системы на обращение.
    """
    __tablename__ = "ticket_responses"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    operator_id = Column(Integer, nullable=False, doc="ID автора ответа (0 для системы)")
    operator_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=False, doc="Текст ответа")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# Конфигурация движка базы данных
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("sqlite:///"):
    # Автоматическое переключение на асинхронный драйвер
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

# echo=True полезен для отладки, но для продакшена лучше False
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# Настройка фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

async def init_db():
    """Инициализация таблиц базы данных."""
    logger.info("🎬 Инициализация схем базы данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ База данных готова.")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий для использования в хендлерах.
    Обеспечивает автоматическое закрытие сессии после выполнения.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
