"""Telegram бот для поддержки клиентов"""
# ВАЖНО: Настройка кодировки должна быть ПЕРВОЙ!
import sys
import os
import io

# Настройка кодировки для Windows (делаем ДО всех импортов)
if sys.platform == 'win32':
    # Устанавливаем переменные окружения
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Переопределяем stdout и stderr для UTF-8
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8', 
            errors='replace',
            line_buffering=True
        )
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, 
            encoding='utf-8', 
            errors='replace',
            line_buffering=True
        )
    
    # Устанавливаем кодовую страницу консоли в UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)  # UTF-8
        kernel32.SetConsoleCP(65001)  # UTF-8
    except Exception:
        pass

# Отключаем телеметрию chromadb ДО импорта rag_system
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "1"
os.environ["ALLOW_RESET"] = "TRUE"

import logging
import asyncio
import tempfile
from pathlib import Path

# Подавляем логи телеметрии chromadb
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry").disabled = True
logging.getLogger("chromadb.telemetry.product").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product").disabled = True
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").disabled = True

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import get_settings

# Получаем настройки с валидацией
try:
    settings = get_settings()
except ValueError as e:
    print(str(e))
    exit(1)
from models import init_db, TicketStatus
from gigachat_client import GigaChatClient
from rag_system import RAGSystem
from classifier import RequestClassifier
from escalation import EscalationSystem
from operator_commands import (
    cmd_tickets, cmd_ticket, cmd_take, cmd_reply, cmd_close, cmd_stats
)
import json

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import requests
from salute_speech_client import SaluteSpeechClient

# Инициализация компонентов
logger.info("Инициализация базы данных...")
init_db()
logger.info("База данных инициализирована")

logger.info("Инициализация GigaChat клиента...")
gigachat = GigaChatClient()

logger.info("Инициализация RAG системы...")
try:
    rag = RAGSystem()
    logger.info(f"RAG система: ChromaDB доступен = {rag.chromadb_available}")
except Exception as e:
    logger.error(f"Ошибка инициализации RAG системы: {e}", exc_info=True)
    # Создаем заглушку, чтобы бот мог работать без RAG
    class SimpleRAGSystem:
        def __init__(self):
            self.chromadb_available = False
            self.knowledge_base = {}
        def get_context_for_query(self, query, max_results=3):
            return "Релевантная информация не найдена."
    rag = SimpleRAGSystem()
    logger.warning("RAG система работает в упрощенном режиме")

logger.info("Инициализация классификатора запросов...")
classifier = RequestClassifier(gigachat_client=gigachat)

logger.info("Инициализация системы эскалации...")
escalation_system = EscalationSystem()

logger.info("Инициализация клиента Salute Speech для распознавания речи...")
try:
    salute_speech_client = SaluteSpeechClient(
        getattr(settings, "SALUTE_SPEECH_CLIENT_ID", ""),
        getattr(settings, "SALUTE_SPEECH_CLIENT_SECRET", ""),
    )
    logger.info("Клиент Salute Speech инициализирован")
except Exception as e:
    logger.warning(f"Не удалось инициализировать Salute Speech клиент: {e}. Голосовое распознавание будет недоступно.")
    salute_speech_client = None

logger.info("Все компоненты успешно инициализированы")

# Хранилище истории разговоров пользователей
user_conversations = {}


def get_user_conversation(user_id: int) -> list:
    """Получение истории разговора пользователя"""
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    return user_conversations[user_id]


def add_to_conversation(user_id: int, role: str, content: str):
    """Добавление сообщения в историю"""
    conversation = get_user_conversation(user_id)
    conversation.append({"role": role, "content": content})
    # Ограничиваем историю последними 10 сообщениями
    if len(conversation) > 10:
        conversation.pop(0)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_message = f"""
Привет, {user.first_name}! 👋

Я интеллектуальный бот поддержки клиентов. Я могу:
• Ответить на типовые вопросы
• Помочь с техническими проблемами
• Создать обращение в службу поддержки
• Показать статус ваших обращений

Доступные команды:
/help - Список команд
/my_tickets - Мои обращения
/new_ticket - Создать новое обращение
/clear - Очистить историю разговора
"""
    await update.message.reply_text(welcome_message)
    
    # Очищаем историю при новом старте
    user_id = user.id
    if user_id in user_conversations:
        user_conversations[user_id] = []


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📋 Доступные команды:

