"""
Модуль для работы с базой данных PostgreSQL
"""
from .connection import get_db, engine, Base
from .models import Ticket, Log
from .ticket_repository import TicketRepository
from .log_repository import LogRepository

__all__ = [
    'get_db',
    'engine',
    'Base',
    'Ticket',
    'Log',
    'TicketRepository',
    'LogRepository',
]
