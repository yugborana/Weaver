"""
Web search tool using DuckDuckGo and Tavily with Pydantic integration.
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import aiohttp

from app.models.research import ResearchSource

logger = logging.getLogger(__name__)

class WebSearchTool:
    """
    Tool for searching the web.
    Prioritizes Tavily (Premium) -> DuckDuckGo (Free/Fallback).
    """
    
    _RATE_LIMIT_DELAY = 1.0 # 1 second between search requests
    _last_request_time = 0.0
    
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._owns_session = True # Track if we created the session
    
    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._owns_session = True

    async def _enforce_rate_limit(self):
        current_time = time.time()
        time_since = current_time - self._last_request_time
        if time_since < self._RATE_LIMIT_DELAY:
            await asyncio.sleep(self._RATE_LIMIT_DELAY - time_since)
        self._last_request_time = time.time()

    async def close(self):
        if self._owns_session and self.session and not self.session.closed:
            await self.session.close()

    async def search(self, query: str, max_results: int = 5) -> List[ResearchSource]:
        """
        Main entry point. Tries Tavily, falls back to DuckDuckGo.
        """
        await self._ensure_session()
        await self._enforce_rate_limit()

        results = []
        
        # 1. Try Tavily (Best for Agents)
        if self.tavily_api_key:
            results = await self.search_tavily(query, max_results)
            if results:
                return results
        
        # 2. Fallback to DuckDuckGo
        logger.info(f"Falling back to DuckDuckGo for: {query}")
        results = await self.search_duckduckgo(query, max_results)
        
        if not results:
            logger.warning(f"No results found for: {query}")
            
        return results

    async def search_tavily(self, query: str, max_results: int = 5) -> List[ResearchSource]:
        """
        Uses Tavily API. Returns validated ResearchSource objects.
        """
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "max_results": max_results,
                # For Deep Research, we want the answer + raw content if possible
                "include_answer": True, 
                "search_depth": "basic", # Use "advanced" for deeper (slower/more expensive) searches
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Tavily Error: {response.status}")
                    return []
                
                data = await response.json()
                results = []
                
                # Parse Tavily 'results' list
                for item in data.get("results", []):
                    # Tavily gives 'content' which is a long snippet. 
                    # We map this to our 'content' field.
                    source = ResearchSource(
                        title=item.get("title", "Untitled"),
                        url=item.get("url"),
                        content=item.get("content", ""),
                        credibility_score=item.get("score", 0.8) # Tavily score is usually relevance
                    )
                    results.append(source)
                
                return results

        except Exception as e:
            logger.error(f"Tavily Exception: {e}")
            return []

    async def search_duckduckgo(self, query: str, max_results: int = 5) -> List[ResearchSource]:
        """
        Uses DuckDuckGo Instant Answer API.
        NOTE: This often returns 0 results for niche research topics.
        """
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                results = []
                
                # 1. Abstract (The main "Instant Answer")
                if data.get("AbstractText"):
                    results.append(ResearchSource(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL"),
                        content=data.get("AbstractText"),
                        credibility_score=0.6,
                        source="DuckDuckGo"
                    ))
                
                # 2. Related Topics (Links)
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if "Text" in topic and "FirstURL" in topic:
                        results.append(ResearchSource(
                            title=topic.get("Text", "")[:50] + "...",
                            url=topic.get("FirstURL"),
                            content=topic.get("Text"),
                            credibility_score=0.5
                        ))
                        
                return results

        except Exception as e:
            logger.error(f"DDG Exception: {e}")
            return []

    async def multi_query_search(self, queries: List[str]) -> Dict[str, List[ResearchSource]]:
        """
        Runs multiple queries in parallel. 
        """
        tasks = [self.search(q) for q in queries]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results_dict = {}
        for query, result in zip(queries, results_list):
            if isinstance(result, list):
                results_dict[query] = result
            else:
                logger.error(f"Failed query '{query}': {result}")
                results_dict[query] = []
        
        return results_dict