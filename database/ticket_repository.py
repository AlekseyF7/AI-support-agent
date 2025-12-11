"""
Репозиторий для работы с тикетами в PostgreSQL
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from datetime import datetime
from .models import Ticket
from bot.ticket_models import Ticket as TicketModel, TicketStatus, TicketPriority, TicketType, TicketClassification


class TicketRepository:
    """Репозиторий для работы с тикетами"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, ticket: TicketModel) -> Ticket:
        """Создание нового тикета"""
        db_ticket = Ticket(
            ticket_number=ticket.ticket_number or self._generate_ticket_number(),
            user_id=ticket.user_id,
            username=ticket.username,
            title=ticket.title,
            description=ticket.description,
            theme=ticket.classification.theme,
            ticket_type=ticket.classification.ticket_type.value,
            priority=ticket.classification.priority.value,
            system_service=ticket.classification.system_service,
            reasoning=ticket.classification.reasoning,
            support_line=ticket.support_line,
            status=ticket.status.value,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            rag_answer=ticket.rag_answer,
            conversation_history=ticket.conversation_history,
            resolved=ticket.resolved,
            resolution=ticket.resolution,
            resolved_at=ticket.resolved_at,
            tags=ticket.tags,
            assigned_to=ticket.assigned_to,
            escalation_reason=ticket.escalation_reason,
            user_satisfaction=ticket.user_satisfaction
        )
        self.db.add(db_ticket)
        self.db.commit()
        self.db.refresh(db_ticket)
        return db_ticket

    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Получение тикета по ID"""
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()

    def get_by_ticket_number(self, ticket_number: str) -> Optional[Ticket]:
        """Получение тикета по номеру"""
        return self.db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    def get_by_user(self, user_id: int, limit: int = 10) -> List[Ticket]:
        """Получение тикетов пользователя"""
        return self.db.query(Ticket).filter(
            Ticket.user_id == user_id
        ).order_by(desc(Ticket.created_at)).limit(limit).all()

    def get_by_support_line(self, support_line: int, status: Optional[TicketStatus] = None) -> List[Ticket]:
        """Получение тикетов по линии поддержки"""
        query = self.db.query(Ticket).filter(Ticket.support_line == support_line)
        
        if status:
            query = query.filter(Ticket.status == status.value)
        
        # Сортировка по приоритету
        priority_order = {
            'критическая': 1,
            'высокая': 2,
            'средняя': 3,
            'низкая': 4
        }
        
        return query.order_by(
            func.array_position(
                list(priority_order.keys()),
                Ticket.priority
            ),
            Ticket.created_at
        ).all()

    def update(self, ticket: TicketModel) -> Ticket:
        """Обновление тикета"""
        db_ticket = self.get_by_id(ticket.id)
        if not db_ticket:
            raise ValueError(f"Ticket {ticket.id} not found")

        db_ticket.title = ticket.title
        db_ticket.description = ticket.description
        db_ticket.theme = ticket.classification.theme
        db_ticket.ticket_type = ticket.classification.ticket_type.value
        db_ticket.priority = ticket.classification.priority.value
        db_ticket.system_service = ticket.classification.system_service
        db_ticket.reasoning = ticket.classification.reasoning
        db_ticket.support_line = ticket.support_line
        db_ticket.status = ticket.status.value
        db_ticket.updated_at = datetime.utcnow()
        db_ticket.rag_answer = ticket.rag_answer
        db_ticket.conversation_history = ticket.conversation_history
        db_ticket.resolved = ticket.resolved
        db_ticket.resolution = ticket.resolution
        db_ticket.resolved_at = ticket.resolved_at
        db_ticket.tags = ticket.tags
        db_ticket.assigned_to = ticket.assigned_to
        db_ticket.escalation_reason = ticket.escalation_reason
        db_ticket.user_satisfaction = ticket.user_satisfaction

        self.db.commit()
        self.db.refresh(db_ticket)
        return db_ticket

    def get_queue_stats(self) -> Dict:
        """Получение статистики очередей"""
        stats = {}
        for line in [1, 2, 3]:
            pending = self.db.query(func.count(Ticket.id)).filter(
                and_(
                    Ticket.support_line == line,
                    Ticket.status.in_(['Новое', 'В работе'])
                )
            ).scalar()
            stats[f'line_{line}_pending'] = pending or 0
        return stats

    def _generate_ticket_number(self) -> str:
        """Генерация номера тикета"""
        last_ticket = self.db.query(Ticket).order_by(desc(Ticket.id)).first()
        if last_ticket:
            last_id = last_ticket.id
        else:
            last_id = 0
        return f"#{last_id + 1:06d}"

    def to_ticket_model(self, db_ticket: Ticket) -> TicketModel:
        """Преобразование DB модели в доменную модель"""
        return TicketModel(
            id=db_ticket.id,
            ticket_number=db_ticket.ticket_number,
            user_id=db_ticket.user_id,
            username=db_ticket.username or "",
            title=db_ticket.title,
            description=db_ticket.description,
            classification=TicketClassification(
                theme=db_ticket.theme,
                ticket_type=TicketType(db_ticket.ticket_type),
                priority=TicketPriority(db_ticket.priority),
                system_service=db_ticket.system_service,
                reasoning=db_ticket.reasoning or ""
            ),
            support_line=db_ticket.support_line,
            status=TicketStatus(db_ticket.status),
            created_at=db_ticket.created_at,
            updated_at=db_ticket.updated_at,
            rag_answer=db_ticket.rag_answer,
            conversation_history=db_ticket.conversation_history,
            resolved=db_ticket.resolved,
            resolution=db_ticket.resolution,
            resolved_at=db_ticket.resolved_at,
            tags=db_ticket.tags,
            assigned_to=db_ticket.assigned_to,
            escalation_reason=db_ticket.escalation_reason,
            user_satisfaction=db_ticket.user_satisfaction
        )
