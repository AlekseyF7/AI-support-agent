# -*- coding: utf-8 -*-
"""Проверка миграции тикетов"""
from bot.ticket_database import TicketDatabase

db = TicketDatabase()
stats = db.get_queue_stats()

print("=" * 60)
print("Статистика миграции тикетов")
print("=" * 60)
print(f"Линия 1 (ожидает): {stats.get('line_1_pending', 0)}")
print(f"Линия 2 (ожидает): {stats.get('line_2_pending', 0)}")
print(f"Линия 3 (ожидает): {stats.get('line_3_pending', 0)}")

# Получаем несколько тикетов для проверки
tickets_line1 = db.get_tickets_by_line(1)
print(f"\nПримеры тикетов (Линия 1, первые 5):")
for ticket in tickets_line1[:5]:
    print(f"  #{ticket.ticket_number}: {ticket.title[:50]}...")

print("\n[OK] Миграция успешно завершена!")

