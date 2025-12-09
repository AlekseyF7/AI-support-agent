"""
Система эскалации обращений (PB5, PB6)
"""
from typing import Dict, Optional, List, Union
from datetime import datetime
import json
import os

from .ticket_models import Ticket, TicketClassification, TicketType, TicketPriority, TicketStatus


class EscalationSystem:
    """Система создания и управления обращениями"""
    
    # Правила определения линии поддержки
    LINE_RULES = {
        "критическая": 3,  # Критическая -> 3-я линия
        "высокая": 2,      # Высокая -> 2-я линия
        "средняя": 1,      # Средняя -> 1-я линия
        "низкая": 1,       # Низкая -> 1-я линия
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
    
    def __init__(self, tickets_file: str = "data/tickets.json"):
        self.tickets_file = tickets_file
        self.ticket_counter = 0
        # Создаем директорию если нужно
        os.makedirs(os.path.dirname(self.tickets_file), exist_ok=True)
        self._load_tickets()
    
    def _load_tickets(self):
        """Загрузка существующих тикетов"""
        if os.path.exists(self.tickets_file):
            try:
                with open(self.tickets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tickets = data.get("tickets", [])
                    if tickets:
                        self.ticket_counter = max([t.get("id", 0) for t in tickets])
            except Exception as e:
                print(f"Ошибка загрузки тикетов: {e}")
        else:
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(self.tickets_file), exist_ok=True)
    
    def _save_ticket(self, ticket: Dict):
        """Сохранение тикета в файл"""
        try:
            if os.path.exists(self.tickets_file):
                with open(self.tickets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"tickets": []}
            
            data["tickets"].append(ticket)
            
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения тикета: {e}")
    
    def _get_priority_str(self, priority: Union[TicketPriority, str]) -> str:
        """Получить строковое значение приоритета"""
        if isinstance(priority, TicketPriority):
            return priority.value
        return str(priority)
    
    def _get_priority_code(self, priority: Union[TicketPriority, str]) -> str:
        """Получить код приоритета (P1-P4)"""
        priority_str = self._get_priority_str(priority)
        code_map = {
            "критическая": "P1",
            "высокая": "P2",
            "средняя": "P3",
            "низкая": "P4",
        }
        return code_map.get(priority_str, "P3")
    
    def determine_support_line(self, theme: str, priority: Union[TicketPriority, str], is_faq: bool = False) -> int:
        """
        Определяет линию поддержки на основе тематики и приоритета
        
        Args:
            theme: Тематика обращения
            priority: Приоритет (TicketPriority или строка)
            is_faq: Является ли это FAQ вопросом
            
        Returns:
            Номер линии поддержки (1, 2 или 3)
        """
        # FAQ вопросы всегда на 1-й линии
        if is_faq:
            return 1
        
        # Получаем строковое значение приоритета
        priority_str = self._get_priority_str(priority)
        
        # Критические проблемы -> 3-я линия
        if priority_str == "критическая":
            return 3
        
        # Автоматическая эскалация по тематике
        if theme in self.AUTO_ESCALATE_THEMES_3:
            return 3
        
        if theme in self.AUTO_ESCALATE_THEMES_2:
            return 2
        
        # Определение по приоритету
        return self.LINE_RULES.get(priority_str, 1)
    
    def create_ticket(self, 
                     user_id: int,
                     username: str,
                     description: str,
                     theme: str,
                     priority: Union[TicketPriority, str],
                     ticket_type: Union[TicketType, str] = None,
                     support_line: int = None,
                     rag_answer: Optional[str] = None,
                     conversation_history: Optional[list] = None) -> Dict:
        """
        Создает новое обращение
        
        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя
            description: Описание проблемы
            theme: Тематика
            priority: Приоритет (TicketPriority или строка)
            ticket_type: Тип обращения (TicketType или строка)
            support_line: Линия поддержки
            rag_answer: Ответ из RAG (если был)
            conversation_history: История диалога
            
        Returns:
            dict с информацией о созданном тикете
        """
        self.ticket_counter += 1
        ticket_id = self.ticket_counter
        
        # Получаем строковые значения
        priority_str = self._get_priority_str(priority)
        priority_code = self._get_priority_code(priority)
        
        # Получаем тип обращения
        if isinstance(ticket_type, TicketType):
            ticket_type_str = ticket_type.value
        elif ticket_type:
            ticket_type_str = str(ticket_type)
        else:
            ticket_type_str = "консультация"
        
        # Определяем линию поддержки если не задана
        if support_line is None:
            support_line = self.determine_support_line(theme, priority)
        
        ticket = {
            "id": ticket_id,
            "ticket_number": f"#{ticket_id:03d}",
            "user_id": user_id,
            "username": username,
            "description": description,
            "theme": theme,
            "ticket_type": ticket_type_str,
            "priority": priority_code,
            "priority_name": priority_str.capitalize(),
            "support_line": support_line,
            "status": "Новое",
            "created_at": datetime.now().isoformat(),
            "rag_answer": rag_answer,
            "conversation_history": conversation_history or [],
            "resolved": False,
            "resolution": None,
            "resolved_at": None
        }
        
        self._save_ticket(ticket)
        
        return ticket
    
    def format_ticket_message(self, ticket: Dict) -> str:
        """
        Форматирует сообщение о созданном тикете
        
        Args:
            ticket: Данные тикета
            
        Returns:
            Отформатированное сообщение
        """
        line_names = {
            1: "1-я линия (Service Desk)",
            2: "2-я линия (Technical Support)",
            3: "3-я линия (Expert Support)"
        }
        
        message = f"""Обращение создано!

Номер: {ticket['ticket_number']}
Тематика: {ticket['theme']}
Критичность: {ticket.get('priority_name', 'Средняя')} ({ticket['priority']})
Линия поддержки: {line_names.get(ticket['support_line'], 'Неизвестно')}
Описание: {ticket['description'][:200]}{'...' if len(ticket['description']) > 200 else ''}
Создано: {datetime.fromisoformat(ticket['created_at']).strftime('%d.%m.%Y %H:%M')}

Обращение передано специалистам. Вы получите уведомление при обновлении статуса."""
        
        return message
