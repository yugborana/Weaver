"""Critic agent for evaluating research reports."""

from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.models.research import (
    AgentType,
    ResearchTask,
    ResearchReport,
    CritiqueFeedback,
    ResearchStatus
)


class CriticAgent(BaseAgent):
    """
    Agent responsible for critiquing research reports.
    """
    
    def __init__(self):
        super().__init__(AgentType.CRITIC)
    
    async def process(
        self,
        task: ResearchTask,
        **kwargs
    ) -> CritiqueFeedback:
        """
        Evaluates the current report in the ResearchTask.
        """
        
        # 1. Validation Checks
        if not task.current_report:
            raise ValueError("Critic Agent failed: No report found in task to critique.")
            
        # 2. Prepare Context
        query = task.query
        report = task.current_report
        
        # 3. Build System Prompt (Focus on Instructions, not JSON Formatting)
        system_prompt = """You are a VERY HARSH Senior Research Critic.
        Your job is to STRICTLY evaluate the provided report. You have HIGH STANDARDS.
        
        Evaluate for:
        1. Logical consistency - Are arguments well-structured?
        2. Depth of data - Is there enough detail and analysis?
        3. Source credibility - Are sources reliable and properly cited?
        4. Hallucinations - Are there vague or unsupported claims?
        5. Completeness - Does it fully answer the research query?

        SCORING GUIDELINES (be strict!):
        - 8-10: EXCEPTIONAL - Publishable quality, comprehensive, no flaws
        - 6-7: GOOD - Solid report but has minor issues
        - 4-5: AVERAGE - Needs significant improvement
        - 1-3: POOR - Major issues, incomplete or inaccurate
        
        Most reports should score between 4-6. Only give 7+ for truly excellent work.
        Be harsh but constructive. Always find weaknesses to improve.
        """
        
        # 4. Generate the Prompt
        # We don't need to teach it JSON structure here; the client handles that.
        prompt = f"""
        # User Query
        Topic: {query.topic}
        Subtopics: {', '.join(query.subtopics)}
        Requirements: {query.requirements or 'N/A'}

        # The Report to Critique
        Title: {report.title}
        
        ## Abstract
        {report.abstract}
        
        ## Sections
        {self._sections_to_text(report.sections)}
        
        ## Conclusion
        {report.conclusion}
        
        ## Metadata
        Source Count: {len(report.references)}
        """
        
        # 5. Call LLM with Pydantic Validation
        # NOTE: This returns a 'CritiqueFeedback' object, NOT a dict.
        feedback = await self.generate_structured_llm_response(
            prompt=prompt,
            response_model=CritiqueFeedback,  # <--- The magic happens here
            system_prompt=system_prompt,
            temperature=0.2 # Low temp for objective grading
        )
        
        return feedback

    def _sections_to_text(self, sections: List) -> str:
        """Helper to format sections for the prompt."""
        text = []
        for i, sec in enumerate(sections, 1):
            text.append(f"Section {i}: {sec.title}")
            text.append(f"{sec.content[:2000]}...") # Truncate very long sections to save tokens
            text.append(f"(Cites {len(sec.source_ids)} sources)\n")
        return "\n".join(text)