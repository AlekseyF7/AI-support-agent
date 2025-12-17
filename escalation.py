"""Система маршрутизации и эскалации обращений"""
import logging
from models import Ticket, SupportLine, TicketStatus, Criticality, SessionLocal
from typing import Optional, List
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class EscalationSystem:
    """Система маршрутизации обращений по линиям поддержки"""
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Получение сессии БД (создается при необходимости)"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def create_ticket(
        self,
        title: str,
        description: str,
        user_id: int,
        user_name: str,
        category,
        criticality,
        support_line,
        conversation_history: list = None
    ) -> Ticket:
        """
        Создание нового обращения (тикета)
        
        Args:
            title: Заголовок обращения
            description: Описание проблемы
            user_id: ID пользователя Telegram
            user_name: Имя пользователя
            category: Категория обращения
            criticality: Критичность
            support_line: Линия поддержки
            conversation_history: История общения
        
        Returns:
            Созданный тикет
        """
        try:
            # Преобразуем историю в JSON строку
            history_json = ""
            if conversation_history:
                history_json = json.dumps(conversation_history, ensure_ascii=False)
            
            ticket = Ticket(
                title=title,
                description=description,
                user_id=user_id,
                user_name=user_name,
                category=category,
                criticality=criticality,
                support_line=support_line,
                status=TicketStatus.OPEN,
                conversation_history=history_json
            )
            
            self.db.add(ticket)
            self.db.commit()
            self.db.refresh(ticket)
            
            logger.info(f"Создан тикет #{ticket.id} для пользователя {user_id} ({user_name}), "
                       f"категория: {category.value}, критичность: {criticality.value}")
            
            return ticket
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка создания тикета: {e}", exc_info=True)
            raise
    
    def get_tickets_by_line(self, support_line: SupportLine, status: TicketStatus = None) -> List[Ticket]:
        """
        Получение тикетов по линии поддержки
        
        Args:
            support_line: Линия поддержки
            status: Статус (опционально)
        
        Returns:
            Список тикетов
        """
        query = self.db.query(Ticket).filter(Ticket.support_line == support_line)
        
        if status:
            query = query.filter(Ticket.status == status)
        
        return query.order_by(Ticket.created_at.desc()).all()
    
    def escalate_ticket(self, ticket_id: int, new_line: SupportLine) -> Optional[Ticket]:
        """
        Эскалация тикета на другую линию поддержки
        
        Args:
            ticket_id: ID тикета
            new_line: Новая линия поддержки
        
        Returns:
            Обновленный тикет или None
        """
        try:
            ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
            
            if not ticket:
                return None
            
            ticket.support_line = new_line
            ticket.status = TicketStatus.ESCALATED
            ticket.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(ticket)
            
            return ticket
        except Exception as e:
            self.db.rollback()
            raise
    
    def update_ticket_status(self, ticket_id: int, status: TicketStatus) -> Optional[Ticket]:
        """
        Обновление статуса тикета
        
        Args:
            ticket_id: ID тикета
            status: Новый статус
        
        Returns:
            Обновленный тикет или None
        """
        try:
            ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
            
            if not ticket:
                return None
            
            ticket.status = status
            ticket.updated_at = datetime.now(timezone.utc)
            
            if status == TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(ticket)
            
            return ticket
        except Exception as e:
            self.db.rollback()
            raise
    
    def get_user_tickets(self, user_id: int) -> List[Ticket]:
        """
        Получение всех тикетов пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список тикетов
        """
        return self.db.query(Ticket).filter(
            Ticket.user_id == user_id
        ).order_by(Ticket.created_at.desc()).all()
    
    def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """
        Получение тикета по ID
        
        Args:
            ticket_id: ID тикета
        
        Returns:
            Тикет или None
        """
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    def get_queue_stats(self) -> dict:
        """
        Получение статистики очередей
        
        Returns:
            Словарь со статистикой по линиям
        """
        stats = {}
        
        for line in SupportLine:
            total = self.db.query(Ticket).filter(
                Ticket.support_line == line,
                Ticket.status != TicketStatus.CLOSED
            ).count()
            
            open_count = self.db.query(Ticket).filter(
                Ticket.support_line == line,
                Ticket.status == TicketStatus.OPEN
            ).count()
            
            stats[line.value] = {
                "total": total,
                "open": open_count
            }
        
        return stats
    
    def close(self):
        """Закрытие сессии БД"""
        if self._db is not None:
            self._db.close()
            self._db = None
    
    def __del__(self):
        """Закрытие сессии при удалении"""
        self.close()

