""" 
Гео-сервис Сбербанка на базе 2GIS Places API.
Используется для поиска ближайших отделений и маршрутизации.
"""
import logging
from typing import List, Dict, Any, Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)

class GeoService:
    """
    Асинхронный сервис для взаимодействия с картографическими данными 2GIS.
    Управляет внутренним HTTP клиентом для оптимального переиспользования соединений.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация сервиса.
        
        Args:
            api_key: Ключ API 2GIS. Если не указан, берется из настроек.
        """
        self.api_key = api_key or settings.DG_API_KEY
        self.base_url = "https://catalog.api.2gis.com/3.0/items"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Ленивая инициализация и возврат асинхронного клиента."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_connections=5) # Ограничиваем нагрузку на API
            )
        return self._client

    async def find_nearest_branches(self, lat: float, lon: float, radius: int = 5000) -> List[Dict[str, Any]]:
        """
        Ищет ближайшие отделения Сбербанка.
        
        Args:
            lat: Широта.
            lon: Долгота.
            radius: Радиус поиска в метрах.
            
        Returns:
            List[Dict]: Список найденных объектов с адресами и координатами.
        """
        if not self.api_key:
            logger.error("❌ 2GIS API Key не обнаружен в конфигурации.")
            return []
            
        params = {
            "q": "Сбербанк",
            "point": f"{lon},{lat}",
            "radius": radius,
            "sort_point": f"{lon},{lat}",
            "key": self.api_key,
            "fields": "items.address_name,items.point,items.schedule,items.contact"
        }
        
        try:
            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "result" not in data or "items" not in data["result"]:
                logger.info(f"📍 Отделения не найдены в радиусе {radius}м ({lat}, {lon})")
                return []
            
            branches = []
            for item in data["result"]["items"]:
                name = item.get("name", "").lower()
                address = item.get("address_name", "").lower()
                
                # Исключаем банкоматы и терминалы для "Платинового" сервиса
                if "банкомат" in name or "банкомат" in address or "терминал" in name:
                    continue
                    
                point = item.get("point", {})
                if not point: continue
                    
                branches.append({
                    "id": item.get("id"),
                    "name": item.get("name", "Сбербанк"),
                    "address": item.get("address_name", "Адрес не указан"),
                    "lat": point.get("lat"),
                    "lon": point.get("lon"),
                    "url": f"https://2gis.ru/geo/{point.get('lon')},{point.get('lat')}",
                    "schedule": item.get("schedule", {}).get("text", "График не указан")
                })
                
            logger.debug(f"🔍 Найдено {len(branches)} отделений для ({lat}, {lon})")
            return branches
            
        except httpx.HTTPStatusError as e:
            logger.error(f"⚠️ 2GIS API HTTP Error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"❌ Непредвиденная ошибка GeoService: {e}")
            return []

    async def close(self):
        """Закрытие сессий и освобождение ресурсов."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("🛡️ GeoService HTTP клиент закрыт")
