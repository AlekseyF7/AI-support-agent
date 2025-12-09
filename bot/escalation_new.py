"""
Система эскалации обращений (PB5, PB6) - обновленная версия
"""
from typing import Dict, Optional, List
from datetime import datetime

from .ticket_models import Ticket, TicketClassification, TicketType, TicketPriority, TicketStatus
from .ticket_database import TicketDatabase


class EscalationSystem:
    """Система создания и управления обращениями (PB6)"""
    
    # Правила определения линии поддержки на основе приоритета
    PRIORITY_TO_LINE = {
        TicketPriority.CRITICAL: 3,  # Критическая -> 3-я линия
        TicketPriority.HIGH: 2,      # Высокая -> 2-я линия
        TicketPriority.MEDIUM: 1,    # Средняя -> 1-я линия
        TicketPriority.LOW: 1,       # Низкая -> 1-я линия
    }
    
    # Тематики, требующие автоматической эскалации на 2-ю линию
    AUTO_ESCALATE_THEMES_2 = [
        "Системная проблема",
        "Конфигурация",
        "Сетевая проблема",
    ]
    
    # Тематики, требующие автоматической эскалации на 3-ю линию
    AUTO_ESCALATE_THEMES_3 = [
        "Критическая системная проблема",
    ]
    
    def __init__(self, db_path: str = "data/tickets.db"):
        """Инициализация системы эскалации с БД"""
        self.db = TicketDatabase(db_path)
    
    def determine_support_line(self, classification: TicketClassification, is_faq: bool = False, 
                             conversation_history: Optional[List[str]] = None) -> int:
        """
        Определяет линию поддержки на основе классификации (PB6)
        
        Args:
            classification: Классификация обращения
            is_faq: Является ли это FAQ вопросом
            conversation_history: История диалога для анализа
            
        Returns:
            Номер линии поддержки (1, 2 или 3)
        """
        # FAQ вопросы всегда на 1-й линии
        if is_faq:
            return 1
        
        # Критические проблемы -> 3-я линия
        if classification.priority == TicketPriority.CRITICAL:
            return 3
        
        # Автоматическая эскалация по тематике
        if classification.theme in self.AUTO_ESCALATE_THEMES_3:
            return 3
        
        if classification.theme in self.AUTO_ESCALATE_THEMES_2:
            return 2
        
        # Определение по приоритету
        return self.PRIORITY_TO_LINE.get(classification.priority, 1)
    
    def create_ticket(self, 
                     user_id: int,
                     username: str,
                     description: str,
                     classification: TicketClassification,
                     support_line: int,
                     rag_answer: Optional[str] = None,
                     conversation_history: Optional[List[str]] = None) -> Ticket:
        """
        Создает новое обращение (PB6)
        
        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя
            description: Описание проблемы
            classification: Классификация обращения
            support_line: Линия поддержки
            rag_answer: Ответ из RAG (если был)
            conversation_history: История диалога
            
        Returns:
            Созданный тикет
        """
        # Генерируем заголовок из описания
        title = description[:100] if len(description) > 100 else description
        
        # Форматируем историю диалога
        if conversation_history:
            formatted_history = [
                f"Пользователь: {msg}" if i % 2 == 0 else f"Бот: {msg}"
                for i, msg in enumerate(conversation_history)
            ]
        else:
            formatted_history = []
        
        ticket = Ticket(
            id=0,  # Будет установлен БД
            ticket_number="",  # Будет сгенерирован БД
            user_id=user_id,
            username=username,
            title=title,
            description=description,
            classification=classification,
            support_line=support_line,
            status=TicketStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            rag_answer=rag_answer,
            conversation_history=formatted_history
        )
        
        # Сохраняем в БД
        ticket = self.db.create_ticket(ticket)
        
        return ticket
    
    def escalate_ticket(self, ticket: Ticket, new_line: int, reason: str) -> Ticket:
        """
        Эскалирует тикет на другую линию поддержки
        
        Args:
            ticket: Тикет для эскалации
            new_line: Новая линия поддержки
            reason: Причина эскалации
            
        Returns:
            Обновленный тикет
        """
        ticket.support_line = new_line
        ticket.status = TicketStatus.ESCALATED
        ticket.escalation_reason = reason
        ticket.updated_at = datetime.now()
        
        return self.db.update_ticket(ticket)
    
    def update_ticket_status(self, ticket: Ticket, status: TicketStatus, 
                           resolution: Optional[str] = None) -> Ticket:
        """
        Обновляет статус тикета
        
        Args:
            ticket: Тикет
            status: Новый статус
            resolution: Решение (если статус = RESOLVED)
            
        Returns:
            Обновленный тикет
        """
        ticket.status = status
        ticket.updated_at = datetime.now()
        
        if status == TicketStatus.RESOLVED:
            ticket.resolved = True
            ticket.resolution = resolution
            ticket.resolved_at = datetime.now()
        
        return self.db.update_ticket(ticket)
    
    def get_tickets_by_line(self, support_line: int, status: Optional[TicketStatus] = None) -> List[Ticket]:
        """Получить тикеты по линии поддержки (очередь)"""
        return self.db.get_tickets_by_line(support_line, status)
    
    def format_ticket_message(self, ticket: Ticket) -> str:
        """
        Форматирует сообщение о созданном тикете
        
        Args:
            ticket: Тикет
            
        Returns:
            Отформатированное сообщение
        """
        line_names = {
            1: "1-я линия (Service Desk)",
            2: "2-я линия (Technical Support)",
            3: "3-я линия (Expert Support)"
        }
        
        type_names = {
            TicketType.CONSULTATION: "Консультация",
            TicketType.INCIDENT: "Инцидент"
        }
        
        priority_names = {
            TicketPriority.CRITICAL: "Критическая",
            TicketPriority.HIGH: "Высокая",
            TicketPriority.MEDIUM: "Средняя",
            TicketPriority.LOW: "Низкая"
        }
        
        message = f"""✅ Обращение создано!

📋 Номер: {ticket.ticket_number}
📌 Тематика: {ticket.classification.theme}
🔖 Тип: {type_names.get(ticket.classification.ticket_type, 'Неизвестно')}
⚡ Критичность: {priority_names.get(ticket.classification.priority, 'Неизвестно')}
👥 Линия поддержки: {line_names.get(ticket.support_line, 'Неизвестно')}"""
        
        if ticket.classification.system_service:
            message += f"\n🖥️ Система/Сервис: {ticket.classification.system_service}"
        
        message += f"""
📝 Описание: {ticket.description[:200]}{'...' if len(ticket.description) > 200 else ''}
🕐 Создано: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}

Обращение передано специалистам. Вы получите уведомление при обновлении статуса."""
        
        return message

