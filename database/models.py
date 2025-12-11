"""
SQLAlchemy модели для PostgreSQL
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base


class Ticket(Base):
    """Модель тикета"""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255))
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    theme = Column(String(100), nullable=False, index=True)
    ticket_type = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False, index=True)
    system_service = Column(String(255))
    reasoning = Column(Text)
    support_line = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    rag_answer = Column(Text)
    conversation_history = Column(JSONB)
    resolved = Column(Boolean, default=False)
    resolution = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    tags = Column(JSONB)
    assigned_to = Column(String(255))
    escalation_reason = Column(Text)
    user_satisfaction = Column(String(50))

    # Связи
    logs = relationship("Log", back_populates="ticket", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('support_line IN (1, 2, 3)', name='check_support_line'),
        Index('idx_tickets_conversation_history', 'conversation_history', postgresql_using='gin'),
        Index('idx_tickets_tags', 'tags', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<Ticket {self.ticket_number}: {self.title}>"


class Log(Base):
    """Модель лога"""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    level = Column(String(20), nullable=False, index=True)
    logger_name = Column(String(255), index=True)
    message = Column(Text, nullable=False)
    module = Column(String(255))
    function_name = Column(String(255))
    line_number = Column(Integer)
    user_id = Column(Integer, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), index=True)
    extra_data = Column(JSONB)
    traceback = Column(Text)

    # Связи
    ticket = relationship("Ticket", back_populates="logs")

    __table_args__ = (
        Index('idx_logs_timestamp_level', 'timestamp', 'level'),
    )

    def __repr__(self):
        return f"<Log {self.level}: {self.message[:50]}>"
