"""
arXiv research paper search tool with Rate Limiting and Pydantic integration.
"""

import logging
import asyncio
import time
import re
from typing import List, Optional
from xml.etree import ElementTree as ET
from datetime import datetime

import aiohttp

# Import the model we defined earlier to ensure compatibility
from app.models.research import ResearchSource

logger = logging.getLogger(__name__)

class ArxivTool:
    """
    Tool for searching arXiv. 
    Includes strict rate limiting (3s) to prevent API bans.
    """
    
    # arXiv API requires 3 seconds between requests
    _RATE_LIMIT_DELAY = 3.0
    _last_request_time = 0.0
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Args:
            session: Optional shared session. If None, one will be created.
        """
        self.base_url = "http://export.arxiv.org/api/query"
        self.session = session
        self._owns_session = session is None
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._owns_session = True

    async def _enforce_rate_limit(self):
        """Sleeps if requests are too frequent."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._RATE_LIMIT_DELAY:
            sleep_time = self._RATE_LIMIT_DELAY - time_since_last
            logger.debug(f"ArxivTool: Rate limiting, sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()

    async def close(self):
        """Close session if we own it."""
        if self._owns_session and self.session and not self.session.closed:
            await self.session.close()

    async def search(
        self,
        query: str,
        max_results: int = 5,
        offset: int = 0,  # Added pagination support
        sort_by: str = "relevance",
        sort_order: str = "descending"
    ) -> List[ResearchSource]:
        """
        Executes search and returns validated ResearchSource objects.
        """
        await self._ensure_session()
        await self._enforce_rate_limit()
        
        try:
            params = {
                "search_query": query,
                "start": offset,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": sort_order
            }
            
            logger.info(f"Searching arXiv: {query} (Offset: {offset})")
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    logger.error(f"arXiv API error: {response.status}")
                    return []
                
                content = await response.text()
                return self._parse_to_models(content)
                
        except Exception as e:
            logger.error(f"arXiv search exception: {str(e)}")
            return []

    def _parse_to_models(self, xml_content: str) -> List[ResearchSource]:
        """
        Parses XML directly into Pydantic ResearchSource models.
        """
        try:
            # Remove namespace prefixes to make parsing easier
            # (Hack but effective for simple arXiv parsing)
            xml_content = re.sub(' xmlns="[^"]+"', '', xml_content, count=1)
            root = ET.fromstring(xml_content)
            
            sources = []
            
            # Navigate standard Atom structure
            for entry in root.findall("entry"):
                try:
                    # 1. Extract ID
                    id_elem = entry.find("id")
                    paper_url = id_elem.text if id_elem is not None else ""
                    
                    # 2. Extract Title
                    title_elem = entry.find("title")
                    title = self._clean_text(title_elem.text) if title_elem is not None else "Unknown Title"
                    
                    # 3. Extract Abstract (Summary)
                    summary_elem = entry.find("summary")
                    abstract = self._clean_text(summary_elem.text) if summary_elem is not None else ""
                    
                    # 4. Extract PDF Link
                    pdf_link = paper_url
                    for link in entry.findall("link"):
                        if link.get("title") == "pdf":
                            pdf_link = link.get("href")
                    
                    # 5. Extract Date
                    published_elem = entry.find("published")
                    pub_date = None
                    if published_elem is not None:
                        try:
                            # 2023-10-12T14:23:00Z
                            pub_date = datetime.strptime(published_elem.text, "%Y-%m-%dT%H:%M:%SZ")
                        except ValueError:
                            pass

                    # 6. Map to ResearchSource Model
                    source = ResearchSource(
                        title=title,
                        url=pdf_link,
                        # We use the abstract as the initial 'content'
                        content=f"ABSTRACT: {abstract}", 
                        credibility_score=1.0, # arXiv is highly credible
                        publication_date=pub_date,
                        # We can store extra metadata if needed
                        # id=paper_url 
                    )
                    sources.append(source)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse a single arXiv entry: {e}")
                    continue
            
            return sources
            
        except ET.ParseError as e:
            logger.error(f"XML Parse Error: {e}")
            return []

    @staticmethod
    def _clean_text(text: str) -> str:
        """Flattens multiline text."""
        if not text: 
            return ""
        return " ".join(text.split())

# --- Usage Example (Async) ---
async def main():
    tool = ArxivTool()
    results = await tool.search("cat:cs.AI AND ti:agent", max_results=3)
    for paper in results:
        print(f"[{paper.publication_date.year}] {paper.title}")
        print(f"Link: {paper.url}\n")
    await tool.close()