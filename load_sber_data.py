"""
Скрипт для загрузки распарсенных данных из JSON в базу знаний (ChromaDB)
"""

import json
import hashlib
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("LoadSberData")


def load_json_to_rag(json_path: str = "sber_data.json"):
    """
    Загружает данные из JSON файла в ChromaDB
    
    Args:
        json_path: Путь к JSON файлу с данными
    """
    from rag_system import RAGSystem
    
    # Читаем JSON
    json_file = Path(json_path)
    if not json_file.exists():
        logger.error(f"❌ Файл не найден: {json_path}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"📂 Загружено {len(data)} записей из {json_path}")
    
    # Фильтруем пустые или слишком короткие записи
    valid_data = []
    for item in data:
        title = item.get("title", "").strip()
        content = item.get("content", "").strip()
        
        # Пропускаем записи с очень коротким контентом
        if len(content) < 20:
            continue
        # Пропускаем если заголовок совпадает с контентом
        if title == content:
            continue
        
        valid_data.append(item)
    
    logger.info(f"✅ Валидных записей: {len(valid_data)}")
    
    if not valid_data:
        logger.warning("⚠️ Нет данных для загрузки")
        return
    
    # Инициализируем RAG систему
    logger.info("🧠 Инициализация RAG системы...")
    rag = RAGSystem()
    
    # Подготавливаем данные для ChromaDB
    documents = []
    metadatas = []
    ids = []
    
    for item in valid_data:
        title = item.get("title", "")
        content = item.get("content", "")
        url = item.get("url", "")
        category = item.get("category", "general")
        
        # Формируем полный текст документа
        full_text = f"{title}\n\n{content}"
        
        # Генерируем уникальный ID
        doc_id = hashlib.md5(f"{title}:{url}".encode()).hexdigest()
        
        documents.append(full_text)
        metadatas.append({
            "question": title,
            "source": url,
            "category": category
        })
        ids.append(doc_id)
    
    # Загружаем в ChromaDB
    logger.info(f"💾 Загрузка {len(documents)} документов в ChromaDB...")
    
    try:
        # Используем upsert для обновления существующих записей
        rag.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        total_count = rag.collection.count()
        logger.info(f"✨ Успешно загружено! Всего в базе знаний: {total_count} документов")
        
        # Показываем примеры загруженных данных
        logger.info("\n📋 Примеры загруженных вопросов:")
        for i, item in enumerate(valid_data[:5], 1):
            logger.info(f"   {i}. {item['title'][:70]}...")
        
        if len(valid_data) > 5:
            logger.info(f"   ... и ещё {len(valid_data) - 5} записей")
            
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки: {e}")
        raise


def test_search(query: str = "Как заблокировать карту?"):
    """Тестовый поиск по базе знаний"""
    import asyncio
    from rag_system import RAGSystem
    
    logger.info(f"\n🔍 Тестовый поиск: '{query}'")
    
    rag = RAGSystem()
    
    async def search():
        result = await rag.get_context_for_query(query, max_results=3, threshold=0.3)
        return result
    
    result = asyncio.run(search())
    
    if result:
        logger.info(f"✅ Найдено:\n{result[:500]}...")
    else:
        logger.info("❌ Ничего не найдено")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Загрузка данных в базу знаний")
    parser.add_argument(
        '--file', '-f',
        type=str,
        default='sber_data.json',
        help='Путь к JSON файлу (по умолчанию: sber_data.json)'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Выполнить тестовый поиск после загрузки'
    )
    parser.add_argument(
        '--query', '-q',
        type=str,
        default='Как заблокировать карту?',
        help='Запрос для тестового поиска'
    )
    
    args = parser.parse_args()
    
    # Загружаем данные
    load_json_to_rag(args.file)
    
    # Опциональный тест
    if args.test:
        test_search(args.query)

