"""
Telegram бот для поддержки клиентов
"""
import os
import time
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
from .database.conversation_storage import ConversationStorage
from .utils.rate_limiter import RateLimiter
from .utils.metrics import get_metrics
from .utils.logger import setup_logger, get_logger

load_dotenv()

# Настройка логгера
logger = setup_logger("support_bot", level=os.getenv("LOG_LEVEL", "INFO"))
metrics = get_metrics()


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
        
        # Персистентное хранение истории диалогов
        storage_type = os.getenv("CONVERSATION_STORAGE_TYPE", "file")
        self.conversation_storage = ConversationStorage(storage_type=storage_type)
        
        # Rate limiter для защиты от злоупотреблений
        self.rate_limiter = RateLimiter()
        
        # Загрузка базы знаний
        logger.info("Инициализация RAG системы...")
        self.rag_system.load_knowledge_base()
        
        # Создание приложения
        self.application = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        self._register_handlers()
        
        # Информация о настройке
        if self.support_chat_id:
            logger.info(f"Группа поддержки настроена: {self.support_chat_id}")
        else:
            logger.warning("SUPPORT_CHAT_ID не настроен. Тикеты не будут отправляться специалистам.")
            logger.info("Добавьте SUPPORT_CHAT_ID в .env файл для отправки тикетов в группу.")
    
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
        self.conversation_storage.clear_history(user.id)
        metrics.record_user_action(user.id, "start_command")
    
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
        self.conversation_storage.clear_history(user.id)
        metrics.record_user_action(user.id, "clear_command")
        await update.message.reply_text("История диалога очищена")
    
    def _add_to_history(self, user_id: int, message: str, is_bot: bool = False):
        """Добавление сообщения в историю"""
        self.conversation_storage.add_message(user_id, message, is_bot=is_bot)
    
    def _get_history(self, user_id: int, limit: int = 10) -> List[str]:
        """Получить историю диалога"""
        return self.conversation_storage.get_history(user_id, limit=limit)
    
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
        
        # Проверка rate limit
        if not self.rate_limiter.is_allowed(user.id, "message"):
            remaining = self.rate_limiter.get_remaining(user.id, "message")
            await update.message.reply_text(
                f"Превышен лимит запросов. Попробуйте позже. "
                f"Оставшихся запросов: {remaining}"
            )
            metrics.increment("rate_limit_exceeded")
            return
        
        # Добавляем сообщение пользователя в историю
        self._add_to_history(user.id, message_text, is_bot=False)
        metrics.record_user_action(user.id, "message_sent")
        metrics.increment("messages_total")
        
        # Показываем индикатор печати
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        start_time = time.time()
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
            history = self._get_history(user.id, limit=10)
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
                    classification,
                    is_faq=is_faq,
                    conversation_history=history
                )
                
                # Создаем тикет
                ticket = self.escalation.create_ticket(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    description=message_text,
                    classification=classification,
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
            duration = time.time() - start_time
            metrics.record_timing("message_processing_time", duration)
            metrics.increment("message_processing_errors")
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            error_message = "Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже или обратитесь в поддержку напрямую."
            await update.message.reply_text(error_message)
        finally:
            duration = time.time() - start_time
            metrics.record_timing("message_processing_time", duration)
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск Telegram бота...")
        self.application.add_error_handler(self.error_handler)
        
        # Сохранение метрик при завершении
        import atexit
        atexit.register(lambda: metrics.save_metrics())
        
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок с детальным логированием"""
        if isinstance(context.error, Conflict):
            error_msg = str(context.error)
            if "getUpdates" in error_msg:
                logger.warning("Конфликт: другой экземпляр бота уже запущен.")
                metrics.increment("bot_conflicts")
                return
        
        error_type = type(context.error).__name__
        error_message = str(context.error)
        
        logger.error(
            f"Exception в обработчике: {error_type}: {error_message}",
            exc_info=context.error
        )
        
        metrics.increment("bot_errors", labels={"error_type": error_type})
        
        if update and hasattr(update, 'effective_user'):
            try:
                user = update.effective_user
                await context.bot.send_message(
                    chat_id=user.id,
                    text="Извините, произошла ошибка. Попробуйте позже."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")
