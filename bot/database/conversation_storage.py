"""
Персистентное хранение истории диалогов
"""
import json
import os
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConversationStorage:
    """Хранение истории диалогов пользователей"""
    
    def __init__(self, storage_type: str = "file", storage_path: Optional[str] = None):
        """
        Инициализация хранилища истории диалогов
        
        Args:
            storage_type: Тип хранилища ('file', 'database')
            storage_path: Путь к файлу или БД
        """
        self.storage_type = storage_type
        
        if storage_type == "file":
            self.storage_path = storage_path or os.getenv("CONVERSATION_STORAGE_PATH", "data/conversations.json")
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
            self._load_from_file()
        elif storage_type == "database":
            # Используем ту же БД что и для тикетов
            from .database_factory import get_database
            self.db = get_database()
            self._init_conversation_table()
        else:
            raise ValueError(f"Неизвестный тип хранилища: {storage_type}")
    
    def _load_from_file(self):
        """Загрузка истории из файла"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self._conversations: Dict[int, List[Dict]] = json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка загрузки истории диалогов: {e}")
                self._conversations = {}
        else:
            self._conversations = {}
    
    def _save_to_file(self):
        """Сохранение истории в файл"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории диалогов: {e}")
    
    def _init_conversation_table(self):
        """Инициализация таблицы для истории диалогов в БД"""
        # Это будет реализовано в конкретных реализациях БД
        pass
    
    def add_message(self, user_id: int, message: str, is_bot: bool = False, metadata: Optional[Dict] = None):
        """
        Добавить сообщение в историю диалога
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            is_bot: Является ли сообщение от бота
            metadata: Дополнительные метаданные
        """
        if self.storage_type == "file":
            if user_id not in self._conversations:
                self._conversations[user_id] = []
            
            self._conversations[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'is_bot': is_bot,
                'metadata': metadata or {}
            })
            
            # Ограничиваем размер истории (последние 50 сообщений)
            if len(self._conversations[user_id]) > 50:
                self._conversations[user_id] = self._conversations[user_id][-50:]
            
            self._save_to_file()
        else:
            # Для БД можно добавить отдельную таблицу или использовать JSON поле
            logger.debug(f"Добавление сообщения для пользователя {user_id} (БД)")
    
    def get_history(self, user_id: int, limit: int = 10) -> List[str]:
        """
        Получить историю диалога пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений
            
        Returns:
            Список сообщений (формат: "Пользователь: ..." или "Бот: ...")
        """
        if self.storage_type == "file":
            if user_id not in self._conversations:
                return []
            
            messages = self._conversations[user_id][-limit:]
            result = []
            for msg in messages:
                prefix = "Бот" if msg['is_bot'] else "Пользователь"
                result.append(f"{prefix}: {msg['message']}")
            
            return result
        else:
            # Для БД нужно реализовать запрос
            logger.debug(f"Получение истории для пользователя {user_id} (БД)")
            return []
    
    def clear_history(self, user_id: int):
        """
        Очистить историю диалога пользователя
        
        Args:
            user_id: ID пользователя
        """
        if self.storage_type == "file":
            if user_id in self._conversations:
                del self._conversations[user_id]
                self._save_to_file()
        else:
            logger.debug(f"Очистка истории для пользователя {user_id} (БД)")
    
    def get_all_conversations(self) -> Dict[int, List[Dict]]:
        """Получить все истории диалогов (для админки)"""
        if self.storage_type == "file":
            return self._conversations.copy()
        else:
            return {}