/start - Начать работу с ботом
/help - Показать эту справку
/my_tickets - Посмотреть все мои обращения
/new_ticket - Создать новое обращение
/clear - Очистить историю нашего разговора

💬 Просто напишите мне ваш вопрос, и я постараюсь помочь!
"""
    await update.message.reply_text(help_text)


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /my_tickets"""
    user = update.effective_user
    tickets = escalation_system.get_user_tickets(user.id)
    
    if not tickets:
        await update.message.reply_text("У вас пока нет обращений.")
        return
    
    message = "📋 Ваши обращения:\n\n"
    for ticket in tickets[:10]:  # Показываем последние 10
        status_emoji = {
            "open": "🟢",
            "in_progress": "🟡",
            "escalated": "🟠",
            "resolved": "✅",
            "closed": "⚫"
        }
        
        criticality_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }
        
        emoji_status = status_emoji.get(ticket.status.value, "⚪")
        emoji_crit = criticality_emoji.get(ticket.criticality.value, "⚪")
        
        message += f"{emoji_status} #{ticket.id} - {ticket.title}\n"
        message += f"   Линия: {ticket.support_line.value} | "
        message += f"Критичность: {emoji_crit} {ticket.criticality.value}\n"
        message += f"   Статус: {ticket.status.value}\n"
        message += f"   Создано: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    await update.message.reply_text(message)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /clear"""
    user = update.effective_user
    user_id = user.id
    
    if user_id in user_conversations:
        user_conversations[user_id] = []
    
    await update.message.reply_text("История разговора очищена. Можем начать заново!")


