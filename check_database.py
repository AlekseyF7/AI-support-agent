"""Проверка структуры базы данных"""
import sqlite3

conn = sqlite3.connect('support.db')
cursor = conn.cursor()

print("=" * 60)
print("Проверка структуры базы данных")
print("=" * 60)

# Проверяем таблицу tickets
cursor.execute("PRAGMA table_info(tickets)")
cols = [row[1] for row in cursor.fetchall()]
print(f"\nКолонки в таблице tickets: {len(cols)}")
for col in cols:
    print(f"  - {col}")

has_op_id = 'operator_id' in cols
has_op_name = 'operator_name' in cols

if has_op_id and has_op_name:
    print("\n✅ Колонки operator_id и operator_name присутствуют")
else:
    print(f"\n❌ Отсутствуют: operator_id={has_op_id}, operator_name={has_op_name}")

# Проверяем таблицу ticket_responses
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_responses'")
result = cursor.fetchone()

if result:
    print("✅ Таблица ticket_responses существует")
    cursor.execute("PRAGMA table_info(ticket_responses)")
    resp_cols = [row[1] for row in cursor.fetchall()]
    print(f"  Колонки: {', '.join(resp_cols)}")
else:
    print("❌ Таблица ticket_responses не найдена")

conn.close()
print("\n" + "=" * 60)

