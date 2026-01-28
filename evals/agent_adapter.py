import asyncio
import json
import re
from typing import Optional, List, Any, Dict
from evals.types import ToolCall, ReasoningStep
from app.orchestrator.coordinator import ResearchCoordinator
from app.models.research import ResearchQuery, ResearchStatus


class ResearchAgentAdapter:
    """
    Adapts the Deep Research Agent (Coordinator) to the AgentProtocol 
    expected by the evaluation framework.
    
    Now includes:
    - Tool call tracking from agent logs
    - Source extraction from research reports
    - Token/cost tracking
    """
    
    def __init__(self):
        self.coordinator: Optional[ResearchCoordinator] = None
        self.last_trace: Dict[str, Any] = {}
        self.tools_called: List[ToolCall] = []
        self.reasoning_steps: List[ReasoningStep] = []
        self.sources_used: List[str] = []
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
    
    async def initialize(self):
        if not self.coordinator:
            from app.orchestrator.coordinator import ResearchCoordinator
            self.coordinator = ResearchCoordinator()
            await self.coordinator.initialize()

    def _reset_tracking(self):
        """Reset tracking data between runs."""
        self.tools_called = []
        self.reasoning_steps = []
        self.sources_used = []
        self.tokens_used = 0
        self.cost_usd = 0.0
        self.last_trace = {}

    async def run(self, task_input: str) -> str:
        """
        Runs the full research workflow for a given query/topic.
        Returns the final report as a string.
        """
        self._reset_tracking()
        await self.initialize()
        
        # 1. Start the task
        query = ResearchQuery(topic=task_input)
        task_id = await self.coordinator.create_task(query)
        
        # 2. Run the workflow
        try:
            await self.coordinator.start_workflow(task_id)
        except Exception as e:
            return f"Error during workflow execution: {e}"
        
        # 3. Retrieve the result
        task = await self.coordinator.get_task(task_id)
        
        if not task:
            return "Task not found after execution."
        
        # 4. Extract tools from task.tools_called (proper tracking) or logs (fallback)
        self._extract_tools_from_task(task)
        
        # 5. Extract reasoning steps from logs
        self._extract_reasoning_from_logs(task)
            
        if task.status == ResearchStatus.COMPLETED and task.current_report:
            # Store trace info
            self.last_trace = {
                "task_id": task_id,
                "revision_count": task.revision_count,
                "plan": task.plan.model_dump() if task.plan else {},
                "feedback_history": [f.model_dump() for f in task.feedback_history],
                "tools_called": [t.__dict__ for t in self.tools_called],
                "sources_used": self.sources_used,
            }
            
            # Extract sources from report
            self._extract_sources_from_report(task)
            
            # Convert report to string
            return json.dumps(task.current_report.model_dump(), indent=2)
            
        elif task.status == ResearchStatus.FAILED:
            return f"Research task failed. logs: {[l.message for l in task.agent_logs[-3:]]}"
            
        else:
            return f"Task finished with unexpected status: {task.status}"

    def _extract_tools_from_task(self, task) -> None:
        """Extract tool calls from task.tools_called (proper tracking)."""
        # First check for proper ToolCallRecord objects
        if hasattr(task, 'tools_called') and task.tools_called:
            for tool_record in task.tools_called:
                # Handle both ToolCallRecord objects and dicts
                if hasattr(tool_record, 'tool_name'):
                    tool_name = tool_record.tool_name
                    query = tool_record.query if hasattr(tool_record, 'query') else ""
                    success = tool_record.success if hasattr(tool_record, 'success') else True
                elif isinstance(tool_record, dict):
                    tool_name = tool_record.get('tool_name', 'unknown')
                    query = tool_record.get('query', '')
                    success = tool_record.get('success', True)
                else:
                    continue
                
                self.tools_called.append(ToolCall(
                    name=tool_name,
                    input_parameters={"query": query},
                    output=None,
                    description=f"Tool call: {tool_name}({query[:50]}...)" if len(query) > 50 else f"Tool call: {tool_name}({query})",
                ))
            return
        
        # Fallback: parse agent_logs if tools_called is empty
        self._extract_tools_from_logs(task)

    def _extract_tools_from_logs(self, task) -> None:
        """Extract tool calls from agent logs."""
        if not hasattr(task, 'agent_logs'):
            return
        
        # NEW: Parse [TOOL_CALL] entries first (most reliable)
        tool_call_pattern = r"\[TOOL_CALL\]\s*(\w+)\((.+?)\.\.\.\)\s*->\s*(\d+)\s*results"
        tools_used_pattern = r"\[TOOLS_USED\]\s*(.+)"
        
        for log in task.agent_logs:
            message = log.message if hasattr(log, 'message') else str(log)
            
            # Check for [TOOL_CALL] format (from coordinator)
            tool_matches = re.findall(tool_call_pattern, message, re.IGNORECASE)
            for match in tool_matches:
                tool_name, query, result_count = match
                self.tools_called.append(ToolCall(
                    name=tool_name,
                    input_parameters={"query": query},
                    output=None,
                    description=f"Tool call: {tool_name}({query}...) -> {result_count} results",
                ))
            
            # Also check for [TOOLS_USED] summary
            tools_used_matches = re.findall(tools_used_pattern, message, re.IGNORECASE)
            for match in tools_used_matches:
                tool_names = [t.strip() for t in match.split(',')]
                for tool_name in tool_names:
                    # Avoid duplicates
                    if not any(t.name == tool_name for t in self.tools_called):
                        self.tools_called.append(ToolCall(
                            name=tool_name,
                            input_parameters={},
                            output=None,
                            description=f"Tool used: {tool_name}",
                        ))

    def _extract_reasoning_from_logs(self, task) -> None:
        """Extract reasoning steps from agent logs."""
        if not hasattr(task, 'agent_logs'):
            return
        
        reasoning_keywords = ["thinking", "planning", "considering", "analyzing", "decided"]
        action_keywords = ["searching", "querying", "calling", "executing", "running"]
        
        current_thought = None
        
        for log in task.agent_logs:
            message = log.message if hasattr(log, 'message') else str(log)
            message_lower = message.lower()
            
            # Check if this is a reasoning step
            is_thought = any(kw in message_lower for kw in reasoning_keywords)
            is_action = any(kw in message_lower for kw in action_keywords)
            
            if is_thought:
                if current_thought:
                    self.reasoning_steps.append(current_thought)
                current_thought = ReasoningStep(thought=message)
            elif is_action and current_thought:
                current_thought.action = message
            elif current_thought and not is_thought:
                current_thought.observation = message
                self.reasoning_steps.append(current_thought)
                current_thought = None
        
        # Add final thought if exists
        if current_thought:
            self.reasoning_steps.append(current_thought)

    def _extract_sources_from_report(self, task) -> None:
        """Extract source URLs and references from the report."""
        if not task.current_report:
            return
        
        report_text = ""
        if hasattr(task.current_report, 'content'):
            report_text = task.current_report.content
        elif hasattr(task.current_report, 'model_dump'):
            report_dict = task.current_report.model_dump()
            report_text = json.dumps(report_dict)
        
        # Extract URLs
        url_pattern = r'https?://[^\s\)\]\}\"\'<>]+'
        urls = re.findall(url_pattern, report_text)
        
        # Extract citations like [1], [Source: ...]
        citation_pattern = r'\[(?:Source:|Ref:|Citation:)?\s*([^\]]+)\]'
        citations = re.findall(citation_pattern, report_text)
        
        # Combine and deduplicate
        all_sources = list(set(urls + [c for c in citations if not c.isdigit()]))
        self.sources_used = all_sources[:20]  # Limit to 20 sources

    def get_last_trace(self) -> Optional[dict]:
        return self.last_trace if self.last_trace else None

    def get_tools_called(self) -> Optional[List[ToolCall]]:
        return self.tools_called if self.tools_called else None

    def get_reasoning_steps(self) -> Optional[List[ReasoningStep]]:
        return self.reasoning_steps if self.reasoning_steps else None
    
    def get_sources_used(self) -> Optional[List[str]]:
        return self.sources_used if self.sources_used else None
    
    def get_token_usage(self) -> Dict[str, Any]:
        return {
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }

