import asyncio
import logging
import random
import re
import hashlib
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except ImportError:
    try:
        from playwright_stealth import stealth as stealth_async
    except ImportError:
        stealth_async = None

from bs4 import BeautifulSoup

from rag_system import RAGSystem
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ShadowHunter")

class ShadowHunter:
    """
    Advanced World-Class Scraper for Sberbank Knowledge.
    Uses Playwright for JS execution and Stealth mode to bypass WAF.
    """
    
    def __init__(self, start_urls: List[str]):
        self.start_urls = start_urls
        self.visited_urls: Set[str] = set()
        self.knowledge_base: List[Dict[str, str]] = []
        self.rag = RAGSystem()
        
        # Domains allowed to crawl to prevent leaking to external sites
        self.allowed_domains = {"www.sberbank.ru", "sberbank.ru"}

    def is_allowed(self, url: str) -> bool:
        """Check if URL belongs to Sberbank domains and hasn't been visited."""
        parsed = urlparse(url)
        return (
            parsed.netloc in self.allowed_domains and 
            url not in self.visited_urls and 
            not url.endswith(('.pdf', '.apk', '.exe', '.zip', '.png', '.jpg'))
        )

    async def extract_qa_pairs(self, html: str, url: str) -> List[Dict[str, str]]:
        """
        Heuristic-based extraction of QA pairs from Sberbank help pages.
        """
        soup = BeautifulSoup(html, 'html.parser')
        pairs = []
        
        # Strategy 1: Sberbank "Kit" Accordions (kit-accordion, kit-details)
        items = soup.find_all(['div', 'section', 'details', 'li'], class_=lambda x: x and any(k in x.lower() for k in ['accordion', 'faq', 'help-item', 'kit-details']))
        
        for item in items:
            question_node = item.find(['h2', 'h3', 'h4', 'div', 'button', 'summary', 'span'], class_=lambda x: x and any(k in x.lower() for k in ['title', 'header', 'question', 'summary', 'trigger', 'heading']))
            answer_node = item.find(['div', 'section', 'p', 'span'], class_=lambda x: x and any(k in x.lower() for k in ['content', 'body', 'answer', 'text', 'pane', 'description']))
            
            if question_node and answer_node:
                q_text = question_node.get_text(separator=' ', strip=True)
                a_text = answer_node.get_text(separator=' ', strip=True)
                
                if 5 < len(q_text) < 500 and 10 < len(a_text):
                    pairs.append({
                        "question": q_text,
                        "answer": a_text,
                        "source": url
                    })

        # Strategy 2: kit-accordion explicit match
        if not pairs:
            titles = soup.find_all(class_=re.compile(r"kit-accordion.*title|header", re.I))
            for title in titles:
                parent = title.find_parent(class_=re.compile(r"kit-accordion", re.I))
                content = None
                if parent:
                    content = parent.find(class_=re.compile(r"content|body|text", re.I))
                
                if title and content:
                    q = title.get_text(strip=True)
                    a = content.get_text(separator=' ', strip=True)
                    if 5 < len(q) < 500 and len(a) > 10:
                        pairs.append({"question": q, "answer": a, "source": url})

        # Strategy 3: Last resort headers
        if not pairs:
            for h in soup.find_all(['h2', 'h3']):
                q = h.get_text(strip=True)
                if len(q) < 10 or len(q) > 400: continue
                ans_parts = []
                for sibling in h.find_next_siblings():
                    if sibling.name in ['h1', 'h2', 'h3', 'h4']: break
                    text = sibling.get_text(separator=' ', strip=True)
                    if text: ans_parts.append(text)
                
                a = "\n".join(ans_parts).strip()
                if len(a) > 20:
                    pairs.append({"question": q, "answer": a, "source": url})
                    
        return pairs

    async def crawl_page(self, browser_context, url: str, depth: int = 0):
        """Recursively crawl pages and extract data."""
        if depth > 2 or not self.is_allowed(url):
            return

        self.visited_urls.add(url)
        logger.info(f"🕸️ Hunting on: {url} (Depth: {depth})")
        
        page = await browser_context.new_page()
        if stealth_async:
            if hasattr(stealth_async, "stealth_async"):
                await stealth_async.stealth_async(page)
            elif callable(stealth_async):
                res = stealth_async(page)
                if asyncio.iscoroutine(res): await res
        
        try:
            # Sberbank uses a heavy loading spinner. We wait for content.
            response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if not response or response.status >= 400:
                logger.warning(f"   ⚠️ Page {url} returned {response.status if response else 'null'}. Skipping.")
                return

            # Wait for spinner to disappear and content to appear
            try:
                await page.wait_for_selector(".kit-accordion, .kit-details, h1, h2", timeout=20000)
            except Exception:
                logger.warning(f"   ⏳ Page content taking too long to surface at {url}. Proceeding anyway.")

            # Mimic human attention span
            await asyncio.sleep(random.uniform(2, 4))
            
            # Scroll to trigger lazy loading - SAFELY against null bodies
            await page.evaluate("""() => {
                if (document.body) {
                    window.scrollTo(0, document.body.scrollHeight / 2);
                }
            }""")
            await asyncio.sleep(1)
            await page.evaluate("""() => {
                if (document.body) {
                    window.scrollTo(0, document.body.scrollHeight);
                }
            }""")
            await asyncio.sleep(2)
            
            html = await page.content()
            new_pairs = await self.extract_qa_pairs(html, url)
            
            if new_pairs:
                logger.info(f"   ✅ Found {len(new_pairs)} QA pairs")
                self.knowledge_base.extend(new_pairs)
            
            # Smart discovery
            if depth < 2:
                links = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
                for link in links:
                    absolute_link = urljoin(url, link).split('#')[0].rstrip('/')
                    # Stay within help/faq pathways
                    if self.is_allowed(absolute_link) and "/help/" in absolute_link.lower():
                        await self.crawl_page(browser_context, absolute_link, depth + 1)
                        
        except Exception as e:
            logger.error(f"   ❌ Failed to hunt on {url}: {str(e)}")
        finally:
            await page.close()

    async def run_hunt(self):
        """Main execution flow for the Shadow Hunter."""
        async with async_playwright() as p:
            logger.info("🎬 Initializing Ghost Browser (Chromium)...")
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            for start_url in self.start_urls:
                await self.crawl_page(context, start_url)
            
            await browser.close()
            
        logger.info(f"🏆 Hunt complete. Total QA pairs found: {len(self.knowledge_base)}")
        
        if self.knowledge_base:
            await self.ingest_to_rag()
        else:
            logger.warning("⚠️ No data gathered. Verify target URLs and selectors.")

    async def ingest_to_rag(self):
        """Push gathered knowledge to ChromaDB with upsert."""
        logger.info(f"💾 Ingesting {len(self.knowledge_base)} items into the Hive Mind...")
        
        documents = [item["answer"] for item in self.knowledge_base]
        metadatas = [{"question": item["question"], "source": item["source"]} for item in self.knowledge_base]
        ids = [hashlib.md5(item["question"].encode()).hexdigest() for item in self.knowledge_base]
        
        try:
            self.rag.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ Integration complete. Current Hive count: {self.rag.collection.count()}")
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")

if __name__ == "__main__":
    # VERIFIED TARGETS
    targets = [
        "https://www.sberbank.ru/ru/person/help",
        "https://www.sberbank.ru/ru/person/help/contributions_faq",
        "https://www.sberbank.ru/ru/person/help/consumer_faq",
        "https://www.sberbank.ru/ru/person/help/ccards_faq"
    ]
    
    hunter = ShadowHunter(targets)
    asyncio.run(hunter.run_hunt())
