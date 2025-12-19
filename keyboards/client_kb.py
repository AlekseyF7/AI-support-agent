from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import settings

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота (Reply) с прямым доступом к Mini App."""
    builder = ReplyKeyboardBuilder()
    
    # Прямая ссылка на Mini App (O2O) для Platinum UX
    webapp_url = settings.WEBAPP_URL or "http://localhost:8000"
    builder.button(text="📍 Найти отделение", web_app=WebAppInfo(url=webapp_url))
    
    builder.button(text="📞 Позвать оператора")
    builder.button(text="📂 Мои заявки")
    builder.button(text="❓ Помощь")
    
    builder.adjust(1, 2, 1)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Опишите вашу проблему...")

def get_operator_actions(ticket_id: int) -> InlineKeyboardMarkup:
    """Инлайн-кнопки для быстрых действий оператора (опционально)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Решено", callback_data=f"close_{ticket_id}")
    builder.button(text="📝 Ответить", callback_data=f"reply_hint_{ticket_id}")
    return builder.as_markup()
