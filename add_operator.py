"""Скрипт для добавления оператора по ID"""
import os
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def add_operator(operator_id: str):
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ Файл .env не найден!")
        sys.exit(1)
    
    # Читаем текущий файл
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = []
    updated = False
    
    for line in content.split('\n'):
        if line.startswith('OPERATOR_IDS='):
            current_ids = line.split('=', 1)[1].strip()
            
            # Проверяем, не добавлен ли уже этот ID
            if current_ids:
                id_list = [oid.strip() for oid in current_ids.split(',') if oid.strip()]
                if operator_id in id_list:
                    print(f"✅ ID {operator_id} уже добавлен в список операторов.")
                    print(f"Текущие операторы: {current_ids}")
                    return
                # Добавляем новый ID
                new_ids = f"{current_ids},{operator_id}"
            else:
                new_ids = operator_id
            
            lines.append(f'OPERATOR_IDS={new_ids}')
            updated = True
        else:
            lines.append(line)
    
    # Если переменная не найдена, добавляем её
    if not updated:
        # Ищем место для вставки после других настроек
        insert_pos = len(lines)
        for i, line in enumerate(lines):
            if line.startswith('# Operator Settings'):
                insert_pos = i + 1
                break
            if line.strip() == "" and i > 0:
                # Проверяем, не комментарий ли предыдущая строка
                prev_line = lines[i-1].strip()
                if prev_line.startswith('#'):
                    insert_pos = i
                    break
        
        lines.insert(insert_pos, f'OPERATOR_IDS={operator_id}')
    
    # Записываем обратно
    with open(env_file, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    
    # Читаем обновленный файл для показа результата
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Находим OPERATOR_IDS для показа
    operator_ids_line = None
    for line in content.split('\n'):
        if line.startswith('OPERATOR_IDS='):
            operator_ids_line = line.split('=', 1)[1].strip()
            break
    
    print("=" * 60)
    print("✅ Оператор успешно добавлен!")
    print("=" * 60)
    print(f"\nTelegram ID: {operator_id}")
    print(f"Username: @I_cant_be_broken")
    print(f"\nТекущие операторы: {operator_ids_line or 'не найдено'}")
    print("\n" + "=" * 60)
    print("⚠️ ВАЖНО: Перезапустите бота для применения изменений!")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        operator_id = sys.argv[1]
    else:
        # Используем ID из сообщения пользователя
        operator_id = "1717959380"
    
    try:
        add_operator(operator_id)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

