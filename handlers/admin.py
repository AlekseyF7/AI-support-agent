""" 
Административный интерфейс оператора службы поддержки.
Реализует управление очередями, обработку тикетов и просмотр статистики.
Обеспечивает синхронизацию статусов с векторной базой данных.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Ticket, TicketStatus, SupportLine, TicketResponse, Category
from config import settings
from escalation import EscalationSystem
from handlers.common import is_operator
from keyboards.operator_kb import get_operator_keyboard, get_ticket_actions, get_line_filter_keyboard
from metrics import metrics

logger = logging.getLogger(__name__)

router = Router()

# Глобальный фильтр роутера: только для операторов, указанных в .env
router.message.filter(lambda m: is_operator(m.from_user.id))
router.callback_query.filter(lambda c: is_operator(c.from_user.id))


# FSM States для интерактивного ответа
class ReplyState(StatesGroup):
    waiting_for_reply = State()

def format_ticket_info(ticket: Ticket) -> str:
    """
    Формирует богатое текстовое представление тикета для оператора.
    
    Args:
        ticket: Объект тикета из БД.
        
    Returns:
        HTML-разметка с деталями обращения.
    """
    status_emoji = {
        TicketStatus.OPEN: "🟢",
        TicketStatus.IN_PROGRESS: "🟡",
        TicketStatus.ESCALATED: "🔴",
        TicketStatus.RESOLVED: "✅",
        TicketStatus.CLOSED: "⚫"
    }
    
    emoji = status_emoji.get(ticket.status, "⚪")
    operator_info = f"\n👤 <b>Оператор:</b> {ticket.operator_name or f'ID:{ticket.operator_id}'}" if ticket.operator_id else ""
    
    return (
        f"{emoji} <b>Тикет #{ticket.id}</b>\n\n"
        f"📋 <b>Заголовок:</b> {ticket.title}\n"
        f"👤 <b>Пользователь:</b> {ticket.user_name} (ID: {ticket.user_id})\n"
        f"📂 <b>Категория:</b> {ticket.category.value}\n"
        f"⚠️ <b>Критичность:</b> {ticket.criticality.value}\n"
        f"📞 <b>Линия:</b> {ticket.support_line.value}\n"
        f"📝 <b>Статус:</b> {ticket.status.value}{operator_info}\n\n"
        f"📄 <b>Описание:</b>\n{ticket.description}\n\n"
        f"🕒 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"🕒 <b>Обновлен:</b> {ticket.updated_at.strftime('%d.%m.%Y %H:%M')}"
    )

@router.message(Command("tickets"))
async def cmd_tickets(message: Message, db: AsyncSession) -> Message:
    """Отображает список последних активных обращений с кнопками действий."""
    try:
        # Получаем 6 последних активных тикетов для удобства
        stmt = select(Ticket).where(
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED])
        ).order_by(Ticket.created_at.desc()).limit(6)
        
        result = await db.execute(stmt)
        open_tickets = list(result.scalars().all())
        
        if not open_tickets:
            return await message.answer("✅ На данный момент все заявки обработаны.", reply_markup=get_operator_keyboard())
        
        await message.answer(f"📋 <b>Активные обращения ({len(open_tickets)}):</b>", parse_mode="HTML")
        
        for ticket in open_tickets:
            status_map = {
                TicketStatus.OPEN: "🟢 Новый",
                TicketStatus.IN_PROGRESS: "🟡 В работе",
                TicketStatus.ESCALATED: "🔴 Эскалировано"
            }
            status_text = status_map.get(ticket.status, "⚪ Неизвестно")
            
            text = (
                f"<b>#{ticket.id}</b> | {status_text}\n"
                f"📝 {ticket.title[:50]}...\n"
                f"👤 {ticket.user_name} | 📞 {ticket.support_line.value}"
            )
            
            await message.answer(text, reply_markup=get_ticket_actions(ticket.id), parse_mode="HTML")
        
        return await message.answer("👆 Выберите тикет для работы", reply_markup=get_operator_keyboard())
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка тикетов: {e}", exc_info=True)
        return await message.answer("❌ Произошла ошибка при загрузке очереди.")

@router.message(Command("ticket"))
async def cmd_ticket(message: Message, command: CommandObject, escalation_system: EscalationSystem) -> Message:
    """Отображает детальную информацию об обращении и историю переписки."""
    if not command.args:
        return await message.answer("❌ Укажите ID: /ticket <id>")
    
    try:
        ticket_id = int(command.args)
    except ValueError:
        return await message.answer("❌ ID должен быть числом.")
    
    ticket = await escalation_system.get_ticket_by_id(ticket_id)
    if not ticket:
        return await message.answer(f"❌ Обращение #{ticket_id} не найдено.")
    
    # Загрузка истории ответов из базы
    stmt = select(TicketResponse).where(
        TicketResponse.ticket_id == ticket_id
    ).order_by(TicketResponse.created_at)
    result = await escalation_system.db.execute(stmt) 
    responses = result.scalars().all()
    
    text = format_ticket_info(ticket)
    if responses:
        text += "\n\n💬 <b>История действий/ответов:</b>\n"
        for resp in responses:
            name = resp.operator_name or f"ID:{resp.operator_id}"
            text += f"\n▫️ <b>{name}</b> ({resp.created_at.strftime('%H:%M')}):\n"
            text += f"   <i>{resp.message}</i>"
    
    return await message.answer(text, parse_mode="HTML")

@router.message(Command("take"))
async def cmd_take(message: Message, command: CommandObject, escalation_system: EscalationSystem) -> Message:
    """Назначает оператора на тикет и меняет статус на 'В работе'."""
    if not command.args:
        return await message.answer("❌ Укажите ID: /take <id>")
    
    try:
        ticket_id = int(command.args)
    except ValueError:
        return await message.answer("❌ Некорректный ID.")
    
    ticket = await escalation_system.get_ticket_by_id(ticket_id)
    if not ticket:
        return await message.answer("❌ Обращение не найдено.")
    
    if ticket.operator_id and ticket.operator_id != message.from_user.id:
        return await message.answer(f"⚠️ Это обращение уже обрабатывает {ticket.operator_name}.")

    # Обновление через систему эскалации для синхронизации с ChromaDB/Vector
    ticket.operator_id = message.from_user.id
    ticket.operator_name = message.from_user.full_name
    await escalation_system.update_ticket_status(ticket_id, TicketStatus.IN_PROGRESS)
    
    return await message.answer(f"✅ Вы взяли обращение #{ticket_id} в работу.")

@router.message(Command("reply"))
async def cmd_reply(message: Message, command: CommandObject, escalation_system: EscalationSystem) -> Message:
    """Отправляет ответ пользователю и фиксирует его в истории обращения."""
    if not command.args or len(command.args.split()) < 2:
        return await message.answer("❌ Используйте: /reply <id> <текст>")
    
    parts = command.args.split(maxsplit=1)
    try:
        ticket_id = int(parts[0])
        message_text = parts[1]
    except ValueError:
        return await message.answer("❌ Неверный формат ID.")
    
    ticket = await escalation_system.get_ticket_by_id(ticket_id)
    if not ticket:
        return await message.answer("❌ Обращение не найдено.")
    
    # Фиксация ответа в БД
    resp = TicketResponse(
        ticket_id=ticket_id,
        operator_id=message.from_user.id,
        operator_name=message.from_user.full_name,
        message=message_text
    )
    escalation_system.db.add(resp)
    
    # Назначение оператора, если тикет был свободным
    if not ticket.operator_id:
        ticket.operator_id = message.from_user.id
        ticket.operator_name = message.from_user.full_name
    
    # Автоматический перевод в статус 'В работе'
    if ticket.status == TicketStatus.OPEN:
        await escalation_system.update_ticket_status(ticket_id, TicketStatus.IN_PROGRESS)
    else:
        await escalation_system.db.commit()
    
    # Уведомление пользователя в Telegram
    try:
        await message.bot.send_message(
            chat_id=ticket.user_id,
            text=f"💬 <b>Ответ оператора по обращению #{ticket_id}:</b>\n\n{message_text}",
            parse_mode="HTML"
        )
        return await message.answer(f"✅ Ваш ответ отправлен пользователю и сохранен в истории.")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить уведомление пользователю #{ticket.user_id}: {e}")
        return await message.answer(f"⚠️ Ответ сохранен в тикете, но пользователь не получил уведомление в боте.")

@router.message(Command("close"))
async def cmd_close(message: Message, command: CommandObject, escalation_system: EscalationSystem) -> Message:
    """Закрывает обращение и уведомляет пользователя о решении."""
    if not command.args:
        return await message.answer("❌ Укажите ID: /close <id>")
        
    try:
        ticket_id = int(command.args)
    except ValueError:
        return await message.answer("❌ Некорректный ID.")
    
    # Статус RESOLVED синхронизирует удаление из векторной базы дедупликации
    ticket = await escalation_system.update_ticket_status(ticket_id, TicketStatus.RESOLVED)
    if not ticket:
        return await message.answer("❌ Обращение не найдено.")
    
    try:
        await message.bot.send_message(
            chat_id=ticket.user_id,
            text=f"✅ Ваше обращение #{ticket_id} отмечено как решенное.\nБудем рады помочь снова!"
        )
    except:
        pass # Игнорируем ошибки отправки при закрытии
        
    return await message.answer(f"✅ Обращение #{ticket_id} успешно закрыто.")

@router.message(Command("stats"))
async def cmd_stats(message: Message, escalation_system: EscalationSystem) -> Message:
    """Выводит сводную аналитику по загруженности линий поддержки."""
    stats = await escalation_system.get_queue_stats()
    
    text = "📊 <b>Оперативная сводка по линиям поддержки:</b>\n"
    
    for line, data in stats.items():
        line_name = line.replace("_", " ").upper()
        text += f"\n📞 <b>{line_name}:</b>\n"
        text += f"   ⚡ Новых: {data['open']}\n"
        text += f"   🚀 Всего в работе: {data['total']}\n"
        
    return await message.answer(text, parse_mode="HTML")


@router.message(Command("metrics"))
async def cmd_metrics(message: Message) -> Message:
    """Метрики эффективности ИИ-агента."""
    from config import settings
    
    text = metrics.format_stats()
    threshold = metrics.get_adaptive_threshold()
    
    # Добавляем информацию об адаптивном пороге
    text += (
        f"\n\n🤖 <b>Adaptive Autopilot:</b>\n"
        f"🎯 Цель: {int(settings.TARGET_SUCCESS_RATE * 100)}%\n"
        f"⚖️ Текущий порог: <b>{threshold}%</b>"
    )
    
    return await message.answer(text, parse_mode="HTML")


# ============= CALLBACK HANDLERS ==============


@router.callback_query(F.data.startswith("take_"))
async def cb_take_ticket(callback: CallbackQuery, escalation_system: EscalationSystem) -> None:
    """Взять тикет в работу через инлайн-кнопку."""
    ticket_id = int(callback.data.split("_")[1])
    ticket = await escalation_system.get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден", show_alert=True)
        return
    
    if ticket.operator_id and ticket.operator_id != callback.from_user.id:
        await callback.answer(f"Уже у оператора {ticket.operator_name}", show_alert=True)
        return
    
    ticket.operator_id = callback.from_user.id
    ticket.operator_name = callback.from_user.full_name
    await escalation_system.update_ticket_status(ticket_id, TicketStatus.IN_PROGRESS)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ Вы взяли тикет #{ticket_id} в работу.")
    await callback.answer("Тикет принят!")


@router.callback_query(F.data.startswith("view_"))
async def cb_view_ticket(callback: CallbackQuery, escalation_system: EscalationSystem) -> None:
    """Просмотр деталей тикета."""
    ticket_id = int(callback.data.split("_")[1])
    ticket = await escalation_system.get_ticket_by_id(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден", show_alert=True)
        return
    
    await callback.message.answer(format_ticket_info(ticket), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("close_"))
async def cb_close_ticket(callback: CallbackQuery, escalation_system: EscalationSystem) -> None:
    """Закрытие тикета через инлайн-кнопку."""
    ticket_id = int(callback.data.split("_")[1])
    ticket = await escalation_system.update_ticket_status(ticket_id, TicketStatus.RESOLVED)
    
    if not ticket:
        await callback.answer("Тикет не найден", show_alert=True)
        return
    
    try:
        await callback.bot.send_message(
            chat_id=ticket.user_id,
            text=f"✅ Ваше обращение #{ticket_id} решено. Спасибо за обращение!"
        )
    except:
        pass
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(f"Тикет #{ticket_id} закрыт!")


@router.callback_query(F.data.startswith("reply_start_"))
async def cb_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало ввода ответа на тикет."""
    ticket_id = int(callback.data.split("_")[2])
    await state.set_state(ReplyState.waiting_for_reply)
    await state.update_data(reply_ticket_id=ticket_id)
    await callback.message.answer(f"✍️ Введите ответ для тикета #{ticket_id}:")
    await callback.answer()


