"""Модели данных для системы поддержки"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
from config import settings

Base = declarative_base()


class Criticality(enum.Enum):
    """Уровни критичности обращения"""
    LOW = "low"  # Низкая
    MEDIUM = "medium"  # Средняя
    HIGH = "high"  # Высокая
    CRITICAL = "critical"  # Критическая


class SupportLine(enum.Enum):
    """Линии поддержки"""
    LINE_1 = "line_1"  # Первая линия - типовые вопросы
    LINE_2 = "line_2"  # Вторая линия - технические вопросы
    LINE_3 = "line_3"  # Третья линия - сложные/критичные вопросы


class TicketStatus(enum.Enum):
    """Статусы заявки"""
    OPEN = "open"  # Открыта
    IN_PROGRESS = "in_progress"  # В работе
    ESCALATED = "escalated"  # Эскалирована
    RESOLVED = "resolved"  # Решена
    CLOSED = "closed"  # Закрыта


class Category(enum.Enum):
    """Категории обращений"""
    TECHNICAL = "technical"  # Технические вопросы
    BILLING = "billing"  # Вопросы по оплате
    ACCOUNT = "account"  # Вопросы по аккаунту
    FEATURE = "feature"  # Функциональность
    BUG = "bug"  # Ошибки
    OTHER = "other"  # Прочее


class Ticket(Base):
    """Модель заявки (обращения)"""
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)  # Telegram user ID
    user_name = Column(String(255))
    
    # Классификация
    category = Column(Enum(Category), nullable=False)
    criticality = Column(Enum(Criticality), nullable=False)
    support_line = Column(Enum(SupportLine), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    
    # Оператор
    operator_id = Column(Integer, nullable=True)  # Telegram ID оператора, взявшего тикет
    operator_name = Column(String(255), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # История взаимодействий
    conversation_history = Column(Text, default="")  # JSON строка с историей
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, title='{self.title}', line={self.support_line.value}, status={self.status.value})>"


class TicketResponse(Base):
    """Модель ответа оператора на тикет"""
    __tablename__ = "ticket_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, nullable=False, index=True)
    operator_id = Column(Integer, nullable=False)  # Telegram ID оператора
    operator_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TicketResponse(id={self.id}, ticket_id={self.ticket_id}, operator_id={self.operator_id})>"


# Создание движка БД
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

