"""Команды для операторов поддержки"""
from models import Ticket, TicketStatus, SupportLine, TicketResponse, SessionLocal
from typing import Optional, List
from datetime import datetime
import json
from telegram import Update
from telegram.ext import ContextTypes


def is_operator(user_id: int, operator_ids: str) -> bool:
    """Проверка, является ли пользователь оператором"""
    if not operator_ids:
        return False
    operator_list = [int(oid.strip()) for oid in operator_ids.split(',') if oid.strip().isdigit()]
    return user_id in operator_list


def format_ticket_info(ticket: Ticket) -> str:
    """Форматирование информации о тикете для вывода"""
    status_emoji = {
        TicketStatus.OPEN: "🟢",
        TicketStatus.IN_PROGRESS: "🟡",
        TicketStatus.ESCALATED: "🔴",
        TicketStatus.RESOLVED: "✅",
        TicketStatus.CLOSED: "⚫"
    }
    
    emoji = status_emoji.get(ticket.status, "⚪")
    
    operator_info = ""
    if ticket.operator_id:
        operator_info = f"\n👤 Оператор: {ticket.operator_name or f'ID:{ticket.operator_id}'}"
    
    return f"""
{emoji} Тикет #{ticket.id}

📋 Заголовок: {ticket.title}
👤 Пользователь: {ticket.user_name} (ID: {ticket.user_id})
📂 Категория: {ticket.category.value}
⚠️ Критичность: {ticket.criticality.value}
📞 Линия: {ticket.support_line.value}
📝 Статус: {ticket.status.value}{operator_info}

📄 Описание:
{ticket.description}

🕒 Создан: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}
🕒 Обновлен: {ticket.updated_at.strftime('%d.%m.%Y %H:%M')}
"""


async def cmd_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE, operator_ids: str):
    """Команда /tickets - просмотр всех открытых тикетов"""
    user_id = update.effective_user.id
    
    if not is_operator(user_id, operator_ids):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    db = SessionLocal()
    try:
        # Получаем все открытые тикеты
        open_tickets = db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        ).order_by(Ticket.created_at.desc()).all()
        
        if not open_tickets:
            await update.message.reply_text("✅ Нет открытых тикетов.")
            return
        
        message = f"📋 Открытые тикеты ({len(open_tickets)}):\n\n"
        
        for ticket in open_tickets[:10]:  # Показываем первые 10
            status_emoji = "🟢" if ticket.status == TicketStatus.OPEN else "🟡"
            message += f"{status_emoji} #{ticket.id} - {ticket.title[:50]}...\n"
            message += f"   Пользователь: {ticket.user_name} | Линия: {ticket.support_line.value}\n\n"
        
        if len(open_tickets) > 10:
            message += f"\n... и еще {len(open_tickets) - 10} тикетов"
        
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении тикетов: {str(e)}")
    finally:
        db.close()


