"""
Shared LLM client adapter for graders.
Eliminates code duplication across LLM-based graders.
"""
from __future__ import annotations
from typing import Any, List, Dict, Optional


class LLMClientAdapter:
    """
    Adapter that wraps the app's LLM client to provide a consistent interface
    for all LLM-based graders.
    """
    
    def __init__(self, model: Optional[str] = None):
        self.model = model
        self._client_getter = None
    
    async def _ensure_client(self):
        if self._client_getter is None:
            from app.llm.client import get_llm_client
            self._client_getter = get_llm_client
    
    async def get_completion_async(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Any]] = None
    ) -> "MockResponse":
        """
        Get a completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tools (currently unused)
            
        Returns:
            MockResponse with 'content' attribute containing the LLM response
        """
        await self._ensure_client()
        client = await self._client_getter()
        
        # Extract system and user messages
        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), 
            "You are a helpful judge."
        )
        user_msg = next(
            (m["content"] for m in messages if m["role"] == "user"), 
            ""
        )
        
        content = await client.generate_response(
            prompt=user_msg, 
            system_prompt=system_msg
        )
        
        return MockResponse(content)


class MockResponse:
    """Simple response wrapper to match expected interface."""
    
    def __init__(self, content: str):
        self.content = content


def get_llm_adapter(model: Optional[str] = None) -> LLMClientAdapter:
    """Factory function to create an LLM adapter."""
    return LLMClientAdapter(model=model)
