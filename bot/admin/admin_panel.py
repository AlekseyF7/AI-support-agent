"""
Простая админ-панель для управления тикетами через Telegram
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError

from ..database.database_factory import get_database
from ..ticket_models import TicketStatus, TicketPriority
from ..utils.logger import get_logger
from ..utils.metrics import get_metrics

logger = get_logger(__name__)
metrics = get_metrics()


class AdminPanel:
    """Админ-панель для управления тикетами"""
    
    def __init__(self, bot_token: str, admin_user_ids: List[int]):
        """
        Инициализация админ-панели
        
        Args:
            bot_token: Токен бота
            admin_user_ids: Список ID администраторов
        """
        self.bot_token = bot_token
        self.admin_user_ids = admin_user_ids
        self.db = get_database()
        self.application = None
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in self.admin_user_ids
    
    def setup_handlers(self, application: Application):
        """Настройка обработчиков команд для админ-панели"""
        self.application = application
        
        # Команды админ-панели
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("tickets", self.tickets_command))
        application.add_handler(CallbackQueryHandler(self.handle_admin_callback))
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin - главное меню админ-панели"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав доступа к админ-панели.")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🎫 Тикеты (Линия 1)", callback_data="admin_tickets_1")],
            [InlineKeyboardButton("🎫 Тикеты (Линия 2)", callback_data="admin_tickets_2")],
            [InlineKeyboardButton("🎫 Тикеты (Линия 3)", callback_data="admin_tickets_3")],
            [InlineKeyboardButton("📈 Метрики", callback_data="admin_metrics")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 Админ-панель\n\nВыберите действие:",
            reply_markup=reply_markup
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика тикетов"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав доступа.")
            return
        
        stats = self.db.get_queue_stats()
        metrics_stats = metrics.get_stats()
        
        message = "📊 Статистика тикетов:\n\n"
        message += f"Линия 1 (ожидает): {stats.get('line_1_pending', 0)}\n"
        message += f"Линия 2 (ожидает): {stats.get('line_2_pending', 0)}\n"
        message += f"Линия 3 (ожидает): {stats.get('line_3_pending', 0)}\n\n"
        message += "📈 Метрики:\n"
        message += f"Всего сообщений: {metrics_stats.get('counters', {}).get('messages_total', 0)}\n"
        message += f"Всего тикетов создано: {metrics_stats.get('counters', {}).get('tickets_created', 0)}\n"
        message += f"RAG запросов: {metrics_stats.get('counters', {}).get('rag_queries_total', 0)}\n"
        message += f"Классификаций: {metrics_stats.get('counters', {}).get('classifications_total', 0)}\n"
        
        await update.message.reply_text(message)
    
    async def tickets_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /tickets - список тикетов"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав доступа.")
            return
        
        # Получаем линию из аргументов или показываем меню
        if context.args:
            try:
                line = int(context.args[0])
                await self._show_tickets(update, line)
            except ValueError:
                await update.message.reply_text("Использование: /tickets <номер_линии>")
        else:
            keyboard = [
                [InlineKeyboardButton("Линия 1", callback_data="admin_tickets_1")],
                [InlineKeyboardButton("Линия 2", callback_data="admin_tickets_2")],
                [InlineKeyboardButton("Линия 3", callback_data="admin_tickets_3")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Выберите линию поддержки:",
                reply_markup=reply_markup
            )
    
    async def _show_tickets(self, update: Update, line: int, status: Optional[TicketStatus] = None):
        """Показать тикеты линии"""
        tickets = self.db.get_tickets_by_line(line, status=status)
        
        if not tickets:
            await update.message.reply_text(f"Нет тикетов на линии {line}.")
            return
        
        message = f"🎫 Тикеты линии {line}:\n\n"
        
        for ticket in tickets[:10]:  # Показываем первые 10
            status_emoji = {
                TicketStatus.NEW: "🆕",
                TicketStatus.IN_PROGRESS: "🔄",
                TicketStatus.RESOLVED: "✅",
                TicketStatus.CLOSED: "🔒",
            }.get(ticket.status, "📝")
            
            priority_emoji = {
                TicketPriority.CRITICAL: "🔴",
                TicketPriority.HIGH: "🟠",
                TicketPriority.MEDIUM: "🟡",
                TicketPriority.LOW: "🟢",
            }.get(ticket.classification.priority, "⚪")
            
            message += f"{status_emoji} {priority_emoji} {ticket.ticket_number}\n"
            message += f"   {ticket.title[:50]}...\n"
            message += f"   Приоритет: {ticket.classification.priority.value}\n"
            message += f"   Статус: {ticket.status.value}\n\n"
        
        if len(tickets) > 10:
            message += f"... и еще {len(tickets) - 10} тикетов"
        
        await update.message.reply_text(message)
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback от inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if not self.is_admin(user_id):
            await query.edit_message_text("❌ У вас нет прав доступа.")
            return
        
        data = query.data
        
        if data == "admin_stats":
            stats = self.db.get_queue_stats()
            metrics_stats = metrics.get_stats()
            
            message = "📊 Статистика:\n\n"
            message += f"Линия 1: {stats.get('line_1_pending', 0)}\n"
            message += f"Линия 2: {stats.get('line_2_pending', 0)}\n"
            message += f"Линия 3: {stats.get('line_3_pending', 0)}\n\n"
            message += f"Всего сообщений: {metrics_stats.get('counters', {}).get('messages_total', 0)}\n"
            
            await query.edit_message_text(message)
        
        elif data.startswith("admin_tickets_"):
            line = int(data.split("_")[-1])
            await self._show_tickets(query, line)
        
        elif data == "admin_metrics":
            stats = metrics.get_stats()
            message = "📈 Метрики производительности:\n\n"
            
            if stats.get('averages'):
                message += "Средние времена:\n"
                for metric, avg in stats['averages'].items():
                    if avg:
                        message += f"  {metric}: {avg:.2f}с\n"
            
            await query.edit_message_text(message)
