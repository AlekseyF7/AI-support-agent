"""
Скрипт для предварительной загрузки модели эмбеддингов.
Выполняется во время сборки Docker-образа.
"""
from sentence_transformers import SentenceTransformer
import os
import sys

# Если имя передано аргументом командной строки, используем его, иначе из ENV, иначе дефолт
if len(sys.argv) > 1:
    MODEL_NAME = sys.argv[1]
else:
    MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-small")

def download():
    print(f"📥 Начинаем загрузку предобученной модели: {MODEL_NAME}...")
    try:
        # Инициализация модели вызовет её скачивание и кеширование
        model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
        print(f"✅ Модель {MODEL_NAME} успешно загружена и закеширована.")
    except Exception as e:
        print(f"❌ Ошибка при загрузке модели {MODEL_NAME}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    download()
