"""
Скрипт миграции тикетов из JSON в SQLite (PB6)
"""
import json
import os
from datetime import datetime
from pathlib import Path

from bot.ticket_database import TicketDatabase
from bot.ticket_models import Ticket, TicketClassification, TicketType, TicketPriority, TicketStatus


def migrate_tickets(json_path: str = "data/tickets.json", db_path: str = "data/tickets.db"):
    """
    Переносит тикеты из JSON в SQLite
    
    Args:
        json_path: Путь к JSON файлу с тикетами
        db_path: Путь к SQLite базе данных
    """
    print("=" * 60)
    print("Миграция тикетов из JSON в SQLite")
    print("=" * 60)
    
    # Проверяем существование JSON файла
    if not os.path.exists(json_path):
        print(f"[ERROR] Файл {json_path} не найден. Миграция не требуется.")
        return
    
    # Загружаем тикеты из JSON
    print(f"\n[INFO] Загрузка тикетов из {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tickets_json = data.get("tickets", [])
    except Exception as e:
        print(f"[ERROR] Ошибка при чтении JSON: {e}")
        return
    
    if not tickets_json:
        print("[INFO] В JSON файле нет тикетов. Миграция не требуется.")
        return
    
    print(f"[OK] Найдено тикетов: {len(tickets_json)}")
    
    # Инициализируем БД
    print(f"\n[INFO] Инициализация базы данных {db_path}...")
    db = TicketDatabase(db_path)
    
    # Проверяем, есть ли уже тикеты в БД
    existing_tickets = db.get_tickets_by_line(1)  # Получаем все тикеты через любую линию
    if existing_tickets:
        print(f"[WARNING] В базе данных уже есть {len(existing_tickets)} тикетов.")
        print("[INFO] Продолжаем миграцию (тикеты будут добавлены с новыми ID)...")
    
    # Мигрируем тикеты
    print(f"\n[INFO] Начало миграции...")
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for ticket_json in tickets_json:
        try:
            # Преобразуем JSON тикет в объект Ticket
            ticket = json_to_ticket(ticket_json)
            
            # Сохраняем в БД
            db.create_ticket(ticket)
            migrated_count += 1
            
            if migrated_count % 10 == 0:
                print(f"  [PROGRESS] Мигрировано: {migrated_count}/{len(tickets_json)}")
        
        except Exception as e:
            error_count += 1
            print(f"  [ERROR] Ошибка при миграции тикета #{ticket_json.get('id', 'unknown')}: {e}")
            skipped_count += 1
    
    # Итоги
    print("\n" + "=" * 60)
    print("[SUMMARY] Итоги миграции:")
    print(f"  [OK] Успешно мигрировано: {migrated_count}")
    print(f"  [SKIP] Пропущено: {skipped_count}")
    print(f"  [ERROR] Ошибок: {error_count}")
    print("=" * 60)
    
    if migrated_count > 0:
        # Показываем статистику
        stats = db.get_queue_stats()
        print("\n[STATS] Статистика очередей:")
        print(f"  Линия 1 (ожидает): {stats.get('line_1_pending', 0)}")
        print(f"  Линия 2 (ожидает): {stats.get('line_2_pending', 0)}")
        print(f"  Линия 3 (ожидает): {stats.get('line_3_pending', 0)}")
        
        # Создаем резервную копию автоматически
        backup_path = f"{json_path}.backup"
        try:
            import shutil
            if not os.path.exists(backup_path):
                shutil.copy2(json_path, backup_path)
                print(f"[OK] Резервная копия создана: {backup_path}")
            else:
                print(f"[INFO] Резервная копия уже существует: {backup_path}")
        except Exception as e:
            print(f"[WARNING] Не удалось создать резервную копию: {e}")


def json_to_ticket(ticket_json: dict) -> Ticket:
    """
    Преобразует тикет из JSON формата в объект Ticket
    
    Args:
        ticket_json: Словарь с данными тикета из JSON
        
    Returns:
        Объект Ticket
    """
    # Преобразуем приоритет
    priority_str = ticket_json.get("priority", "P3")
    priority_map = {
        "P1": TicketPriority.CRITICAL,
        "P2": TicketPriority.HIGH,
        "P3": TicketPriority.MEDIUM,
        "P4": TicketPriority.LOW
    }
    priority = priority_map.get(priority_str, TicketPriority.MEDIUM)
    
    # Определяем тип обращения (по умолчанию консультация)
    # Можно попытаться определить по описанию
    description = ticket_json.get("description", "").lower()
    if any(word in description for word in ["не работает", "ошибка", "не могу", "не получается", "сбой"]):
        ticket_type = TicketType.INCIDENT
    else:
        ticket_type = TicketType.CONSULTATION
    
    # Создаем классификацию
    classification = TicketClassification(
        theme=ticket_json.get("theme", "Техническая проблема"),
        ticket_type=ticket_type,
        priority=priority,
        system_service=None,  # В старых тикетах этого поля нет
        reasoning=ticket_json.get("reasoning", "Мигрировано из JSON")
    )
    
    # Преобразуем статус
    status_str = ticket_json.get("status", "Новое")
    status_map = {
        "Новое": TicketStatus.NEW,
        "В работе": TicketStatus.IN_PROGRESS,
        "Ожидание ответа пользователя": TicketStatus.WAITING_FOR_USER,
        "Решено": TicketStatus.RESOLVED,
        "Закрыто": TicketStatus.CLOSED,
        "Эскалировано": TicketStatus.ESCALATED
    }
    status = status_map.get(status_str, TicketStatus.NEW)
    
    # Преобразуем даты
    created_at_str = ticket_json.get("created_at")
    if isinstance(created_at_str, str):
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except:
            created_at = datetime.now()
    else:
        created_at = datetime.now()
    
    updated_at = created_at  # По умолчанию
    resolved_at = None
    if ticket_json.get("resolved_at"):
        resolved_at_str = ticket_json.get("resolved_at")
        if isinstance(resolved_at_str, str):
            try:
                resolved_at = datetime.fromisoformat(resolved_at_str)
            except:
                resolved_at = None
    
    # Генерируем заголовок
    description_text = ticket_json.get("description", "")
    title = description_text[:100] if len(description_text) > 100 else description_text
    
    # Форматируем историю диалога
    conversation_history = ticket_json.get("conversation_history", [])
    if conversation_history and isinstance(conversation_history, list):
        # Если история уже отформатирована, оставляем как есть
        # Если нет - форматируем
        formatted_history = []
        for i, msg in enumerate(conversation_history):
            if isinstance(msg, str):
                if not msg.startswith(("Пользователь:", "Бот:")):
                    # Определяем, кто говорит (чередуем)
                    prefix = "Пользователь:" if i % 2 == 0 else "Бот:"
                    formatted_history.append(f"{prefix} {msg}")
                else:
                    formatted_history.append(msg)
    else:
        formatted_history = []
    
    # Создаем объект Ticket
    ticket = Ticket(
        id=0,  # Будет установлен БД
        ticket_number="",  # Будет сгенерирован БД
        user_id=ticket_json.get("user_id", 0),
        username=ticket_json.get("username", "unknown"),
        title=title,
        description=description_text,
        classification=classification,
        support_line=ticket_json.get("support_line", 1),
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        rag_answer=ticket_json.get("rag_answer"),
        conversation_history=formatted_history,
        resolved=ticket_json.get("resolved", False),
        resolution=ticket_json.get("resolution"),
        resolved_at=resolved_at
    )
    
    return ticket


if __name__ == "__main__":
    print("[START] Запуск миграции тикетов...")
    migrate_tickets()
    print("\n[OK] Миграция завершена!")

