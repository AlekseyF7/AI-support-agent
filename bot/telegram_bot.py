"""
Telegram бот для поддержки клиентов
"""
import os
import logging
from typing import Dict, List
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import Conflict
from dotenv import load_dotenv

from .rag_system import RAGSystem
from .classifier import TicketClassifier
from .escalation import EscalationSystem
from .question_filter import QuestionFilter
from .support_notifier import SupportNotifier

load_dotenv()

# Настройка логгера
logger = logging.getLogger(__name__)


class SupportBot:
    """Telegram бот для поддержки клиентов"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        # Инициализация компонентов
        self.rag_system = RAGSystem()
        self.classifier = TicketClassifier()
        self.escalation = EscalationSystem()
        self.support_notifier = SupportNotifier()
        
        # ID группы поддержки для проверки сообщений
        self.support_chat_id = os.getenv("SUPPORT_CHAT_ID")
        
        # История диалогов пользователей {user_id: [messages]}
        self.conversation_history: Dict[int, List[str]] = {}
        
        # Загрузка базы знаний
        print("Инициализация RAG системы...")
        self.rag_system.load_knowledge_base()
        
        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.WARNING
        )
        
        # Создание приложения
        self.application = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        self._register_handlers()
        
        # Информация о настройке
        if self.support_chat_id:
            print(f"[INFO] Группа поддержки настроена: {self.support_chat_id}")
        else:
            print("[WARNING] SUPPORT_CHAT_ID не настроен. Тикеты не будут отправляться специалистам.")
            print("[INFO] Добавьте SUPPORT_CHAT_ID в .env файл для отправки тикетов в группу.")
    
    def _register_handlers(self):
        """Регистрация обработчиков команд и сообщений"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        
        # Callback для кнопок управления тикетами
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        welcome_message = f"""Привет, {user.first_name}!

Я - бот поддержки банка, готовый помочь с вашими вопросами.

Я могу:
- Ответить на вопросы по интернет-банку и картам
- Помочь с восстановлением доступа
- Создать обращение для специалистов

Просто опишите вашу проблему или задайте вопрос!

Команды:
/help - справка
/clear - очистить историю диалога"""
        
        await update.message.reply_text(welcome_message)
        self.conversation_history[user.id] = []
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_message = """Справка по использованию бота

Как работает бот:
1. Вы описываете проблему или задаете вопрос
2. Бот ищет ответ в базе знаний
3. Если ответ найден - бот отвечает сразу
4. Если нужна помощь специалиста - создается обращение
5. Специалист получает ваш вопрос и отвечает

Примеры вопросов:
- "Как изменить пароль в интернет-банке?"
- "Не могу войти в мобильное приложение"
- "Как заблокировать карту?"
- "Не приходит SMS с кодом"

Команды:
/start - начать работу
/clear - очистить историю диалога"""
        
        await update.message.reply_text(help_message)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка истории диалога"""
        user = update.effective_user
        self.conversation_history[user.id] = []
        await update.message.reply_text("История диалога очищена")
    
    def _add_to_history(self, user_id: int, message: str, is_bot: bool = False):
        """Добавление сообщения в историю"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        prefix = "Пользователь" if not is_bot else "Бот"
        self.conversation_history[user_id].append(f"{prefix}: {message}")
        
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
    
    def _is_support_chat(self, chat_id: int) -> bool:
        """Проверка, является ли чат группой поддержки"""
        if not self.support_chat_id:
            return False
        return str(chat_id) == str(self.support_chat_id)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline кнопки"""
        await self.support_notifier.handle_ticket_callback(update, context)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        chat_id = update.effective_chat.id
        
        # Если сообщение из группы поддержки - проверяем, это ответ на тикет
        if self._is_support_chat(chat_id):
            handled = await self.support_notifier.handle_support_reply(update, context)
            if handled:
                return
            # Если не ответ на тикет - игнорируем
            return
        
        user = update.effective_user
        message_text = update.message.text
        
        # Добавляем сообщение пользователя в историю
        self._add_to_history(user.id, message_text, is_bot=False)
        
        # Показываем индикатор печати
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        try:
            # Шаг 0: Проверка релевантности вопроса
            is_relevant, reason = QuestionFilter.is_relevant(message_text)
            if not is_relevant:
                rejection_msg = QuestionFilter.get_rejection_message()
                await update.message.reply_text(rejection_msg)
                self._add_to_history(user.id, rejection_msg, is_bot=True)
                logger.info(f"Вопрос отклонен фильтром: {reason}")
                return
            
            # Шаг 1: Поиск ответа в базе знаний
            rag_result = self.rag_system.get_answer(message_text)
            answer = rag_result.get("answer", "").strip()
            
            # Проверяем качество ответа
            error_phrases = [
                "не удалось найти ответ",
                "не знаю ответа",
                "обратитесь к специалисту",
                "произошла ошибка при поиске"
            ]
            has_good_answer = answer and len(answer) > 10 and not any(phrase in answer.lower() for phrase in error_phrases)
            
            print(f"[DEBUG] RAG Answer: {answer[:100] if answer else 'None'}...")
            print(f"[DEBUG] Has good answer: {has_good_answer}")
            
            is_faq = self.rag_system.is_faq_question(message_text, answer) if answer else False
            
            # Шаг 2: Классификация
            history = self.conversation_history.get(user.id, [])
            classification = self.classifier.classify(message_text, history)
            
            priority_str = classification.priority.value if hasattr(classification.priority, 'value') else str(classification.priority)
            
            # Шаг 3: Определение необходимости эскалации
            high_priority = priority_str in ["критическая", "высокая", "P1", "P2"]
            low_priority = priority_str in ["средняя", "низкая", "P3", "P4"]
            
            if has_good_answer and is_faq and low_priority:
                # Простой FAQ вопрос - отвечаем без создания тикета
                response = f"💡 {answer}"
                if rag_result.get("sources"):
                    response += f"\n\n📚 Источники: {len(rag_result['sources'])} документов"
                
                await update.message.reply_text(response)
                self._add_to_history(user.id, response, is_bot=True)
            
            else:
                # Требуется создание обращения
                support_line = self.escalation.determine_support_line(
                    classification.theme,
                    classification.priority,
                    is_faq=is_faq
                )
                
                # Создаем тикет
                ticket = self.escalation.create_ticket(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    description=message_text,
                    theme=classification.theme,
                    priority=classification.priority,
                    ticket_type=classification.ticket_type,
                    support_line=support_line,
                    rag_answer=answer if answer else None,
                    conversation_history=history
                )
                
                # Отправляем тикет специалистам
                await self.support_notifier.notify_support(context.bot, ticket)
                
                # Формируем ответ пользователю
                response_parts = []
                
                if answer and len(answer.strip()) > 5:
                    response_parts.append(f"💡 Ответ из базы знаний:\n{answer}")
                    if rag_result.get("sources"):
                        response_parts.append(f"📚 Источники: {len(rag_result['sources'])} документов")
                    response_parts.append("")
                
                response_parts.append("⚠️ Ваше обращение зарегистрировано и передано специалистам.")
                response_parts.append(self.escalation.format_ticket_message(ticket))
                
                if classification.reasoning:
                    response_parts.append(f"\n📊 Обоснование: {classification.reasoning}")
                
                response = "\n".join(response_parts)
                
                await update.message.reply_text(response)
                self._add_to_history(user.id, response, is_bot=True)
        
        except Exception as e:
            print(f"Ошибка обработки сообщения: {e}")
            import traceback
            traceback.print_exc()
            error_message = "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже или обратитесь в поддержку напрямую."
            await update.message.reply_text(error_message)
    
    def run(self):
        """Запуск бота"""
        print("Запуск Telegram бота...")
        self.application.add_error_handler(self.error_handler)
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        if isinstance(context.error, Conflict):
            error_msg = str(context.error)
            if "getUpdates" in error_msg:
                print("\n[WARNING] Конфликт: другой экземпляр бота уже запущен.")
                return
        
        logger.error(f"Exception: {context.error}", exc_info=context.error)
        
        if update and hasattr(update, 'effective_user'):
            try:
                user = update.effective_user
                await context.bot.send_message(
                    chat_id=user.id,
                    text="Извините, произошла ошибка. Попробуйте позже."
                )
            except Exception:
                pass
