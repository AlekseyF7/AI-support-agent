""" 
Система интеллектуальной маршрутизации и эскалации обращений.
Реализует семантическое группирование похожих тикетов для снижения нагрузки на операторов.
"""
import logging
import json
import asyncio
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import Ticket, SupportLine, TicketStatus, Criticality, Category, TicketResponse

logger = logging.getLogger(__name__)

class EscalationSystem:
    """
    Бизнес-логика управления жизненным циклом обращений.
    
    Attributes:
        db (AsyncSession): Сессия SQLAlchemy.
        chroma_client: Клиент векторной БД ChromaDB (опционально).
        embedding_func: Функция для генерации эмбеддингов (опционально).
    """
    
    def __init__(self, db: AsyncSession, chroma_client=None, embedding_func=None):
        self.db = db
        self.chroma_client = chroma_client
        self.embedding_func = embedding_func
        self.collection = None
        
        if self.chroma_client and self.embedding_func:
            try:
                self.collection = self.chroma_client.get_or_create_collection(
                    name="active_tickets_vectors",
                    embedding_function=self.embedding_func
                )
            except Exception as e:
                logger.error(f"❌ Критическая ошибка при инициализации ChromaDB коллекции: {e}")

    async def find_similar_open_ticket(self, text: str, threshold: float = 0.4) -> Optional[Ticket]:
        """
        Ищет открытое обращение с похожим смыслом запроса.
        
        Args:
            text: Текст нового запроса.
            threshold: Порог схожести (L2-дистанция в ChromaDB). 0.0 - идентично.
            
        Returns:
            Объект Ticket, если найдено совпадение, иначе None.
        """
        if not self.collection:
            return None
            
        try:
            loop = asyncio.get_running_loop()
            # Модель ожидает префикс 'query: ' для оптимального поиска
            query_text = f"query: {text}"
            
            results = await loop.run_in_executor(
                None, 
                lambda: self.collection.query(
                    query_texts=[query_text], 
                    n_results=1,
                    where={"status": "open"} 
                )
            )
            
            if results['ids'] and results['ids'][0]:
                distance = results['distances'][0][0]
                if distance < threshold:
                    ticket_id = int(results['ids'][0][0])
                    logger.info(f"🔍 Семантическое совпадение: тикет #{ticket_id} (distance: {distance:.4f})")
                    return await self.get_ticket_by_id(ticket_id)
            
            return None
        except Exception as e:
            logger.error(f"⚠️ Ошибка семантического поиска тикетов: {e}")
            return None

    async def create_ticket(
        self,
        title: str,
        description: str,
        user_id: int,
        user_name: str,
        category: Category,
        criticality: Criticality,
        support_line: SupportLine,
        conversation_history: Optional[List[dict]] = None,
        allow_grouping: bool = True
    ) -> Tuple[Ticket, bool]:
        """
        Регистрирует новое обращение в системе. Выполняет дедупликацию запросов.
        
        Returns:
            Tuple[Ticket, bool]: Объект тикета и флаг, является ли он новым (True/False).
        """
        if allow_grouping:
            similar_ticket = await self.find_similar_open_ticket(description)
            if similar_ticket:
                # Добавляем системный ответ-уведомление в существующий тикет
                resp = TicketResponse(
                    ticket_id=similar_ticket.id,
                    operator_id=0,
                    operator_name="System (Deduplication)",
                    message=f"📢 Повторное обращение от пользователя {user_name} (ID: {user_id}).\n"
                            f"Текст запроса синхронизирован: {description}"
                )
                self.db.add(resp)
                similar_ticket.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
                return similar_ticket, False

        try:
            history_json = json.dumps(conversation_history or [], ensure_ascii=False)
            
            ticket = Ticket(
                title=title[:255],
                description=description,
                user_id=user_id,
                user_name=user_name,
                category=category,
                criticality=criticality,
                support_line=support_line,
                status=TicketStatus.OPEN,
                conversation_history=history_json
            )
            
            self.db.add(ticket)
            await self.db.commit()
            await self.db.refresh(ticket)
            
            # Регистрация вектора в ChromaDB для будущего поиска
            if self.collection:
                loop = asyncio.get_running_loop()
                # Для документов используем префикс 'passage: ' (опционально, зависит от конфига LocalEmbeddingFunction)
                await loop.run_in_executor(
                    None,
                    lambda: self.collection.add(
                        ids=[str(ticket.id)],
                        documents=[description],
                        metadatas=[{"status": "open", "user_id": user_id}]
                    )
                )
            
            logger.info("✅ Создан тикет #%s. Линия: %s, Приоритет: %s", 
                        ticket.id, support_line.value, criticality.value)
            return ticket, True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Ошибка создания тикета: {e}")
            raise

    async def update_ticket_status(self, ticket_id: int, status: TicketStatus) -> Optional[Ticket]:
        """Обновляет статус тикета и синхронизирует состояние в векторной БД."""
        try:
            ticket = await self.get_ticket_by_id(ticket_id)
            if not ticket:
                return None
            
            ticket.status = status
            ticket.updated_at = datetime.now(timezone.utc)
            
            if status == TicketStatus.RESOLVED:
                ticket.resolved_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            if self.collection:
                loop = asyncio.get_running_loop()
                if status in [TicketStatus.CLOSED, TicketStatus.RESOLVED]:
                    # Удаляем из активной выборки для дедупликации
                    await loop.run_in_executor(
                        None, lambda: self.collection.delete(ids=[str(ticket_id)])
                    )
                else:
                    await loop.run_in_executor(
                        None, 
                        lambda: self.collection.update(
                            ids=[str(ticket_id)], 
                            metadatas=[{"status": status.value, "user_id": ticket.user_id}]
                        )
                    )
            
            await self.db.refresh(ticket)
            logger.info("🔄 Статус тикета #%s изменен на %s", ticket_id, status.value)
            return ticket
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Ошибка обновления статуса тикета #%s: {e}", ticket_id)
            raise

    async def get_tickets_by_line(self, support_line: SupportLine, status: TicketStatus = None) -> List[Ticket]:
        """Получает список тикетов для конкретной линии поддержки."""
        stmt = select(Ticket).where(Ticket.support_line == support_line)
        if status:
            stmt = stmt.where(Ticket.status == status)
        
        result = await self.db.execute(stmt.order_by(Ticket.created_at.desc()))
        return list(result.scalars().all())
    
    async def get_user_tickets(self, user_id: int) -> List[Ticket]:
        """Получает все обращения конкретного пользователя."""
        stmt = select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Получает тикет по его первичному ключу."""
        return await self.db.get(Ticket, ticket_id)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Формирует статистику загруженности линий поддержки."""
        stats = {}
        for line in SupportLine:
            total_stmt = select(func.count()).select_from(Ticket).where(
                Ticket.support_line == line, 
                Ticket.status != TicketStatus.CLOSED
            )
            open_stmt = select(func.count()).select_from(Ticket).where(
                Ticket.support_line == line, 
                Ticket.status == TicketStatus.OPEN
            )
            
            total_count = (await self.db.execute(total_stmt)).scalar() or 0
            open_count = (await self.db.execute(open_stmt)).scalar() or 0
            
            stats[line.value] = {
                "total": total_count,
                "open": open_count
            }
        return stats
