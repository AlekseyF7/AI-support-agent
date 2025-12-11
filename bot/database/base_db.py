"""
Базовый класс для работы с базами данных тикетов
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime

from ..ticket_models import Ticket, TicketStatus


class TicketDatabase(ABC):
    """Абстрактный базовый класс для работы с БД тикетов"""
    
    @abstractmethod
    def create_ticket(self, ticket: Ticket) -> Ticket:
        """Создать новый тикет"""
        pass
    
    @abstractmethod
    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        """Получить тикет по ID"""
        pass
    
    @abstractmethod
    def get_tickets_by_user(self, user_id: int, limit: int = 10) -> List[Ticket]:
        """Получить тикеты пользователя"""
        pass
    
    @abstractmethod
    def get_tickets_by_line(self, support_line: int, status: Optional[TicketStatus] = None) -> List[Ticket]:
        """Получить тикеты по линии поддержки"""
        pass
    
    @abstractmethod
    def update_ticket(self, ticket: Ticket) -> Ticket:
        """Обновить тикет"""
        pass
    
    @abstractmethod
    def get_queue_stats(self) -> Dict:
        """Получить статистику очередей"""
        pass
