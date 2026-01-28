"""Reviser agent for improving research reports based on feedback."""

import datetime
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.models.research import (
    AgentType,
    ResearchTask,
    ResearchReport,
    ResearchSection,
    CritiqueFeedback
)


class ReviserAgent(BaseAgent):
    """
    Agent responsible for rewriting reports based on critique.
    """
    
    def __init__(self):
        super().__init__(AgentType.REVISER)
    
    async def process(
        self,
        task: ResearchTask,
        **kwargs
    ) -> ResearchReport:
        """
        Takes the current report and critique, and generates a V2 report.
        """
        
        # 1. Validation
        if not task.current_report:
            raise ValueError("Reviser cannot work without an existing report.")
        
        # In a real loop, you'd pull the *latest* feedback. 
        # Assuming the last item in feedback_history is the relevant one.
        if not task.feedback_history:
            raise ValueError("Reviser cannot work without critique feedback.")
            
        report = task.current_report
        feedback = task.feedback_history[-1] # Get latest critique
        query = task.query
        
        # 2. System Prompt
        system_prompt = """You are a Senior Editor. 
        Your goal is to rewrite the provided Research Report to address the Critic's feedback.
        
        RULES:
        1. Keep the same structure (Introduction -> Sections -> Conclusion) unless asked to change it.
        2. IMPROVE the prose: make it professional, objective, and dense with information.
        3. DO NOT invent new sources. Use the sources provided in the original text.
        4. If the critique says a section is weak, expand on the logic or clarify the argument.
        """
        
        # 3. User Prompt
        # We flatten lists to strings for the prompt
        strengths_txt = "\n- ".join(feedback.strengths)
        weaknesses_txt = "\n- ".join(feedback.weaknesses)
        suggestions_txt = "\n- ".join(feedback.actionable_suggestions)
        
        prompt = f"""
        # ORIGINAL REQUEST
        Topic: {query.topic}
        
        # CRITIQUE (Implement these changes!)
        Score: {feedback.overall_score}/10
        
        ## Weaknesses to Fix:
        - {weaknesses_txt}
        
        ## Suggestions:
        - {suggestions_txt}
        
        # THE ORIGINAL DRAFT
        Title: {report.title}
        
        ## Abstract
        {report.abstract}
        
        ## Sections
        {self._sections_to_text(report.sections)}
        
        ## Conclusion
        {report.conclusion}
        
        # INSTRUCTION
        Rewrite the report. Output the full 'ResearchReport' object structure. 
        Retain existing valid sources in the 'sources' list.
        """
        
        # 4. Generate with Pydantic Validation
        # The client returns a ResearchReport instance directly
        revised_report = await self.generate_structured_llm_response(
            prompt=prompt,
            response_model=ResearchReport,
            system_prompt=system_prompt,
            temperature=0.3 # Slightly higher than 0 to allow creative rewriting
        )
        
        # 5. Post-Processing (Logic handled by Code, not AI)
        # Increment revision number
        current_rev = report.metadata.get("revision_number", 1)
        revised_report.metadata = {
            **report.metadata,
            "revision_number": current_rev + 1,
            "last_critique_score": feedback.overall_score,
            "revised_by": "AI_Reviser_Agent"
        }
        
        return revised_report

    def _sections_to_text(self, sections: List[ResearchSection]) -> str:
        """Helper to format sections for the LLM context."""
        text = []
        for i, sec in enumerate(sections, 1):
            text.append(f"--- Section {i}: {sec.title} ---")
            text.append(sec.content)
            # We explicitly mention sources so the LLM knows what to keep
            if sec.source_ids:
                text.append(f"(Cites {len(sec.source_ids)} sources)")
            text.append("\n")
        return "\n".join(text)