@router.message(ReplyState.waiting_for_reply)
async def process_reply_text(message: Message, state: FSMContext, escalation_system: EscalationSystem) -> None:
    """Обработка текста ответа оператора."""
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    
    if not ticket_id:
        await state.clear()
        return await message.answer("❌ Ошибка: тикет не найден в контексте.")
    
    ticket = await escalation_system.get_ticket_by_id(ticket_id)
    if not ticket:
        await state.clear()
        return await message.answer("❌ Тикет не найден.")
    
    # Сохраняем ответ
    resp = TicketResponse(
        ticket_id=ticket_id,
        operator_id=message.from_user.id,
        operator_name=message.from_user.full_name,
        message=message.text
    )
    escalation_system.db.add(resp)
    
    if not ticket.operator_id:
        ticket.operator_id = message.from_user.id
        ticket.operator_name = message.from_user.full_name
    
    if ticket.status == TicketStatus.OPEN:
        await escalation_system.update_ticket_status(ticket_id, TicketStatus.IN_PROGRESS)
    else:
        await escalation_system.db.commit()
    
    # Уведомление пользователя
    try:
        await message.bot.send_message(
            chat_id=ticket.user_id,
            text=f"💬 <b>Ответ оператора по обращению #{ticket_id}:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        await message.answer("✅ Ответ отправлен пользователю!")
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление: {e}")
        await message.answer("⚠️ Ответ сохранен, но пользователь его не получит.")
    
    await state.clear()


# ============= КНОПКИ КЛАВИАТУРЫ ==============

@router.message(F.text == "📋 Активные заявки")
async def btn_active_tickets(message: Message, db: AsyncSession) -> None:
    """Кнопка активных заявок."""
    await cmd_tickets(message, db)


@router.message(F.text == "📊 Статистика")
async def btn_stats(message: Message, escalation_system: EscalationSystem) -> None:
    """Кнопка статистики."""
    await cmd_stats(message, escalation_system)


@router.message(F.text == "🔍 Поиск тикета")
async def btn_search_ticket(message: Message) -> None:
    """Подсказка по поиску."""
    await message.answer("Введите номер тикета:\n/ticket <ID>")


@router.message(F.text == "❓ Справка")
async def btn_operator_help(message: Message) -> None:
    """Кнопка справки оператора."""
    from handlers.common import cmd_help
    await cmd_help(message)


# ============= ОПЕРАТОР /start ==============

@router.message(Command("start"))
async def cmd_operator_start(message: Message) -> Message:
    """Приветствие для оператора с панелью управления."""
    return await message.answer(
        "🛠️ <b>Панель оператора поддержки</b>\n\n"
        "Добро пожаловать! Используйте клавиатуру ниже или команды:\n"
        "• /tickets — активные заявки\n"
        "• /stats — статистика линий\n"
        "• /ticket [id] — детали тикета",
        reply_markup=get_operator_keyboard(),
        parse_mode="HTML"
    )
