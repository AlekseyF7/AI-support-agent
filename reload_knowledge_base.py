# -*- coding: utf-8 -*-
"""Перезагрузка базы знаний после обновления FAQ"""
import os
import shutil
from bot.rag_system import RAGSystem

print("=" * 60)
print("Перезагрузка базы знаний")
print("=" * 60)

# Путь к базе данных ChromaDB
db_path = "./chroma_db"

# Удаляем старую базу данных
if os.path.exists(db_path):
    print(f"[INFO] Удаление старой базы данных: {db_path}")
    try:
        shutil.rmtree(db_path)
        print("[OK] Старая база данных удалена")
    except Exception as e:
        print(f"[ERROR] Ошибка при удалении: {e}")
        print("[INFO] Продолжаем с существующей базой...")

# Создаем новую RAG систему и загружаем базу знаний
print("\n[INFO] Загрузка обновленной базы знаний...")
try:
    rag = RAGSystem(knowledge_base_path="knowledge_base", db_path=db_path)
    rag.load_knowledge_base()
    print("[OK] База знаний успешно перезагружена!")
    print("\n[INFO] Теперь бот будет использовать обновленные FAQ для банковской поддержки.")
except Exception as e:
    print(f"[ERROR] Ошибка при загрузке базы знаний: {e}")
    import traceback
    traceback.print_exc()

