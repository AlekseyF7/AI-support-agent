"""Скрипт для обновления токена Telegram"""
import re

# Читаем файл
with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем токен
new_token = '8320220590:AAEM77vO-EREFsdQEnk1Tbpocim9cxvI1lE'
content = re.sub(
    r'TELEGRAM_BOT_TOKEN=.*',
    f'TELEGRAM_BOT_TOKEN={new_token}',
    content
)

# Записываем обратно
with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

print('Токен Telegram обновлен успешно!')
print(f'Новый токен: {new_token[:15]}...')

