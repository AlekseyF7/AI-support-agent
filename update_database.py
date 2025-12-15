"""Скрипт для обновления схемы базы данных"""
import sqlite3
import os
import sys

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'buffer'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        except:
            pass

try:
    from config import settings
except:
    print("Ошибка импорта config")
    sys.exit(1)

def update_database():
    """Обновление схемы базы данных - добавление новых колонок"""
    
    # Получаем путь к БД из DATABASE_URL
    db_path = settings.DATABASE_URL.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        print("Создаю новую базу данных...")
        from models import init_db
        init_db()
        print("✅ База данных создана!")
        return
    
    print(f"Подключение к базе данных: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие колонки в таблице tickets
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Текущие колонки: {', '.join(columns)}")
        
        updates_made = False
        
        # Добавляем operator_id, если его нет
        if 'operator_id' not in columns:
            print("Добавление колонки operator_id...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN operator_id INTEGER")
            updates_made = True
            print("✅ Колонка operator_id добавлена")
        
        # Добавляем operator_name, если его нет
        if 'operator_name' not in columns:
            print("Добавление колонки operator_name...")
            cursor.execute("ALTER TABLE tickets ADD COLUMN operator_name VARCHAR(255)")
            updates_made = True
            print("✅ Колонка operator_name добавлена")
        
        # Проверяем, существует ли таблица ticket_responses
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_responses'")
        if not cursor.fetchone():
            print("Создание таблицы ticket_responses...")
            cursor.execute("""
                CREATE TABLE ticket_responses (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    operator_id INTEGER NOT NULL,
                    operator_name VARCHAR(255),
                    message TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
                )
            """)
            cursor.execute("CREATE INDEX ix_ticket_responses_ticket_id ON ticket_responses (ticket_id)")
            updates_made = True
            print("✅ Таблица ticket_responses создана")
        
        conn.commit()
        
        if updates_made:
            print("\n" + "=" * 60)
            print("✅ База данных успешно обновлена!")
            print("=" * 60)
        else:
            print("\n✅ База данных уже актуальна, обновлений не требуется.")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ Ошибка при обновлении базы данных: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        update_database()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

