from __future__ import annotations
import time
from typing import Any, List, Optional, Protocol
from .types import EvalCase, EvalResult, ToolCall, ReasoningStep
from .graders import Grader, UnifiedGrader


# =============================================================================
# Agent Protocol
# =============================================================================

class AgentProtocol(Protocol):
    async def run(self, task: str) -> str: ...
    def get_last_trace(self) -> Optional[dict]: ...
    def get_tools_called(self) -> Optional[List[ToolCall]]: ...
    def get_reasoning_steps(self) -> Optional[List[ReasoningStep]]: ...


# =============================================================================
# Evaluator
# =============================================================================

class Evaluator:
    
    def __init__(
        self,
        agent: Any,
        grader: Optional[Grader] = None,
        include_trace: bool = True,
        include_tools: bool = True,
        include_reasoning: bool = True,
    ):
        self.agent = agent
        self.grader = grader or UnifiedGrader()
        self.include_trace = include_trace
        self.include_tools = include_tools
        self.include_reasoning = include_reasoning
    
    async def run_case(self, case: EvalCase) -> EvalResult:
        start_time = time.perf_counter()
        output, error, trace, tools_called, reasoning_steps = None, None, None, None, None
        sources_used = None
        
        try:
            output = await self.agent.run(case.input)
            if self.include_trace and hasattr(self.agent, 'get_last_trace'):
                trace = self.agent.get_last_trace()
            if self.include_tools and hasattr(self.agent, 'get_tools_called'):
                tools_called = self.agent.get_tools_called()
            if self.include_reasoning and hasattr(self.agent, 'get_reasoning_steps'):
                reasoning_steps = self.agent.get_reasoning_steps()
            if hasattr(self.agent, 'get_sources_used'):
                sources_used = self.agent.get_sources_used()
        except Exception as e:
            error = str(e)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        enriched_case = self._enrich_case(case, tools_called, reasoning_steps, trace)
        
        grader_breakdown = None
        if error:
            passed, score, reason = False, 0.0, f"Error: {error}"
        elif output is None:
            passed, score, reason = False, 0.0, "No output from agent"
        else:
            if hasattr(self.grader, 'grade_async'):
                passed, score, reason = await self.grader.grade_async(output, enriched_case)
            else:
                passed, score, reason = self.grader.grade(output, enriched_case)
            
            # Check if grader populated breakdown in case metadata (CompositeGrader does this)
            if "grader_breakdown" in enriched_case.metadata:
                grader_breakdown = enriched_case.metadata["grader_breakdown"]
        
        grader_type = "llm_judge"
        if hasattr(self.grader, "__class__"):
            # Simple heuristic: LLMGrader -> llm_judge, TaskCompletionGrader -> task_completion
            class_name = self.grader.__class__.__name__
            import re
            # Convert PascalCase to snake_case
            grader_type = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
            if grader_type.endswith("_grader"):
                grader_type = grader_type[:-7]
        
        # Extract tool names for display
        tools_used = None
        if tools_called:
            tools_used = [t.name if hasattr(t, 'name') else t.get('name', 'unknown') for t in tools_called]
                
        return EvalResult(
            case=case, output=output, passed=passed, score=score,
            reason=reason, latency_ms=latency_ms, trace=trace, error=error,
            grader_type=grader_type,
            grader_breakdown=grader_breakdown,
            tools_used=tools_used,
            sources_cited=sources_used,
        )
    
    def _enrich_case(
        self,
        case: EvalCase,
        tools_called: Optional[List[ToolCall]],
        reasoning_steps: Optional[List[ReasoningStep]],
        trace: Optional[dict],
    ) -> EvalCase:
        enriched_metadata = dict(case.metadata)
        if tools_called is not None:
            enriched_metadata["tools_called"] = tools_called
        if reasoning_steps is not None:
            enriched_metadata["reasoning_steps"] = reasoning_steps
        if trace is not None:
            enriched_metadata["trace"] = trace
        return EvalCase(input=case.input, expected=case.expected, name=case.name, metadata=enriched_metadata)
