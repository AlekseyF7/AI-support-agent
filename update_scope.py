"""Скрипт для обновления Scope (ID пространства) в .env файле"""
import os
import sys
import io

# Настройка кодировки для Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def update_scope():
    env_file = ".env"
    
    # ID пространства (Workspace ID) - НЕ используется для scope
    # Scope должен быть стандартным: GIGACHAT_API_PERS, GIGACHAT_API_B2B, GIGACHAT_API_CORP
    workspace_id = "PLS-019aba56-cdcb-7432-9303-168828c1ec84"
    scope = "GIGACHAT_API_PERS"  # Стандартный scope для получения токена
    
    if not os.path.exists(env_file):
        print("Файл .env не найден. Создайте его сначала!")
        sys.exit(1)
    
    # Читаем текущий файл
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Обновляем значения
    lines = []
    updated_scope = False
    updated_workspace_id = False
    
    for line in content.split('\n'):
        if line.startswith('GIGACHAT_SCOPE='):
            lines.append(f'GIGACHAT_SCOPE={scope}')
            updated_scope = True
        elif line.startswith('GIGACHAT_WORKSPACE_ID='):
            lines.append(f'GIGACHAT_WORKSPACE_ID={workspace_id}')
            updated_workspace_id = True
        else:
            lines.append(line)
    
    # Если переменная scope не найдена, добавляем её
    if not updated_scope:
        insert_pos = -1
        for i, line in enumerate(lines):
            if line.startswith('GIGACHAT_AUTHORIZATION_KEY=') or line.startswith('GIGACHAT_CLIENT_SECRET='):
                insert_pos = i
                break
        if insert_pos >= 0:
            lines.insert(insert_pos + 1, f'GIGACHAT_SCOPE={scope}')
        else:
            # Ищем место после других GIGACHAT_ переменных
            for i, line in enumerate(lines):
                if line.startswith('GIGACHAT_'):
                    insert_pos = i
                    break
            if insert_pos >= 0:
                lines.insert(insert_pos + 1, f'GIGACHAT_SCOPE={scope}')
            else:
                lines.append(f'GIGACHAT_SCOPE={scope}')
    
    # Если переменная workspace_id не найдена, добавляем её после scope
    if not updated_workspace_id:
        insert_pos = -1
        for i, line in enumerate(lines):
            if line.startswith('GIGACHAT_SCOPE='):
                insert_pos = i
                break
        if insert_pos >= 0:
            lines.insert(insert_pos + 1, f'GIGACHAT_WORKSPACE_ID={workspace_id}')
        else:
            lines.append(f'GIGACHAT_WORKSPACE_ID={workspace_id}')
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    
    print("Файл .env обновлен!")
    
    # Показываем текущее состояние
    print("\nОбновленные настройки GigaChat в .env:")
    print("-" * 60)
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and 'GIGACHAT' in line:
                key, value = line.split('=', 1)
                if 'AUTHORIZATION_KEY' in key:
                    masked = value[:30] + "..." if len(value) > 30 else value
                    print(f"[OK] {key}={masked}")
                elif 'SCOPE' in key or 'WORKSPACE' in key:
                    print(f"[OK] {key}={value}")
                else:
                    masked = value[:15] + "..." if len(value) > 15 else value
                    print(f"[OK] {key}={masked}")
    print("-" * 60)
    print(f"\n✅ Scope (ID пространства) успешно обновлен: {scope}")

if __name__ == "__main__":
    try:
        update_scope()
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

