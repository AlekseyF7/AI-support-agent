""" 
Пользовательский интерфейс взаимодействия с ИИ-ассистентом.
Реализует мультимодальную обработку (текст, голос, изображения) и O2O навигацию.
"""
import asyncio
import logging
import io
from typing import Dict, List, Optional, Union

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from models import Category, Criticality, SupportLine
from gigachat_client import GigaChatClient
from rag_system import RAGSystem, MockRAGSystem
from classifier import RequestClassifier
from escalation import EscalationSystem
from salute_speech_client import SaluteSpeechClient
from metrics import metrics  # Система метрик
from geo_service import GeoService
from keyboards.client_kb import get_main_keyboard
from config import settings

logger = logging.getLogger(__name__)

router = Router()

# Кэш контекста диалогов (InMemory для демонстрации, рекомендуется Redis для продакшена)
_user_conversations: Dict[int, List[dict]] = {}

def get_user_conversation(user_id: int) -> List[dict]:
    """Возвращает историю сообщений пользователя."""
    return _user_conversations.setdefault(user_id, [])

def add_to_conversation(user_id: int, role: str, content: str):
    """Добавляет сообщение в историю, соблюдая лимит окна контекста."""
    conv = get_user_conversation(user_id)
    conv.append({"role": role, "content": content})
    if len(conv) > 10:  # Окно в 10 сообщений для экономии токенов и памяти
        conv.pop(0)