async def cmd_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, operator_ids: str):
    """Команда /ticket <id> - просмотр конкретного тикета"""
    user_id = update.effective_user.id
    
    if not is_operator(user_id, operator_ids):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("❌ Укажите ID тикета: /ticket <id>")
        return
    
    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Неверный ID тикета. Используйте число.")
        return
    
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден.")
            return
        
        # Получаем историю ответов
        responses = db.query(TicketResponse).filter(
            TicketResponse.ticket_id == ticket_id
        ).order_by(TicketResponse.created_at).all()
        
        message = format_ticket_info(ticket)
        
        if responses:
            message += "\n\n💬 Ответы операторов:\n"
            for resp in responses:
                message += f"\n👤 {resp.operator_name or f'ID:{resp.operator_id}'} ({resp.created_at.strftime('%d.%m %H:%M')}):\n"
                message += f"{resp.message}\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def cmd_take(update: Update, context: ContextTypes.DEFAULT_TYPE, operator_ids: str):
    """Команда /take <id> - взять тикет в работу"""
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or update.effective_user.username or "Unknown"
    
    if not is_operator(user_id, operator_ids):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("❌ Укажите ID тикета: /take <id>")
        return
    
    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Неверный ID тикета. Используйте число.")
        return
    
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден.")
            return
        
        if ticket.status == TicketStatus.CLOSED:
            await update.message.reply_text(f"❌ Тикет #{ticket_id} уже закрыт.")
            return
        
        if ticket.operator_id and ticket.operator_id != user_id:
            await update.message.reply_text(
                f"⚠️ Тикет #{ticket_id} уже взят в работу другим оператором (ID: {ticket.operator_id})"
            )
            return
        
        # Берем тикет в работу
        ticket.operator_id = user_id
        ticket.operator_name = user_name
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        await update.message.reply_text(
            f"✅ Тикет #{ticket_id} взят в работу.\n"
            f"Используйте /reply <id> <сообщение> для ответа пользователю."
        )
    except Exception as e:
        db.rollback()
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, operator_ids: str, bot):
    """Команда /reply <id> <сообщение> - ответить пользователю"""
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name or update.effective_user.username or "Unknown"
    
    if not is_operator(user_id, operator_ids):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("❌ Используйте: /reply <id> <сообщение>")
        return
    
    try:
        ticket_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❌ Неверный ID тикета. Используйте число.")
        return
    
    if not message_text:
        await update.message.reply_text("❌ Сообщение не может быть пустым.")
        return
    
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден.")
            return
        
        # Создаем запись ответа
        response = TicketResponse(
            ticket_id=ticket_id,
            operator_id=user_id,
            operator_name=user_name,
            message=message_text
        )
        db.add(response)
        
        # Обновляем статус тикета, если он еще не взят в работу
        if not ticket.operator_id:
            ticket.operator_id = user_id
            ticket.operator_name = user_name
        
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Отправляем сообщение пользователю
        try:
            user_message = f"💬 Ответ от оператора по тикету #{ticket_id}:\n\n{message_text}"
            await bot.send_message(chat_id=ticket.user_id, text=user_message)
            
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю по тикету #{ticket_id}"
            )
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Ответ сохранен, но не удалось отправить пользователю: {str(e)}"
            )
            
    except Exception as e:
        db.rollback()
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def cmd_close(update: Update, context: ContextTypes.DEFAULT_TYPE, operator_ids: str):
    """Команда /close <id> - закрыть тикет"""
    user_id = update.effective_user.id
    
    if not is_operator(user_id, operator_ids):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text("❌ Укажите ID тикета: /close <id>")
        return
    
    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Неверный ID тикета. Используйте число.")
        return
    
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            await update.message.reply_text(f"❌ Тикет #{ticket_id} не найден.")
            return
        
        ticket.status = TicketStatus.RESOLVED
        ticket.resolved_at = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=ticket.user_id,
                text=f"✅ Тикет #{ticket_id} закрыт. Спасибо за обращение!"
            )
        except:
            pass  # Игнорируем ошибки отправки
        
        await update.message.reply_text(f"✅ Тикет #{ticket_id} закрыт.")
    except Exception as e:
        db.rollback()
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, operator_ids: str):
    """Команда /stats - статистика по тикетам"""
    user_id = update.effective_user.id
    
    if not is_operator(user_id, operator_ids):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    db = SessionLocal()
    try:
        stats_message = "📊 Статистика по тикетам:\n\n"
        
        for status in TicketStatus:
            count = db.query(Ticket).filter(Ticket.status == status).count()
            emoji = {
                TicketStatus.OPEN: "🟢",
                TicketStatus.IN_PROGRESS: "🟡",
                TicketStatus.ESCALATED: "🔴",
                TicketStatus.RESOLVED: "✅",
                TicketStatus.CLOSED: "⚫"
            }.get(status, "⚪")
            
            stats_message += f"{emoji} {status.value}: {count}\n"
        
        stats_message += "\n📞 По линиям поддержки:\n"
        
        for line in SupportLine:
            open_count = db.query(Ticket).filter(
                Ticket.support_line == line,
                Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
            ).count()
            
            stats_message += f"   {line.value}: {open_count} открытых\n"
        
        await update.message.reply_text(stats_message)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

