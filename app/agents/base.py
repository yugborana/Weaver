"""Base agent class for all research agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

# Import the model base class for type hinting
from pydantic import BaseModel

# Use the getter function we created to avoid circular imports/global state issues
from app.llm.client import get_llm_client
from app.models.research import (
    AgentMessage,
    AgentType,
    ResearchTask, # We use the Task object as the main context
)

# Define a generic type variable that must be a Pydantic model
T = TypeVar("T", bound=BaseModel)

class BaseAgent(ABC):
    """
    Base class for all research agents.
    Handles common LLM interactions and logging.
    """
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        # We don't store the client in self to avoid pickling issues if you scale later.
        # We fetch it dynamically when needed.
    
    @abstractmethod
    async def process(
        self,
        task: ResearchTask,
        **kwargs
    ) -> Any:
        """
        Process the current state of the research task.
        
        Args:
            task: The full state object (containing query, current_report, feedback, etc.)
            kwargs: Additional context if needed
        """
        pass
    
    async def generate_llm_response(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate a plain text response from the LLM.
        """
        client = await get_llm_client()
        return await client.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature
        )
    
    async def generate_structured_llm_response(
        self,
        prompt: str,
        response_model: Type[T],  # <--- CRITICAL CHANGE: Pass the class type
        system_prompt: str = "You are a helpful AI assistant.",
        temperature: float = 0.3
    ) -> T:  # <--- Returns an instance of T (e.g., ResearchPlan), not Dict
        """
        Generate a structured Pydantic model response from the LLM.
        """
        client = await get_llm_client()
        return await client.generate_structured_response(
            prompt=prompt,
            response_model=response_model,
            system_prompt=system_prompt,
            temperature=temperature
        )
    
    def create_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """Create an agent message for the logs."""
        return AgentMessage(
            agent_type=self.agent_type,
            message=message,
            metadata=metadata or {}
        )

    def log(self, message: str):
        """Simple internal logger."""
        print(f"[{self.agent_type.value.upper()}] {message}")