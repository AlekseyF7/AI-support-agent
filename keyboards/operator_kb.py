"""Клавиатуры для оператора службы поддержки."""
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_operator_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура для оператора техподдержки."""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="📋 Активные заявки")
    builder.button(text="📊 Статистика")
    builder.button(text="🔍 Поиск тикета")
    builder.button(text="❓ Справка")
    
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Введите команду или ID тикета...")


def get_ticket_actions(ticket_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки для быстрых действий с тикетом."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👁️ Подробнее", callback_data=f"view_{ticket_id}")
    builder.button(text="✋ Взять в работу", callback_data=f"take_{ticket_id}")
    builder.button(text="💬 Ответить", callback_data=f"reply_start_{ticket_id}")
    builder.button(text="✅ Закрыть", callback_data=f"close_{ticket_id}")
    
    builder.adjust(2, 2)
    return builder.as_markup()


def get_line_filter_keyboard() -> InlineKeyboardMarkup:
    """Фильтр по линиям поддержки."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="1️⃣ Линия 1", callback_data="filter_line_1")
    builder.button(text="2️⃣ Линия 2", callback_data="filter_line_2")
    builder.button(text="3️⃣ Линия 3", callback_data="filter_line_3")
    builder.button(text="🔄 Все", callback_data="filter_all")
    
    builder.adjust(3, 1)
    return builder.as_markup()


def get_priority_filter_keyboard() -> InlineKeyboardMarkup:
    """Фильтр по приоритету."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🔴 Критический", callback_data="priority_critical")
    builder.button(text="🟠 Высокий", callback_data="priority_high")
    builder.button(text="🟡 Средний", callback_data="priority_medium")
    builder.button(text="🟢 Низкий", callback_data="priority_low")
    
    builder.adjust(2, 2)
    return builder.as_markup()
