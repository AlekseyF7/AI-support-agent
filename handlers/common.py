"""Общие хендлеры (Справка, приветствие)."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.client_kb import get_main_keyboard
from config import settings

router = Router()

def is_operator(user_id: int) -> bool:
    """Централизованная проверка прав оператора."""
    return user_id in settings.operator_list

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам."""
    text = (
        "🤖 <b>Справка по боту службы поддержки</b>\n\n"
        "Я помогу вам решить вопросы по продуктам Сбера.\n\n"
        "🔹 <b>Текст:</b> Просто напишите свой вопрос.\n"
        "🔹 <b>Голос:</b> Отправьте голосовое сообщение для распознавания.\n"
        "🔹 <b>Фото:</b> Скриншот ошибки поможет мне понять проблему.\n"
        "🔹 <b>📍 Локация:</b> Нажмите кнопку в меню, чтобы найти ближайший офис.\n\n"
        "Если я не смогу ответить, ваш запрос будет передан оператору."
    )
    
    reply_markup = get_main_keyboard()
    
    if is_operator(message.from_user.id):
        text += (
            "\n\n🛠 <b>Команды оператора:</b>\n"
            "• /tickets - список активных заявок\n"
            "• /ticket [id] - детали обращения\n"
            "• /take [id] - взять в работу\n"
            "• /reply [id] [текст] - ответить пользователю\n"
            "• /close [id] - закрыть обращение\n"
            "• /stats - статистика нагрузки"
        )
        from keyboards.operator_kb import get_operator_keyboard
        reply_markup = get_operator_keyboard()
        
    await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    """Помощь через встроенную кнопку."""
    # Переиспользуем логику сообщения
    await cmd_help(callback.message)
    await callback.answer()

@router.message(F.text == "❓ Помощь")
async def text_help(message: Message):
    """Обработка кнопки с клавиатуры."""
    await cmd_help(message)
