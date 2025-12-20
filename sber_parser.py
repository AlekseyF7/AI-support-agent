"""
Улучшенный парсер сайта Сбербанка
Поддерживает: FAQ, статьи помощи, информацию о продуктах
Выходные форматы: JSON, ChromaDB (RAG)
"""

import asyncio
import json
import logging
import hashlib
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

# HTTP клиент
import httpx

# Парсинг HTML
from bs4 import BeautifulSoup

# Опциональный Playwright для JS-рендеринга
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Опциональная интеграция с RAG
try:
    from rag_system import RAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SberParser")


@dataclass
class ParsedItem:
    """Структура спарсенного элемента"""
    title: str
    content: str
    url: str
    category: str = "general"
    parsed_at: str = ""
    
    def __post_init__(self):
        if not self.parsed_at:
            self.parsed_at = datetime.now().isoformat()
    
    @property
    def id(self) -> str:
        return hashlib.md5(f"{self.title}:{self.url}".encode()).hexdigest()


class SberParser:
    """
    Универсальный парсер сайта Сбербанка
    
    Режимы работы:
    - simple: httpx (быстро, но без JS)
    - browser: Playwright (медленнее, но рендерит JS)
    """
    
    # Стартовые URL для парсинга
    DEFAULT_URLS = [
        "https://www.sberbank.ru/ru/person/help",
        "https://www.sberbank.ru/ru/person/help/sberbank_online",
        "https://www.sberbank.ru/ru/person/help/cards",
        "https://www.sberbank.ru/ru/person/help/sbp",
        "https://www.sberbank.ru/ru/person/help/contributions_faq",
        "https://www.sberbank.ru/ru/person/help/consumer_faq",
        "https://www.sberbank.ru/ru/person/help/ccards_faq",
    ]
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    ALLOWED_DOMAINS = {"www.sberbank.ru", "sberbank.ru"}
    
    def __init__(
        self,
        urls: Optional[List[str]] = None,
        use_browser: bool = False,
        max_depth: int = 2,
        output_file: Optional[str] = None,
        save_to_rag: bool = False
    ):
        self.urls = urls or self.DEFAULT_URLS
        self.use_browser = use_browser and PLAYWRIGHT_AVAILABLE
        self.max_depth = max_depth
        self.output_file = output_file
        self.save_to_rag = save_to_rag and RAG_AVAILABLE
        
        self.visited: Set[str] = set()
        self.results: List[ParsedItem] = []
        
        if use_browser and not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright не установлен. Используется httpx.")
        
        if save_to_rag and not RAG_AVAILABLE:
            logger.warning("⚠️ RAG система недоступна. Результаты будут сохранены в JSON.")
    
    def _is_valid_url(self, url: str) -> bool:
        """Проверка валидности URL"""
        parsed = urlparse(url)
        if parsed.netloc not in self.ALLOWED_DOMAINS:
            return False
        if url in self.visited:
            return False
        # Исключаем файлы
        skip_ext = ('.pdf', '.apk', '.exe', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.svg')
        if any(url.lower().endswith(ext) for ext in skip_ext):
            return False
        return True
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Нормализация URL"""
        absolute = urljoin(base_url, url)
        # Убираем якоря и trailing slash
        return absolute.split('#')[0].rstrip('/')
    
    async def _fetch_simple(self, url: str) -> Optional[str]:
        """Загрузка страницы через httpx"""
        async with httpx.AsyncClient(
            verify=False,
            headers=self.HEADERS,
            follow_redirects=True,
            timeout=15
        ) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                logger.warning(f"HTTP {response.status_code}: {url}")
            except Exception as e:
                logger.error(f"Ошибка загрузки {url}: {e}")
        return None
    
    async def _fetch_browser(self, url: str, browser_context) -> Optional[str]:
        """Загрузка страницы через Playwright"""
        page = await browser_context.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if not response or response.status >= 400:
                return None
            
            # Ждём загрузки контента
            try:
                await page.wait_for_selector("h1, h2, .kit-accordion", timeout=10000)
            except:
                pass
            
            # Скроллим для lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            return await page.content()
        except Exception as e:
            logger.error(f"Ошибка браузера {url}: {e}")
            return None
        finally:
            await page.close()
    
    def _parse_html(self, html: str, url: str) -> List[ParsedItem]:
        """Извлечение данных из HTML"""
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # Определяем категорию по URL
        category = "general"
        if "/cards" in url or "/ccards" in url:
            category = "cards"
        elif "/sbp" in url:
            category = "sbp"
        elif "/sberbank_online" in url:
            category = "online"
        elif "/contributions" in url:
            category = "deposits"
        elif "/consumer" in url:
            category = "credits"
        
        # === Стратегия 1: Kit-аккордеоны Сбера ===
        accordions = soup.find_all(
            ['div', 'section', 'details'],
            class_=lambda x: x and any(k in str(x).lower() for k in ['accordion', 'faq', 'kit-details', 'help-item'])
        )
        
        for acc in accordions:
            # Заголовок
            title_elem = acc.find(
                ['h2', 'h3', 'h4', 'button', 'summary', 'span', 'div'],
                class_=lambda x: x and any(k in str(x).lower() for k in ['title', 'header', 'question', 'trigger', 'heading', 'summary'])
            )
            # Контент
            content_elem = acc.find(
                ['div', 'section', 'p'],
                class_=lambda x: x and any(k in str(x).lower() for k in ['content', 'body', 'answer', 'text', 'pane'])
            )
            
            if title_elem and content_elem:
                title = title_elem.get_text(separator=' ', strip=True)
                content = content_elem.get_text(separator=' ', strip=True)
                
                if 5 < len(title) < 500 and len(content) > 20:
                    items.append(ParsedItem(
                        title=title,
                        content=content,
                        url=url,
                        category=category
                    ))
        
        # === Стратегия 2: Заголовки + следующий контент ===
        if not items:
            for header in soup.find_all(['h2', 'h3']):
                title = header.get_text(strip=True)
                if len(title) < 10 or len(title) > 400:
                    continue
                
                content_parts = []
                for sibling in header.find_next_siblings():
                    if sibling.name in ['h1', 'h2', 'h3']:
                        break
                    text = sibling.get_text(separator=' ', strip=True)
                    if text:
                        content_parts.append(text)
                
                content = "\n".join(content_parts).strip()
                if len(content) > 30:
                    items.append(ParsedItem(
                        title=title,
                        content=content,
                        url=url,
                        category=category
                    ))
        
        # === Стратегия 3: Структурированные списки ===
        if not items:
            for ul in soup.find_all('ul', class_=lambda x: x and 'list' in str(x).lower()):
                for li in ul.find_all('li', recursive=False):
                    text = li.get_text(separator=' ', strip=True)
                    if 20 < len(text) < 1000:
                        # Пробуем разделить на вопрос-ответ
                        parts = re.split(r'[:\?\-–—]', text, maxsplit=1)
                        if len(parts) == 2 and len(parts[0]) > 5 and len(parts[1]) > 10:
                            items.append(ParsedItem(
                                title=parts[0].strip(),
                                content=parts[1].strip(),
                                url=url,
                                category=category
                            ))
        
        return items
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Извлечение ссылок для обхода"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            absolute = self._normalize_url(href, base_url)
            
            # Только ссылки на разделы помощи
            if self._is_valid_url(absolute) and '/help' in absolute.lower():
                links.append(absolute)
        
        return links
    
    async def _crawl_simple(self, url: str, depth: int = 0):
        """Рекурсивный обход через httpx"""
        if depth > self.max_depth or not self._is_valid_url(url):
            return
        
        self.visited.add(url)
        logger.info(f"📄 [{depth}] {url}")
        
        html = await self._fetch_simple(url)
        if not html:
            return
        
        # Проверка на блокировку сертификатами
        if "gosuslugi.ru/crt" in html or "Национальный УЦ" in html:
            logger.warning(f"🛑 Блокировка сертификатом: {url}")
            return
        
        items = self._parse_html(html, url)
        if items:
            logger.info(f"   ✅ Найдено {len(items)} элементов")
            self.results.extend(items)
        
        # Рекурсивный обход
        if depth < self.max_depth:
            links = self._extract_links(html, url)
            for link in links[:10]:  # Лимит на кол-во ссылок с одной страницы
                await self._crawl_simple(link, depth + 1)
    
    async def _crawl_browser(self, url: str, browser_context, depth: int = 0):
        """Рекурсивный обход через Playwright"""
        if depth > self.max_depth or not self._is_valid_url(url):
            return
        
        self.visited.add(url)
        logger.info(f"🌐 [{depth}] {url}")
        
        html = await self._fetch_browser(url, browser_context)
        if not html:
            return
        
        items = self._parse_html(html, url)
        if items:
            logger.info(f"   ✅ Найдено {len(items)} элементов")
            self.results.extend(items)
        
        # Рекурсивный обход
        if depth < self.max_depth:
            links = self._extract_links(html, url)
            for link in links[:10]:
                await self._crawl_browser(link, browser_context, depth + 1)
                await asyncio.sleep(0.5)  # Вежливый delay
    
    async def run(self) -> List[ParsedItem]:
        """Запуск парсера"""
        logger.info("=" * 50)
        logger.info("🚀 Запуск парсера Сбербанка")
        logger.info(f"   Режим: {'browser' if self.use_browser else 'simple'}")
        logger.info(f"   Глубина: {self.max_depth}")
        logger.info(f"   URL: {len(self.urls)} стартовых")
        logger.info("=" * 50)
        
        if self.use_browser:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.HEADERS['User-Agent']
                )
                
                for url in self.urls:
                    await self._crawl_browser(url, context)
                
                await browser.close()
        else:
            for url in self.urls:
                await self._crawl_simple(url)
        
        # Дедупликация
        seen_ids = set()
        unique_results = []
        for item in self.results:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_results.append(item)
        self.results = unique_results
        
        logger.info("=" * 50)
        logger.info(f"✨ Завершено. Найдено: {len(self.results)} уникальных элементов")
        
        # Сохранение результатов
        await self._save_results()
        
        return self.results
    
    async def _save_results(self):
        """Сохранение результатов"""
        if not self.results:
            logger.warning("⚠️ Нет данных для сохранения")
            return
        
        # JSON файл
        if self.output_file:
            output_path = Path(self.output_file)
            data = [asdict(item) for item in self.results]
            output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            logger.info(f"💾 Сохранено в {output_path}")
        
        # RAG система
        if self.save_to_rag:
            try:
                rag = RAGSystem()
                documents = [item.content for item in self.results]
                metadatas = [
                    {"question": item.title, "source": item.url, "category": item.category}
                    for item in self.results
                ]
                ids = [item.id for item in self.results]
                
                rag.collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"🧠 Загружено в RAG. Всего в базе: {rag.collection.count()}")
            except Exception as e:
                logger.error(f"❌ Ошибка RAG: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="Парсер сайта Сбербанка",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python sber_parser.py                          # Быстрый парсинг
  python sber_parser.py --browser                # С рендерингом JS
  python sber_parser.py --output data.json       # Сохранить в файл
  python sber_parser.py --rag                    # Загрузить в ChromaDB
  python sber_parser.py --url https://sberbank.ru/ru/person/help/cards
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        action='append',
        help='URL для парсинга (можно указать несколько раз)'
    )
    parser.add_argument(
        '--browser', '-b',
        action='store_true',
        help='Использовать Playwright для рендеринга JS'
    )
    parser.add_argument(
        '--depth', '-d',
        type=int,
        default=2,
        help='Максимальная глубина обхода (по умолчанию: 2)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Путь к выходному JSON файлу'
    )
    parser.add_argument(
        '--rag',
        action='store_true',
        help='Сохранить результаты в RAG систему (ChromaDB)'
    )
    
    args = parser.parse_args()
    
    scraper = SberParser(
        urls=args.url,
        use_browser=args.browser,
        max_depth=args.depth,
        output_file=args.output,
        save_to_rag=args.rag
    )
    
    results = await scraper.run()
    
    # Если не указан output, выводим превью
    if not args.output and not args.rag:
        print("\n📋 Превью результатов:")
        for i, item in enumerate(results[:5], 1):
            print(f"\n{i}. [{item.category}] {item.title[:60]}...")
            print(f"   {item.content[:100]}...")
        
        if len(results) > 5:
            print(f"\n... и ещё {len(results) - 5} элементов")


if __name__ == "__main__":
    asyncio.run(main())

