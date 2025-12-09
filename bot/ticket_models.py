"""
Модели данных для тикетов и обращений
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class TicketType(Enum):
    """Тип обращения"""
    CONSULTATION = "консультация"  # Вопрос, нужна помощь
    INCIDENT = "инцидент"  # Проблема, что-то не работает


class TicketPriority(Enum):
    """Критичность обращения"""
    LOW = "низкая"  # P4
    MEDIUM = "средняя"  # P3
    HIGH = "высокая"  # P2
    CRITICAL = "критическая"  # P1


class TicketStatus(Enum):
    """Статус обращения"""
    NEW = "Новое"
    IN_PROGRESS = "В работе"
    WAITING_FOR_USER = "Ожидание ответа пользователя"
    RESOLVED = "Решено"
    CLOSED = "Закрыто"
    ESCALATED = "Эскалировано"


@dataclass
class TicketClassification:
    """Классификация обращения"""
    theme: str  # Тематика (система/сервис)
    ticket_type: TicketType  # Тип (консультация/инцидент)
    priority: TicketPriority  # Критичность
    system_service: Optional[str] = None  # Конкретная система/сервис
    reasoning: str = ""  # Обоснование классификации


@dataclass
class Ticket:
    """Модель обращения"""
    id: int
    ticket_number: str
    user_id: int
    username: str
    title: str  # Заголовок
    description: str  # Описание проблемы
    classification: TicketClassification
    support_line: int  # Линия поддержки (1/2/3)
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    
    # Дополнительные поля
    rag_answer: Optional[str] = None  # Ответ из RAG
    conversation_history: Optional[List[str]] = None  # История диалога
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    # Метаданные
    tags: Optional[List[str]] = None
    assigned_to: Optional[str] = None
    escalation_reason: Optional[str] = None
    user_satisfaction: Optional[str] = None  # "satisfied", "not_satisfied", "no_feedback"
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь для сохранения"""
        data = asdict(self)
        # Преобразуем Enum в строки
        data['ticket_type'] = self.classification.ticket_type.value
        data['priority'] = self.classification.priority.value
        data['status'] = self.status.value
        # Преобразуем datetime в строки
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        # Классификация
        data['theme'] = self.classification.theme
        data['system_service'] = self.classification.system_service
        data['reasoning'] = self.classification.reasoning
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Ticket':
        """Создание из словаря"""
        # Преобразуем строки обратно в Enum
        ticket_type = TicketType(data.get('ticket_type', 'консультация'))
        priority = TicketPriority(data.get('priority', 'средняя'))
        status = TicketStatus(data.get('status', 'Новое'))
        
        # Преобразуем строки в datetime
        created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        updated_at = datetime.fromisoformat(data['updated_at']) if isinstance(data['updated_at'], str) else data['updated_at']
        resolved_at = None
        if data.get('resolved_at'):
            resolved_at = datetime.fromisoformat(data['resolved_at']) if isinstance(data['resolved_at'], str) else data['resolved_at']
        
        # Классификация
        classification = TicketClassification(
            theme=data.get('theme', 'Техническая проблема'),
            ticket_type=ticket_type,
            priority=priority,
            system_service=data.get('system_service'),
            reasoning=data.get('reasoning', '')
        )
        
        return cls(
            id=data['id'],
            ticket_number=data['ticket_number'],
            user_id=data['user_id'],
            username=data['username'],
            title=data.get('title', data.get('description', '')[:100]),
            description=data['description'],
            classification=classification,
            support_line=data['support_line'],
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            rag_answer=data.get('rag_answer'),
            conversation_history=data.get('conversation_history'),
            resolved=data.get('resolved', False),
            resolution=data.get('resolution'),
            resolved_at=resolved_at,
            tags=data.get('tags'),
            assigned_to=data.get('assigned_to'),
            escalation_reason=data.get('escalation_reason'),
            user_satisfaction=data.get('user_satisfaction')
        )

