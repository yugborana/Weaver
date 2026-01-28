"""Researcher agent for conducting initial research."""

import asyncio
import logging
from typing import List, Optional

from app.agents.base import BaseAgent
from app.models.research import (
    AgentType,
    ResearchTask,
    ResearchPlan,
    ResearchReport,
    ResearchSource,
    ResearchStatus
)
from app.tools.web_search import WebSearchTool
from app.tools.wikipedia import WikipediaTool
from app.config import settings

logger = logging.getLogger(__name__)

class ResearcherAgent(BaseAgent):
    """
    Agent responsible for planning, gathering data, and writing the first draft.
    """
    
    def __init__(self):
        super().__init__(AgentType.RESEARCHER)
        # Tools
        self.web_search = WebSearchTool(tavily_api_key=settings.tavily_api_key)
        self.wikipedia = WikipediaTool()
    
    async def process(
        self,
        task: ResearchTask,
        **kwargs
    ) -> ResearchReport:
        """
        Full lifecycle: Plan -> Search -> Write.
        """
        query = task.query
        logger.info(f"Starting Research for: {query.topic}")
        
        # 1. GENERATE PLAN (Strategy)
        # We check if a plan already exists in the task (resume capability)
        if not task.plan:
            task.plan = await self._generate_plan(task)
            task.status = ResearchStatus.PLANNING
            # In a real DB app, you'd save the task here
        
        # 2. EXECUTE SEARCH (Parallel)
        # We pass the plan's specific search queries, not just the raw topic
        logger.info("Executing Search Strategy...")
        task.status = ResearchStatus.IN_PROGRESS
        
        raw_sources = await self._gather_data_parallel(task.plan, task)
        
        # Store raw results in task for the Critic to see later
        # We store them as a flat list of ResearchSource objects
        task.raw_search_results = [s.model_dump() for s in raw_sources] 
        
        # 3. WRITE REPORT
        logger.info("Drafting Report...")
        report = await self._write_report(task, raw_sources)
        
        # Cleanup
        await self._cleanup_tools()
        
        return report

    async def _generate_plan(self, task: ResearchTask) -> ResearchPlan:
        """Generates a structured search strategy."""
        
        system_prompt = "You are a Senior Research Strategist. Plan the information gathering phase."
        
        prompt = f"""
        Topic: {task.query.topic}
        Subtopics: {task.query.subtopics}
        Requirements: {task.query.requirements}
        
        Create a research plan. 
        - Break the topic into 3-5 specific search queries.
        - Identify key data points needed (stats, dates, names).
        """
        
        return await self.generate_structured_llm_response(
            prompt=prompt,
            response_model=ResearchPlan,
            system_prompt=system_prompt
        )

    async def _gather_data_parallel(self, plan: ResearchPlan, task: "ResearchTask") -> List[ResearchSource]:
        """
        Runs all search tools in parallel for maximum speed.
        Now tracks tool calls for evaluation purposes.
        """
        from app.models.research import ToolCallRecord
        import time
        
        all_sources: List[ResearchSource] = []
        
        # 1. Create Tasks - use the generated 'search_queries' from the plan
        primary_query = plan.search_queries[0]
        
        # Track tool calls
        async def run_and_track_web_search(query: str) -> List[ResearchSource]:
            start = time.perf_counter()
            try:
                results = await self.web_search.search(query)
                duration = (time.perf_counter() - start) * 1000
                # Log the tool call
                task.tools_called.append(ToolCallRecord(
                    tool_name="web_search",
                    query=query,
                    result_count=len(results),
                    success=True,
                    duration_ms=duration
                ))
                logger.info(f"[TOOL] web_search({query}) -> {len(results)} results in {duration:.0f}ms")
                return results
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                task.tools_called.append(ToolCallRecord(
                    tool_name="web_search",
                    query=query,
                    result_count=0,
                    success=False,
                    duration_ms=duration,
                    error=str(e)
                ))
                logger.error(f"[TOOL] web_search({query}) FAILED: {e}")
                return []
        
        async def run_and_track_wikipedia(topic: str) -> List[ResearchSource]:
            start = time.perf_counter()
            try:
                results = await self.wikipedia.search(topic)
                duration = (time.perf_counter() - start) * 1000
                # Log the tool call
                task.tools_called.append(ToolCallRecord(
                    tool_name="wikipedia_search",
                    query=topic,
                    result_count=len(results),
                    success=True,
                    duration_ms=duration
                ))
                logger.info(f"[TOOL] wikipedia_search({topic}) -> {len(results)} results in {duration:.0f}ms")
                return results
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                task.tools_called.append(ToolCallRecord(
                    tool_name="wikipedia_search",
                    query=topic,
                    result_count=0,
                    success=False,
                    duration_ms=duration,
                    error=str(e)
                ))
                logger.error(f"[TOOL] wikipedia_search({topic}) FAILED: {e}")
                return []
        
        # 2. Run concurrently with tracking
        tasks = [
            run_and_track_web_search(primary_query),
            run_and_track_wikipedia(plan.main_topic)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 3. Flatten results
        for res in results:
            if isinstance(res, list):
                all_sources.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Search tool failed: {res}")
                
        # 4. Filter duplicates (by URL)
        unique_sources = {}
        for s in all_sources:
            if s.url and s.url not in unique_sources:
                unique_sources[s.url] = s
        
        logger.info(f"[TOOLS] Total: {len(task.tools_called)} tool calls, {len(unique_sources)} unique sources")
        
        return list(unique_sources.values())

    async def _write_report(
        self, 
        task: ResearchTask, 
        sources: List[ResearchSource]
    ) -> ResearchReport:
        """
        Synthesizes the raw sources into a coherent report.
        """
        
        # Format sources for the LLM context
        context_str = self._format_sources_for_prompt(sources)
        
        system_prompt = """You are a Lead Researcher. 
        Write a detailed, objective report based ONLY on the provided context.
        CITE YOUR SOURCES. When you use a fact, link it to the source URL provided in the context.
        """
        
        prompt = f"""
        # TASK
        Topic: {task.query.topic}
        Structure: {task.plan.subtopics}
        
        # RAW DATA (Use this to write the report)
        {context_str}
        
        # INSTRUCTIONS
        - Write a professional report with an Abstract, Sections, and Conclusion.
        - In the 'sources' list of the JSON, ONLY include sources you actually cited in the text.
        """
        
        # Direct Pydantic Generation
        report = await self.generate_structured_llm_response(
            prompt=prompt,
            response_model=ResearchReport,
            system_prompt=system_prompt,
            temperature=0.4 # Balanced creativity/factuality
        )
        
        # Post-process: Add metadata
        report.metadata["generated_by"] = "ResearcherAgent"
        report.metadata["source_count"] = len(sources)
        
        return report

    def _format_sources_for_prompt(self, sources: List[ResearchSource]) -> str:
        """
        Optimizes source text to fit in context window.
        """
        formatted = []
        for i, s in enumerate(sources[:15], 1): # Limit to top 15 sources to save tokens
            formatted.append(f"Source [{i}]: {s.title}")
            formatted.append(f"URL: {s.url}")
            # Truncate content to 400 chars per source
            content_snippet = s.content[:400].replace("\n", " ") 
            formatted.append(f"Content: {content_snippet}...\n")
            
        return "\n".join(formatted)

    async def _cleanup_tools(self):
        await self.web_search.close()
        await self.wikipedia.close()