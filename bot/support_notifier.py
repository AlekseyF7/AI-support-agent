"""
Система уведомления специалистов о новых тикетах и обработки ответов
"""
import os
import json
from typing import Dict, Optional, Union
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from dotenv import load_dotenv

from .ticket_models import Ticket, TicketPriority, TicketType, TicketStatus

load_dotenv()


class SupportNotifier:
    """Класс для отправки тикетов специалистам и обработки их ответов"""
    
    # Маппинг линий поддержки на группы
    LINE_GROUPS = {
        1: os.getenv("SUPPORT_LINE_1_CHAT_ID"),  # Service Desk
        2: os.getenv("SUPPORT_LINE_2_CHAT_ID"),  # Technical Support
        3: os.getenv("SUPPORT_LINE_3_CHAT_ID"),  # Expert Support
    }
    
    # Общая группа для всех тикетов (если линейные группы не настроены)
    DEFAULT_SUPPORT_CHAT = os.getenv("SUPPORT_CHAT_ID")
    
    # Хранение связи: message_id в группе -> данные тикета
    # В продакшене лучше хранить в БД
    ticket_messages: Dict[int, Dict] = {}
    
    def __init__(self):
        self.tickets_mapping_file = "data/ticket_messages.json"
        self._load_mappings()
    
    def _load_mappings(self):
        """Загрузка маппинга сообщений к тикетам"""
        try:
            if os.path.exists(self.tickets_mapping_file):
                with open(self.tickets_mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем ключи в int
                    self.ticket_messages = {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"Ошибка загрузки маппинга тикетов: {e}")
            self.ticket_messages = {}
    
    def _save_mappings(self):
        """Сохранение маппинга сообщений к тикетам"""
        try:
            os.makedirs(os.path.dirname(self.tickets_mapping_file), exist_ok=True)
            with open(self.tickets_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.ticket_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения маппинга тикетов: {e}")
    
    def get_support_chat_id(self, support_line: int) -> Optional[str]:
        """Получить ID чата для линии поддержки"""
        # Сначала пробуем специфичную группу для линии
        chat_id = self.LINE_GROUPS.get(support_line)
        if chat_id:
            return chat_id
        # Если нет - используем общую группу
        return self.DEFAULT_SUPPORT_CHAT
    
    def format_ticket_for_support(self, ticket: Union[Ticket, Dict]) -> str:
        """Форматирование тикета для отправки специалистам"""
        # Поддержка как Ticket объекта, так и Dict для обратной совместимости
        if isinstance(ticket, Ticket):
            ticket_dict = ticket.to_dict()
            priority_code = {
                TicketPriority.CRITICAL: "P1",
                TicketPriority.HIGH: "P2",
                TicketPriority.MEDIUM: "P3",
                TicketPriority.LOW: "P4"
            }.get(ticket.classification.priority, "P3")
            ticket_type_str = ticket.classification.ticket_type.value
            theme = ticket.classification.theme
            priority_name = {
                TicketPriority.CRITICAL: "Критическая",
                TicketPriority.HIGH: "Высокая",
                TicketPriority.MEDIUM: "Средняя",
                TicketPriority.LOW: "Низкая"
            }.get(ticket.classification.priority, "Средняя")
            created_at_str = ticket.created_at.strftime('%d.%m.%Y %H:%M')
        else:
            ticket_dict = ticket
            priority_code = ticket.get('priority', 'P3')
            ticket_type_str = ticket.get('ticket_type', 'консультация')
            theme = ticket.get('theme', 'Неизвестно')
            priority_name = ticket.get('priority_name', 'Средняя')
            created_at_str = datetime.fromisoformat(ticket['created_at']).strftime('%d.%m.%Y %H:%M')
        
        line_names = {
            1: "1-я линия (Service Desk)",
            2: "2-я линия (Technical Support)", 
            3: "3-я линия (Expert Support)"
        }
        
        priority_emoji = {
            "P1": "🔴",
            "P2": "🟠",
            "P3": "🟡",
            "P4": "🟢"
        }
        
        emoji = priority_emoji.get(priority_code, "⚪")
        
        message = f"""{emoji} НОВОЕ ОБРАЩЕНИЕ {emoji}

📋 Номер: {ticket_dict.get('ticket_number', 'N/A')}
👤 Пользователь: @{ticket_dict.get('username', 'Неизвестно')} (ID: {ticket_dict.get('user_id', 'N/A')})
📌 Тематика: {theme}
📝 Тип: {ticket_type_str}
⚡ Критичность: {priority_name} ({priority_code})
👥 Линия: {line_names.get(ticket_dict.get('support_line', 1), 'Неизвестно')}
🕐 Создано: {created_at_str}

💬 ОПИСАНИЕ ПРОБЛЕМЫ:
{ticket_dict.get('description', 'Нет описания')}"""

        # Добавляем ответ из базы знаний если есть
        rag_answer = ticket_dict.get('rag_answer') or (ticket.rag_answer if isinstance(ticket, Ticket) else None)
        if rag_answer:
            message += f"\n\n📚 ОТВЕТ ИЗ БАЗЫ ЗНАНИЙ:\n{rag_answer[:500]}{'...' if len(rag_answer) > 500 else ''}"
        
        # Добавляем историю диалога если есть
        conversation_history = ticket_dict.get('conversation_history') or (ticket.conversation_history if isinstance(ticket, Ticket) else None)
        if conversation_history:
            history = conversation_history[-5:]  # Последние 5 сообщений
            if history:
                message += f"\n\n📜 ИСТОРИЯ ДИАЛОГА:\n"
                for msg in history:
                    msg_str = msg if isinstance(msg, str) else str(msg)
                    message += f"  • {msg_str[:100]}{'...' if len(msg_str) > 100 else ''}\n"
        
        message += "\n\n💡 Чтобы ответить пользователю, просто ответьте (Reply) на это сообщение."
        
        return message
    
    def get_ticket_keyboard(self, ticket_id: int) -> InlineKeyboardMarkup:
        """Создание клавиатуры для управления тикетом"""
        keyboard = [
            [
                InlineKeyboardButton("✅ В работу", callback_data=f"ticket_inprogress_{ticket_id}"),
                InlineKeyboardButton("⏳ Ожидание", callback_data=f"ticket_waiting_{ticket_id}"),
            ],
            [
                InlineKeyboardButton("✔️ Решено", callback_data=f"ticket_resolved_{ticket_id}"),
                InlineKeyboardButton("❌ Закрыть", callback_data=f"ticket_closed_{ticket_id}"),
            ],
            [
                InlineKeyboardButton("⬆️ Эскалация", callback_data=f"ticket_escalate_{ticket_id}"),
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def notify_support(self, bot, ticket: Union[Ticket, Dict]) -> Optional[int]:
        """
        Отправка уведомления о новом тикете в группу поддержки
        
        Args:
            bot: Экземпляр бота Telegram
            ticket: Данные тикета (Ticket объект или Dict)
            
        Returns:
            message_id отправленного сообщения или None
        """
        # Поддержка как Ticket объекта, так и Dict
        if isinstance(ticket, Ticket):
            support_line = ticket.support_line
            ticket_id = ticket.id
            ticket_number = ticket.ticket_number
            user_id = ticket.user_id
        else:
            support_line = ticket['support_line']
            ticket_id = ticket['id']
            ticket_number = ticket['ticket_number']
            user_id = ticket['user_id']
        
        support_chat_id = self.get_support_chat_id(support_line)
        
        if not support_chat_id:
            print(f"[WARNING] Не настроен чат поддержки для линии {support_line}")
            print("[INFO] Добавьте SUPPORT_CHAT_ID в .env файл")
            return None
        
        try:
            message_text = self.format_ticket_for_support(ticket)
            keyboard = self.get_ticket_keyboard(ticket_id)
            
            sent_message = await bot.send_message(
                chat_id=support_chat_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode=None  # Без форматирования для надежности
            )
            
            # Сохраняем связь message_id -> ticket
            self.ticket_messages[sent_message.message_id] = {
                "ticket_id": ticket_id,
                "ticket_number": ticket_number,
                "user_id": user_id,
                "support_chat_id": support_chat_id,
                "created_at": datetime.now().isoformat()
            }
            self._save_mappings()
            
            print(f"[INFO] Тикет {ticket_number} отправлен в группу поддержки")
            return sent_message.message_id
            
        except Exception as e:
            print(f"[ERROR] Ошибка отправки тикета в группу поддержки: {e}")
            return None
    
    async def handle_support_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Обработка ответа специалиста на тикет
        
        Args:
            update: Update от Telegram
            context: Контекст
            
        Returns:
            True если это был ответ на тикет, False иначе
        """
        message = update.message
        
        # Проверяем, что это ответ на сообщение
        if not message.reply_to_message:
            return False
        
        reply_to_id = message.reply_to_message.message_id
        
        # Проверяем, есть ли это сообщение в наших тикетах
        if reply_to_id not in self.ticket_messages:
            return False
        
        ticket_data = self.ticket_messages[reply_to_id]
        user_id = ticket_data['user_id']
        ticket_number = ticket_data['ticket_number']
        
        # Получаем информацию о специалисте
        support_user = update.effective_user
        support_name = support_user.username or support_user.first_name or "Специалист"
        
        # Формируем ответ для пользователя
        response_to_user = f"""📩 Ответ на ваше обращение {ticket_number}

👤 От специалиста: @{support_name}

💬 Сообщение:
{message.text}

---
Если у вас остались вопросы, просто напишите в этот чат."""

        try:
            # Отправляем ответ пользователю
            await context.bot.send_message(
                chat_id=user_id,
                text=response_to_user
            )
            
            # Подтверждаем специалисту
            await message.reply_text(
                f"✅ Ответ отправлен пользователю (тикет {ticket_number})"
            )
            
            print(f"[INFO] Ответ на тикет {ticket_number} отправлен пользователю {user_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка отправки ответа пользователю: {e}")
            await message.reply_text(
                f"❌ Не удалось отправить ответ пользователю. Ошибка: {str(e)[:100]}"
            )
            return False
    
    async def handle_ticket_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Обработка нажатий кнопок управления тикетом
        
        Args:
            update: Update от Telegram
            context: Контекст
            
        Returns:
            True если callback обработан
        """
        query = update.callback_query
        data = query.data
        
        if not data.startswith("ticket_"):
            return False
        
        await query.answer()
        
        parts = data.split("_")
        if len(parts) < 3:
            return False
        
        action = parts[1]
        ticket_id = int(parts[2])
        
        support_user = update.effective_user
        support_name = support_user.username or support_user.first_name or "Специалист"
        
        # Маппинг действий на статусы
        action_to_status = {
            "inprogress": TicketStatus.IN_PROGRESS,
            "waiting": TicketStatus.WAITING_FOR_USER,
            "resolved": TicketStatus.RESOLVED,
            "closed": TicketStatus.CLOSED,
            "escalate": TicketStatus.ESCALATED,
        }
        
        # Обновляем тикет в БД если возможно
        try:
            from .ticket_database import TicketDatabase
            db = TicketDatabase()
            ticket = db.get_ticket(ticket_id)
            
            if ticket:
                if action in action_to_status:
                    new_status = action_to_status[action]
                    resolution = None
                    
                    if action == "resolved":
                        resolution = f"Решено специалистом @{support_name}"
                    
                    # Обновляем статус в БД
                    ticket.status = new_status
                    ticket.updated_at = datetime.now()
                    ticket.assigned_to = support_name
                    
                    if action == "resolved":
                        ticket.resolved = True
                        ticket.resolution = resolution
                        ticket.resolved_at = datetime.now()
                    elif action == "escalate":
                        # Эскалация на следующую линию
                        if ticket.support_line < 3:
                            ticket.support_line += 1
                            ticket.escalation_reason = f"Эскалировано специалистом @{support_name}"
                    
                    db.update_ticket(ticket)
        except Exception as e:
            print(f"[WARNING] Не удалось обновить тикет в БД: {e}")
        
        status_messages = {
            "inprogress": f"🔄 Тикет #{ticket_id:03d} взят в работу специалистом @{support_name}",
            "waiting": f"⏳ Тикет #{ticket_id:03d} ожидает ответа пользователя",
            "resolved": f"✅ Тикет #{ticket_id:03d} решен специалистом @{support_name}",
            "closed": f"❌ Тикет #{ticket_id:03d} закрыт",
            "escalate": f"⬆️ Тикет #{ticket_id:03d} эскалирован на следующую линию",
        }
        
        status_message = status_messages.get(action, f"Статус тикета #{ticket_id:03d} изменен")
        
        # Обновляем сообщение
        try:
            # Добавляем статус к сообщению
            original_text = query.message.text
            new_text = f"{original_text}\n\n---\n{status_message}"
            
            # Если тикет закрыт или решен - убираем кнопки
            if action in ["resolved", "closed"]:
                await query.edit_message_text(text=new_text)
            else:
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=self.get_ticket_keyboard(ticket_id)
                )
            
            # Уведомляем пользователя об изменении статуса
            # Находим user_id по ticket_id
            for msg_id, ticket_data in self.ticket_messages.items():
                if ticket_data['ticket_id'] == ticket_id:
                    user_id = ticket_data['user_id']
                    ticket_number = ticket_data['ticket_number']
                    
                    user_notification = {
                        "inprogress": f"🔄 Ваше обращение {ticket_number} взято в работу специалистом.",
                        "waiting": f"⏳ Ожидаем вашего ответа по обращению {ticket_number}.",
                        "resolved": f"✅ Ваше обращение {ticket_number} решено! Если у вас остались вопросы, создайте новое обращение.",
                        "closed": f"❌ Ваше обращение {ticket_number} закрыто.",
                        "escalate": f"⬆️ Ваше обращение {ticket_number} передано старшему специалисту.",
                    }
                    
                    if action in user_notification:
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=user_notification[action]
                            )
                        except Exception as e:
                            print(f"[WARNING] Не удалось уведомить пользователя: {e}")
                    break
            
        except Exception as e:
            print(f"[ERROR] Ошибка обновления статуса тикета: {e}")
        
        return True


# Глобальный экземпляр для использования в боте
support_notifier = SupportNotifier()