@router.message(Command("start"))
async def cmd_start(message: Message) -> Message:
    """Приветственное сообщение и инициализация меню."""
    return await message.answer(
        "👋 <b>Здравствуйте! Я ИИ-помощник Сбербанка.</b>\n\n"
        "Я помогу вам решить вопросы по банковским продуктам:\n"
        "• 💳 Консультация по картам и вкладам\n"
        "• 🖼️ Анализ скриншотов с ошибками\n"
        "• 🎙️ Понимание голосовых сообщений\n"
        "• 📍 Поиск отделений и построение маршрутов\n\n"
        "Напишите ваш вопрос или выберите действие в меню.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.location)
async def handle_location(message: Message, geo: GeoService) -> Message:
    """Обработка входящей геопозиции для поиска ближайших отделений."""
    if not geo:
        return await message.answer("❌ Сервис геолокации временно недоступен.")
    
    lat, lon = message.location.latitude, message.location.longitude
    status_msg = await message.answer("🔍 Ищу ближайшие к вам отделения Сбера...")
    
    branches = await geo.find_nearest_branches(lat, lon, radius=5000)
    
    if not branches:
        return await status_msg.edit_text(
            "📍 Поблизости не найдено отделений Сбера.\n"
            "Попробуйте обратиться в чат или позвонить по номеру 900."
        )

    text = "📍 <b>Ближайшие к вам отделения:</b>\n\n"
    for i, b in enumerate(branches[:3], 1):
        text += f"{i}. <b>{b['name']}</b>\n"
        text += f"🏠 {b['address']}\n"
        text += f"🔗 <a href='{b['url']}'>Посмотреть на 2GIS</a>\n\n"
    
    await status_msg.delete()
    return await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

async def process_user_request_core(
    event: Union[Message, CallbackQuery], 
    text: str, 
    db: AsyncSession,
    gigachat: GigaChatClient,
    rag: Union[RAGSystem, MockRAGSystem],
    classifier: RequestClassifier,
    escalation_system: EscalationSystem
) -> None:
    """
    Централизованное ядро обработки входящего запроса.
    Реализует цепочку: Классификация -> RAG -> Генерация -> O2O.
    """
    user = event.from_user
    chat_id = event.message.chat.id if isinstance(event, CallbackQuery) else event.chat.id
    target_msg = event.message if isinstance(event, CallbackQuery) else event
    
    # 1. Анализ намерений и домена (Без записи в историю до подтверждения релевантности)
    conversation = get_user_conversation(user.id)
    await event.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Классификация
    cls = await classifier.classify(text, conversation)
    
    # Проверка на соответствие банковской тематике (защита от оффтопа)
    if not cls.get("is_bank_related", True):
        await target_msg.answer("❗ Данный запрос не поддерживается ИИ-ассистентом Сбербанка.")
        return

    # Добавление в контекст после валидации
    add_to_conversation(user.id, "user", text)
    current_conv = get_user_conversation(user.id)

    # ПРИМЕЧАНИЕ: Тикеты теперь создаются УСЛОВНО после самооценки (шаг 5)
    # Старая логика удалена в пользу интеллектуальной эскалации


    # 3. Retrieval Augmented Generation (RAG)
    kb_context = await rag.get_context_for_query(text)
    system_prompt = (
        "Ты - официальный ИИ-ассистент Сбербанка. Твоя речь вежлива и профессиональна.\n"
        "Отвечай чётко и по существу. Если не знаешь ответ - честно признай это.\n"
        "Используй предоставленные выдержки из базы знаний Сбера для ответа.\n"
        f"БАЗА ЗНАНИЙ:\n{kb_context if kb_context else 'Данные отсутствуют. Ответь общими знаниями о Сбере.'}"
    )
    
    # Формируем окно для GigaChat
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(current_conv[-4:])
    
    answer = await gigachat.generate_response(messages)
    add_to_conversation(user.id, "assistant", answer)
    
    # 4. САМООЦЕНКА: Агент определяет, помог ли он пользователю
    assessment = await classifier.assess_response(text, answer, cls)
    logger.info(f"🎯 Самооценка: resolved={assessment['is_resolved']}, confidence={assessment['confidence']}, escalate={assessment['needs_escalation']}")
    
    # Запись метрик
    metrics.record_request(cls, assessment)
    
    # 5. УСЛОВНАЯ ЭСКАЛАЦИЯ: Тикет создается ТОЛЬКО если агент не помог
    # ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА: Не создавать тикет, если это простой чат (resolved=True)
    if assessment["needs_escalation"]:
        try:
            ticket, is_new = await escalation_system.create_ticket(
                title=f"[{cls['support_line'].value.upper()}] {text[:50]}...",
                description=f"Запрос: {text}\n\nОтвет ИИ: {answer}\n\nПричина эскалации: {assessment.get('escalation_reason', 'Не определена')}",
                user_id=user.id,
                user_name=user.full_name,
                category=cls["category"],
                criticality=cls["criticality"],
                support_line=cls["support_line"],
                conversation_history=current_conv
            )
            if is_new:
                answer += f"\n\n📋 <i>Создано обращение #{ticket.id}. Специалист свяжется с вами.</i>"
            else:
                answer += f"\n\n📋 <i>Запрос добавлен к обращению #{ticket.id}.</i>"
        except Exception as e:
            logger.error(f"❌ Ошибка эскалации: {e}")
    
    # 6. Формирование клавиатуры ответа
    buttons = []
    
    # Кнопка O2O только если нужен визит ИЛИ явно запрошено
    is_location_request = cls.get("needs_offline") or "отделени" in text.lower() or "офис" in text.lower() or "банкомат" in text.lower()
    
    if is_location_request:
        webapp_url = settings.WEBAPP_URL or "https://sber-support-agent.ngrok.io" # Fallback
        buttons.append([InlineKeyboardButton(text="📍 Найти ближайшее отделение", web_app=WebAppInfo(url=webapp_url))])
    
    # Кнопка ручной эскалации (только если нет тикета)
    if assessment["is_resolved"] and not assessment["needs_escalation"]:
        buttons.append([InlineKeyboardButton(text="❌ Проблема не решена", callback_data=f"escalate_{user.id}")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    
    await target_msg.answer(answer, reply_markup=reply_markup, parse_mode="HTML")

@router.message(F.text, ~F.text.startswith("/"))
async def handle_text_request(
    message: Message, 
    db: AsyncSession,
    gigachat: GigaChatClient,
    rag: Union[RAGSystem, MockRAGSystem],
    classifier: RequestClassifier,
    escalation_system: EscalationSystem,
    **kwargs
) -> None:
    """Обработка обычных текстовых сообщений."""
    # Логика экранных кнопок ReplyKeyboard
    if message.text == "📂 Мои заявки":
        return await text_my_tickets(message, escalation_system)
    if message.text == "📞 Позвать оператора":
        return await text_contact_operator(message, escalation_system)
    if message.text == "❓ Помощь":
        from handlers.common import cmd_help
        return await cmd_help(message)
        
    await process_user_request_core(
        message, 
        message.text, 
        db=db, 
        gigachat=gigachat, 
        rag=rag, 
        classifier=classifier, 
        escalation_system=escalation_system
    )

@router.message(F.voice | F.audio)
async def handle_voice_request(
    message: Message, 
    bot: Bot, 
    stt: SaluteSpeechClient,
    db: AsyncSession,
    gigachat: GigaChatClient,
    rag: Union[RAGSystem, MockRAGSystem],
    classifier: RequestClassifier,
    escalation_system: EscalationSystem,
    **kwargs
) -> None:
    """Обработка голосовых сообщений через Salute Speech."""
    if not stt:
        return await message.answer("⚠️ Голосовой ввод временно недоступен.")

    status = await message.answer("🎤 Распознаю вашу речь...")
    try:
        audio = message.voice or message.audio
        file = await bot.get_file(audio.file_id)
        buffer = io.BytesIO()
        await bot.download(file, destination=buffer)
        
        text, ok = await stt.recognize(buffer.getvalue())
        if not ok or not text:
            return await status.edit_text("❌ Не удалось распознать голос. Пожалуйста, напишите текстом.")

        await status.delete()
        await process_user_request_core(
            message, 
            f"[ГОЛОСОВОЕ СООБЩЕНИЕ]: {text}", 
            db=db, 
            gigachat=gigachat,
            rag=rag,
            classifier=classifier,
            escalation_system=escalation_system
        )
    except Exception as e:
        logger.error(f"❌ Ошибка STT: {e}")
        await status.edit_text("❌ Произошла ошибка при обработке аудио.")

@router.message(F.photo | F.document.mime_type.startswith("image/"))
async def handle_image_request(
    message: Message, 
    bot: Bot, 
    gigachat: GigaChatClient,
    db: AsyncSession,
    rag: Union[RAGSystem, MockRAGSystem],
    classifier: RequestClassifier,
    escalation_system: EscalationSystem,
    **kwargs
) -> None:
    """Vision-анализ скриншотов и документов."""
    status = await message.answer("👁️ Анализирую изображение...")
    try:
        source = message.photo[-1] if message.photo else message.document
        file = await bot.get_file(source.file_id)
        buffer = io.BytesIO()
        await bot.download(file, destination=buffer)
        
        prompt = "Опиши проблему или информацию на этом банковском документе/скриншоте максимально подробно."
        analysis = await gigachat.analyze_image(buffer.getvalue(), prompt)
        
        user_comment = message.caption or ""
        enriched_text = f"[АНАЛИЗ ИЗОБРАЖЕНИЯ]: {analysis}\n[КОММЕНТАРИЙ]: {user_comment}"
        
        await status.delete()
        await process_user_request_core(
            message, 
            enriched_text, 
            db=db, 
            gigachat=gigachat,
            rag=rag,
            classifier=classifier,
            escalation_system=escalation_system
        )
    except Exception as e:
        logger.error(f"❌ Ошибка Vision: {e}")
        try:
            await status.edit_text("❌ Не удалось проанализировать изображение.")
        except:
            await message.answer("❌ Не удалось проанализировать изображение.")

@router.callback_query(F.data == "my_tickets")
async def cb_my_tickets(callback: CallbackQuery, escalation_system: EscalationSystem) -> None:
    """Просмотр заявок через инлайн-кнопку."""
    await cb_my_tickets_core(callback.message, callback.from_user.id, escalation_system)
    await callback.answer()

async def text_my_tickets(message: Message, escalation_system: EscalationSystem) -> None:
    """Просмотр заявок через меню."""
    await cb_my_tickets_core(message, message.from_user.id, escalation_system)

async def cb_my_tickets_core(message: Message, user_id: int, escalation_system: EscalationSystem) -> None:
    """Логика формирования списка обращений."""
    tickets = await escalation_system.get_user_tickets(user_id)
    if not tickets:
        await message.answer("📭 У вас пока нет активных обращений.")
        return
    
    text = "📋 <b>Ваши обращения:</b>\n\n"
    for t in tickets[:5]:
        status_icons = {"open": "🟢", "in_progress": "🟡", "resolved": "✅", "closed": "⚫"}
        icon = status_icons.get(t.status.value, "⚪")
        text += f"{icon} <b>#{t.id}</b>\n📝 {t.title}\nСтатус: <i>{t.status.value}</i>\n\n"
    
    await message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "contact_operator")
async def cb_contact_operator(callback: CallbackQuery, escalation_system: EscalationSystem) -> None:
    """Вызов оператора через инлайн-кнопку."""
    await contact_operator_core(callback.message, callback.from_user, escalation_system)
    await callback.answer()

async def text_contact_operator(message: Message, escalation_system: EscalationSystem) -> None:
    """Вызов оператора через меню."""
    await contact_operator_core(message, message.from_user, escalation_system)

async def contact_operator_core(message: Message, from_user, escalation_system_obj: EscalationSystem) -> None:
    """Создание прямого запроса к оператору."""
    try:
        ticket, is_new = await escalation_system_obj.create_ticket(
            title="Запрос оператора (вручную)",
            description="Пользователь запросил живого оператора через меню.",
            user_id=from_user.id,
            user_name=from_user.full_name,
            category=Category.OTHER,
            criticality=Criticality.MEDIUM,
            support_line=SupportLine.LINE_1,
            conversation_history=get_user_conversation(from_user.id)
        )
        await message.answer(
            f"✅ Создано обращение <b>#{ticket.id}</b>.\nСпециалист свяжется с вами в этом чате.", 
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка вызова оператора: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

@router.callback_query(F.data.startswith("escalate_"))
async def cb_manual_escalation(callback: CallbackQuery, escalation_system: EscalationSystem) -> None:
    """Ручная эскалация по нажатию кнопки 'Проблема не решена'."""
    user = callback.from_user
    conversation = get_user_conversation(user.id)
    
    # Получаем последний вопрос пользователя из истории
    last_question = "Пользователь указал, что проблема не решена"
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_question = msg.get("content", last_question)
            break
    
    try:
        ticket, is_new = await escalation_system.create_ticket(
            title=f"[РУЧНАЯ ЭСКАЛАЦИЯ] {last_question[:40]}...",
            description=f"Пользователь нажал 'Проблема не решена'.\n\nПоследний запрос: {last_question}",
            user_id=user.id,
            user_name=user.full_name,
            category=Category.OTHER,
            criticality=Criticality.MEDIUM,
            support_line=SupportLine.LINE_1,
            conversation_history=conversation
        )
        
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ Создано обращение <b>#{ticket.id}</b>.\n"
            "Специалист 1-й линии поддержки свяжется с вами в ближайшее время.",
            parse_mode="HTML"
        )
        await callback.answer("Обращение создано!")
    except Exception as e:
        logger.error(f"❌ Ошибка ручной эскалации: {e}")
        await callback.answer("Ошибка создания обращения", show_alert=True)

@router.message(Command("clear"))
async def cmd_clear(message: Message) -> Message:
    """Очистка истории диалога."""
    _user_conversations[message.from_user.id] = []
    return await message.answer("🧹 Контекст диалога очищен. Я готов к новым вопросам!")
