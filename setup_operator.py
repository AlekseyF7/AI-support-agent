"""Скрипт для настройки операторов в .env файле"""
import os
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def setup_operator():
    env_file = ".env"
    
    print("Настройка операторов для бота поддержки")
    print("=" * 60)
    print("\nДля получения вашего Telegram ID:")
    print("1. Напишите боту @userinfobot в Telegram")
    print("2. Скопируйте ваш ID (число)")
    print("3. Введите ID операторов через запятую (например: 123456789,987654321)")
    print("\nИли нажмите Enter, чтобы пропустить настройку.")
    print("-" * 60)
    
    operator_ids = input("\nВведите ID операторов: ").strip()
    
    if not os.path.exists(env_file):
        print("Файл .env не найден. Создайте его сначала!")
        sys.exit(1)
    
    # Читаем текущий файл
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Обновляем значения
    lines = []
    updated = False
    
    for line in content.split('\n'):
        if line.startswith('OPERATOR_IDS='):
            if operator_ids:
                lines.append(f'OPERATOR_IDS={operator_ids}')
                updated = True
            else:
                # Если пусто, пропускаем строку (удаляем)
                updated = True
                continue
        else:
            lines.append(line)
    
    # Если переменная не найдена и есть значение, добавляем её
    if not updated and operator_ids:
        # Ищем место после других настроек
        insert_pos = len(lines) - 1
        for i, line in enumerate(lines):
            if line.startswith('# Operator Settings') or line.startswith('OPERATOR_IDS='):
                insert_pos = i
                break
            if line.strip() == "" and i > 0 and lines[i-1].strip().startswith('#'):
                insert_pos = i
                break
        
        lines.insert(insert_pos, f'OPERATOR_IDS={operator_ids}')
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    
    if operator_ids:
        print("\n✅ ID операторов успешно обновлены!")
        print(f"Операторы: {operator_ids}")
    else:
        print("\n✅ Операторы не настроены. Бот будет работать только для пользователей.")
    
    print("\nДоступные команды для операторов:")
    print("- /tickets - список открытых тикетов")
    print("- /ticket <id> - просмотр конкретного тикета")
    print("- /take <id> - взять тикет в работу")
    print("- /reply <id> <сообщение> - ответить пользователю")
    print("- /close <id> - закрыть тикет")
    print("- /stats - статистика по тикетам")

if __name__ == "__main__":
    try:
        setup_operator()
    except KeyboardInterrupt:
        print("\n\nОперация отменена.")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