async def process_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
    """Общий обработчик логики ответа по тексту (из чата, голоса или изображения)"""
    user = update.effective_user
    user_id = user.id
    
    # Добавляем сообщение пользователя в историю
    add_to_conversation(user_id, "user", user_message)
    conversation = get_user_conversation(user_id)
    
    # Показываем статус "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Проверяем, является ли сообщение приветствием
        user_message_lower = user_message.lower().strip()
        greetings = [
            "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер",
            "доброе утро", "доброй ночи", "приветствую", "салют", "хай", "hi", "hello",
            "доброго времени суток", "доброго дня"
        ]
        is_greeting = any(user_message_lower.startswith(greeting) or user_message_lower == greeting 
                          for greeting in greetings)
        
        # Если это не приветствие, проверяем банковскую тематику
        if not is_greeting:
            classification_check = classifier.classify(user_message, conversation)
            if not classification_check.get("is_bank_related", False):
                await update.message.reply_text(
                    "❌ Я могу помочь только с вопросами, связанными с банковскими услугами.\n\n"
                    "Ваш вопрос не относится к банковской тематике. "
                    "Я специализируюсь на вопросах, связанных с:\n"
                    "• Банковскими услугами, счетами, картами\n"
                    "• Переводами, кредитами, депозитами\n"
                    "• Мобильным приложением банка, интернет-банком\n"
                    "• Банкоматами, платежами и операциями по счетам\n\n"
                    "Пожалуйста, задайте вопрос, связанный с банковскими услугами."
                )
                return
        
        # 1. Пытаемся найти ответ в RAG базе знаний
        context_docs = rag.get_context_for_query(user_message, max_results=3)
        
        # 2. Формируем промпт для ответа с учетом контекста
        system_prompt = """Ты - вежливый и профессиональный помощник службы поддержки банка. 
Отвечай на вопросы пользователей на основе предоставленной информации из базы знаний.
Если информации недостаточно или вопрос требует создания обращения, сообщи об этом.
Отвечай кратко и по делу, на русском языке."""
        
        # Формируем сообщения для GigaChat
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context_docs and context_docs != "Релевантная информация не найдена.":
            context_message = f"""Контекст из базы знаний:
{context_docs}

Вопрос пользователя: {user_message}"""
            messages.append({"role": "user", "content": context_message})
        else:
            messages.append({"role": "user", "content": user_message})
        
        # 3. Генерируем ответ
        bot_response = gigachat.generate_response(messages, temperature=0.7)
        
        # 4. Проверяем, нужно ли создавать обращение
        # (если пользователь явно просит помощь или RAG не нашел ответ)
        # Приветствия не создают тикеты
        should_create_ticket = (
            not is_greeting and (
                "обращение" in user_message.lower() or
                "заявка" in user_message.lower() or
                "тикет" in user_message.lower() or
                context_docs == "Релевантная информация не найдена." or
                "не знаю" in bot_response.lower() or
                "не могу" in bot_response.lower()
            )
        )
        
        # Отправляем ответ пользователю
        await update.message.reply_text(bot_response)
        
        # Добавляем ответ в историю
        add_to_conversation(user_id, "assistant", bot_response)
        
        # 5. Если нужно, классифицируем и создаем обращение
        if should_create_ticket:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            
            # Классификация обращения
            classification = classifier.classify(user_message, conversation)
            
            # Проверяем банковскую тематику перед созданием тикета
            if not classification.get("is_bank_related", False):
                await update.message.reply_text(
                    "❌ Не удалось создать обращение.\n\n"
                    "Ваш вопрос не относится к банковской тематике. "
                    "Я могу помочь только с вопросами, связанными с банковскими услугами, "
                    "счетами, картами, переводами, кредитами и другими банковскими операциями.\n\n"
                    "Пожалуйста, уточните ваш вопрос, если он связан с банком."
                )
                return
            
            # Блокируем создание тикета, если категория "other" (нет конкретной тематики)
            from models import Category
            if classification["category"] == Category.OTHER:
                await update.message.reply_text(
                    "❌ Не удалось создать обращение.\n\n"
                    "Ваш вопрос не содержит конкретной тематики. "
                    "Пожалуйста, уточните ваш вопрос или опишите проблему более детально, "
                    "чтобы мы могли вам помочь."
                )
                return
            
            # Создаем тикет
            ticket = escalation_system.create_ticket(
                title=user_message[:100] if len(user_message) > 100 else user_message,
                description=user_message,
                user_id=user_id,
                user_name=user.full_name or user.username or "Unknown",
                category=classification["category"],
                criticality=classification["criticality"],
                support_line=classification["support_line"],
                conversation_history=conversation
            )
            
            # Уведомление о создании обращения
            ticket_message = f"""
✅ Обращение создано!

📋 Номер: #{ticket.id}
📂 Категория: {ticket.category.value}
⚠️ Критичность: {ticket.criticality.value}
📞 Линия поддержки: {ticket.support_line.value}
📝 Статус: {ticket.status.value}

Ваше обращение передано в соответствующую линию поддержки. Мы свяжемся с вами в ближайшее время.
"""
            await update.message.reply_text(ticket_message)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Попробуйте позже или используйте команду /help."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_message = update.message.text
    await process_user_text(update, context, user_message)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    if salute_speech_client is None:
        await update.message.reply_text(
            "❌ Голосовое распознавание недоступно: не настроены учетные данные Salute Speech. "
            "Пожалуйста, отправьте вопрос текстом."
        )
        return
    
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("Не удалось получить голосовое сообщение.")
        return

    # Показываем статус обработки
    status_msg = await update.message.reply_text("🎤 Распознаю речь...")

    try:
        file = await context.bot.get_file(voice.file_id)
        with tempfile.TemporaryDirectory() as tmpdir:
            ogg_path = Path(tmpdir) / "voice.ogg"
            await file.download_to_drive(str(ogg_path))

            # Проверяем размер файла (Salute Speech имеет ограничения)
            file_size = ogg_path.stat().st_size
            if file_size > 2 * 1024 * 1024:  # 2 MB
                await status_msg.edit_text(
                    "❌ Файл слишком большой (максимум 2 МБ). "
                    "Попробуйте записать более короткое сообщение."
                )
                return

            # Распознаём речь через Sber Salute Speech (SmartSpeech REST API)
            loop = asyncio.get_running_loop()
            text = await loop.run_in_executor(
                None, lambda: salute_speech_client.recognize_file(str(ogg_path), content_type="audio/ogg")
            )

            if not text or len(text.strip()) < 3:
                await status_msg.edit_text(
                    "❌ Не удалось распознать речь. "
                    "Попробуйте говорить громче, чётче и ближе к микрофону."
                )
                return

            # Убираем сообщение о распознавании и сразу обрабатываем текст
            await status_msg.delete()
            await process_user_text(update, context, text)

    except RuntimeError as e:
        # Ошибка с credentials
        logger.error(f"Ошибка Salute Speech (credentials): {e}")
        await status_msg.edit_text(
            "❌ Голосовое распознавание недоступно: не настроены учетные данные Salute Speech. "
            "Обратитесь к администратору."
        )
    except (requests.exceptions.SSLError, requests.exceptions.HTTPError) as e:
        logger.error(f"Ошибка соединения с Salute Speech: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Ошибка при обращении к сервису распознавания речи. "
            "Попробуйте позже или отправьте вопрос текстом."
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Не удалось обработать голосовое сообщение. "
            "Попробуйте ещё раз или отправьте вопрос текстом."
        )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изображений/скриншотов с распознаванием текста"""
    message = update.message
    photo = message.photo[-1] if message.photo else None
    document = message.document if message.document and message.document.mime_type and message.document.mime_type.startswith("image/") else None

    if not photo and not document:
        await message.reply_text("Не удалось получить изображение. Попробуйте отправить скриншот как фото или картинку.")
        return

    # Показываем статус обработки
    status_msg = await message.reply_text("🖼️ Распознаю текст на изображении...")

    try:
        file = await (context.bot.get_file(photo.file_id) if photo else context.bot.get_file(document.file_id))

        with tempfile.TemporaryDirectory() as tmpdir:
            img_path = Path(tmpdir) / "screenshot.png"
            await file.download_to_drive(str(img_path))

            # Улучшенная обработка изображения для лучшего OCR
            image = Image.open(img_path)
            
            # Конвертируем в RGB, если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Улучшаем качество изображения для OCR
            # Увеличиваем контрастность
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Увеличиваем резкость
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Применяем легкое размытие для уменьшения шума
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Увеличиваем размер, если изображение маленькое (улучшает распознавание)
            width, height = image.size
            if width < 800 or height < 600:
                scale = max(800 / width, 600 / height)
                new_size = (int(width * scale), int(height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Распознаём текст с улучшенными параметрами
            ocr_config = r'--oem 3 --psm 6 -l rus+eng'
            ocr_text = pytesseract.image_to_string(image, lang="rus+eng", config=ocr_config).strip()
            
            # Очищаем результат от лишних пробелов и переносов
            lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
            ocr_text = ' '.join(lines)

            if not ocr_text or len(ocr_text.strip()) < 3:
                await status_msg.edit_text(
                    "❌ Не удалось распознать текст на изображении. "
                    "Убедитесь, что текст достаточно крупный и четкий."
                )
                return

            # Убираем сообщение о распознавании и сразу обрабатываем текст
            # НЕ показываем распознанный текст пользователю, только обрабатываем
            await status_msg.delete()
            await process_user_text(update, context, ocr_text)

    except pytesseract.TesseractNotFoundError:
        await status_msg.edit_text(
            "❌ Tesseract OCR не установлен. "
            "Обратитесь к администратору для настройки системы."
        )
        logger.error("Tesseract OCR не найден в системе")
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Не удалось обработать изображение. "
            "Попробуйте еще раз или опишите проблему текстом."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    # Пытаемся отправить пользователю сообщение об ошибке
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже или используйте команду /help."
            )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")


def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики для пользователей
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_tickets", my_tickets))
    application.add_handler(CommandHandler("clear", clear_history))
    
    # Регистрируем обработчики для операторов
    async def tickets_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_tickets(update, context, settings.OPERATOR_IDS)
    
    async def ticket_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_ticket(update, context, settings.OPERATOR_IDS)
    
    async def take_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_take(update, context, settings.OPERATOR_IDS)
    
    async def reply_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_reply(update, context, settings.OPERATOR_IDS, context.bot)
    
    async def close_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_close(update, context, settings.OPERATOR_IDS)
    
    async def stats_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cmd_stats(update, context, settings.OPERATOR_IDS)
    
    application.add_handler(CommandHandler("tickets", tickets_wrapper))
    application.add_handler(CommandHandler("ticket", ticket_wrapper))
    application.add_handler(CommandHandler("take", take_wrapper))
    application.add_handler(CommandHandler("reply", reply_wrapper))
    application.add_handler(CommandHandler("close", close_wrapper))
    application.add_handler(CommandHandler("stats", stats_wrapper))
    
    # Обработчик обычных сообщений (должен быть последним среди текстовых)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Обработчики голосовых сообщений и изображений
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("=" * 60)
    logger.info("Telegram бот поддержки запущен")
    logger.info("Ожидание сообщений...")
    logger.info("=" * 60)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

