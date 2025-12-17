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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
)
from config import get_settings

# Получаем настройки с валидацией
try:
    settings = get_settings()
except ValueError as e:
    print(str(e))
    exit(1)

from database import init_db
from models import Ticket, Category, Criticality, SupportLine, TicketStatus
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
    """Обработчик команды /start и главное меню"""
    user = update.effective_user
    
    # Очищаем историю при новом старте
    user_id = user.id
    if user_id in user_conversations:
        user_conversations[user_id] = []
        
    welcome_text = (
        f"Здравствуйте, {user.first_name}! 👋\n\n"
        "Я интеллектуальный помощник поддержки. "
        "Опишите вашу проблему текстом, и я помогу её решить или создам обращение."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🗣️ Связаться с оператором", callback_data="contact_operator"),
            InlineKeyboardButton("📋 Мои обращения", callback_data="my_tickets"),
        ],
        [
             InlineKeyboardButton("❓ Помощь", callback_data="help"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📋 <b>Справка</b>

Я умею:
• Отвечать на вопросы по услугам банка
• Принимать жалобы и предложения
• Показывать статус ваших обращений

🔹 <b>Как пользоваться:</b>
Просто напишите ваш вопрос в чат. Если это новая тема, я автоматически создам обращение.

🔹 <b>Команды:</b>
/start - Главное меню
/my_tickets - Мои обращения
/help - Эта справка
"""
    # Определяем, куда отвечать (на команду или на нажатие кнопки)
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(help_text, parse_mode="HTML")
    elif update.message:
        await update.message.reply_text(help_text, parse_mode="HTML")
    else:
        # Fallback на случай, если сообщение не найдено (например, эффективное сообщение)
        if update.effective_message:
            await update.effective_message.reply_text(help_text, parse_mode="HTML")


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /my_tickets"""
    user = update.effective_user
    tickets = escalation_system.get_user_tickets(user.id)
    
    # Определяем сообщение для ответа
    target_message = None
    if update.callback_query and update.callback_query.message:
        target_message = update.callback_query.message
    elif update.message:
        target_message = update.message
    else:
        target_message = update.effective_message

    if not target_message:
        logger.error("Не удалось определить сообщение для ответа в my_tickets")
        return

    if not tickets:
        await target_message.reply_text("У вас пока нет активных обращений.")
        return
    
    message = "📋 <b>Ваши обращения:</b>\n\n"
    for ticket in tickets[:5]:  # Показываем последние 5 для компактности
        status_emoji = {
            "open": "🟢", "in_progress": "🟡", "escalated": "🟠",
            "resolved": "✅", "closed": "⚫"
        }
        
        # Экранирование для HTML не требуется для обычного текста, если там нет < > &
        # Но на всякий случай можно простым replace или html.escape
        import html
        title = html.escape(ticket.title)
        
        message += f"{status_emoji.get(ticket.status.value, '⚪')} <b>#{ticket.id}</b>\n"
        message += f"📝 {title}\n"
        message += f"Раздел: {ticket.category.value}\n"
        message += f"Статус: {ticket.status.value}\n\n"
    
    await target_message.reply_text(message, parse_mode="HTML")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /clear"""
    user = update.effective_user
    user_id = user.id
    
    if user_id in user_conversations:
        user_conversations[user_id] = []
    
    if update.message:
         await update.message.reply_text("🧹 История переписки очищена.")
    elif update.effective_message:
         await update.effective_message.reply_text("🧹 История переписки очищена.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "help":
        await help_command(update, context)
        
    elif data == "my_tickets":
        await my_tickets(update, context)
        
    elif data == "contact_operator":
        # Создаем тикет с эскалацией
        try:
            ticket = escalation_system.create_ticket(
                title="Запрос оператора",
                description="Пользователь запросил связь с оператором через меню",
                user_id=user.id,
                user_name=user.first_name,
                category=Category.OTHER,
                criticality=Criticality.MEDIUM,
                support_line=SupportLine.LINE_1,
                conversation_history=get_user_conversation(user.id)
            )
            await query.message.reply_text(
                f"✅ <b>Обращение #{ticket.id} создано.</b>\n"
                "Оператор подключится к диалогу в ближайшее время.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка создания тикета оператора: {e}")
            await query.message.reply_text("Не удалось связаться с оператором. Попробуйте позже.")


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
        # 1. Проверяем приветствия
        user_message_lower = user_message.lower().strip()
        greetings = ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро", "start", "начать"]
        if any(user_message_lower.startswith(g) for g in greetings) and len(user_message) < 20:
            if not update.callback_query: # Не показываем меню снова, если это callback
                 await start(update, context)
            return

        # 2. Классификация и проверка тематики
        classification = classifier.classify(user_message, conversation)
        
        # Фильтрация не-Сбер вопросов
        if not classification.get("is_bank_related", True):
            await update.message.reply_text(
                "❌ Я могу помочь только с вопросами Сбербанка.\n"
                "(карты, вклады, приложение, переводы, кредиты)"
            )
            return

        # 3. Автоматическое создание тикета (если новая тема)
        # Проверяем, есть ли уже открытый тикет
        # TODO: Добавить проверку открытых тикетов, пока просто создаем если is_new_topic
        
        if classification.get("is_new_topic", False):
            # Создаем тикет "тихо" (без уведомления пользователя, или с минимальным)
            try:
                ticket = escalation_system.create_ticket(
                    title=f"Авто-обращение: {user_message[:30]}...",
                    description=user_message,
                    user_id=user_id,
                    user_name=user.first_name,
                    category=classification["category"],
                    criticality=classification["criticality"],
                    support_line=classification["support_line"],
                    conversation_history=conversation
                )
                logger.info(f"Создан авто-тикет #{ticket.id}")
            except Exception as e:
                logger.error(f"Ошибка создания авто-тикета: {e}")

        # 4. RAG Поиск
        context_docs = rag.get_context_for_query(user_message, max_results=3)
        
        # 5. Генерация ответа
        system_prompt = f"""Ты - помощник службы поддержки Сбербанка.
Твоя задача: вежливо помочь клиенту.
Контекст из базы знаний:
{context_docs if context_docs else "Нет информации"}

Отвечай кратко, вежливо и по сути вопроса."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем последние сообщения для контекста
        for msg in conversation[-3:]: 
            messages.append(msg)
            
        ai_response = gigachat.generate_response(messages)
        
        # Добавляем ответ бота в историю
        add_to_conversation(user_id, "assistant", ai_response)
        
        await update.message.reply_text(ai_response)


    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла техническая ошибка. Попробуйте позже.")


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
            
            final_message = f"Пользователь прислал голосовое сообщение.\n[ТРАНСКРИПЦИЯ]: {text}"
            await process_user_text(update, context, final_message)

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

            # Анализируем содержимое с помощью GigaChat (чистим OCR)
            await status_msg.edit_text("🧠 Анализирую содержимое изображения...")
            # Запускаем в executor, так как это синхронный вызов сети
            loop = asyncio.get_running_loop()
            clean_content = await loop.run_in_executor(
                None, lambda: gigachat.analyze_image_content(ocr_text)
            )
            
            # Формируем итоговое сообщение с учетом подписи (caption)
            caption = message.caption or ""
            
            # Структурированное сообщение для классификатора и оператора
            final_message = (
                f"Пользователь прислал скриншот/изображение.\n"
                f"[АНАЛИЗ ИЗОБРАЖЕНИЯ]: {clean_content}\n"
                f"[ТЕКСТ ПОДПИСИ]: {caption if caption else 'без подписи'}"
            )

            # Убираем сообщение о статусе и обрабатываем
            await status_msg.delete()
            await process_user_text(update, context, final_message)

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
    
    # Обработчик кнопок меню
    application.add_handler(CallbackQueryHandler(button_handler))
    
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

