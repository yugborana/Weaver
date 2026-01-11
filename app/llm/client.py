"""
Groq LLM Client for Deep Research Agent.
Handles text generation and structured JSON outputs using Pydantic.
"""

import json
import asyncio
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel, ValidationError

# pip install groq
from groq import AsyncGroq, APIConnectionError, RateLimitError

# Generic type variable for Pydantic models
T = TypeVar("T", bound=BaseModel)

class GroqClient:
    """
    Async Groq client wrapper.
    """
    
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.client: Optional[AsyncGroq] = None

    async def initialize(self) -> bool:
        """Initialize the Groq client."""
        try:
            self.client = AsyncGroq(api_key=self.api_key)
            return True
        except Exception as e:
            print(f"Failed to initialize LLM Client: {e}")
            return False

    async def _ensure_initialized(self):
        """Lazy initialization check."""
        if not self.client:
            success = await self.initialize()
            if not success:
                raise RuntimeError("Failed to initialize Groq client.")

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful research assistant.",
        temperature: float = 0.7
    ) -> str:
        """
        Generate a standard string response.
        """
        await self._ensure_initialized()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
            
        except RateLimitError:
            # Simple retry logic could be added here
            raise RuntimeError("Groq Rate Limit Exceeded.")
        except APIConnectionError:
            raise RuntimeError("Groq Connection Error.")
        except Exception as e:
            raise RuntimeError(f"LLM Generation Error: {str(e)}")

    async def generate_structured_response(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str = "You are a precise data extraction assistant.",
        temperature: float = 0.1
    ) -> T:
        """
        Generates a response and parses it into the provided Pydantic model.
        Uses Groq's native JSON mode.
        """
        await self._ensure_initialized()

        # 1. Construct schema instruction
        # We dump the Pydantic schema to JSON so the LLM knows exactly what fields to fill.
        json_schema = json.dumps(response_model.model_json_schema(), indent=2)
        
        schema_instruction = f"""
        You are a structured data processor. 
        You MUST output a valid JSON object that matches this schema exactly:
        {json_schema}
        
        Do not include markdown formatting (like ```json). Output ONLY the raw JSON.
        """
        
        full_system_prompt = f"{system_prompt}\n\n{schema_instruction}"

        try:
            # 2. Call LLM with JSON mode enabled
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                # This forces the model to output valid JSON
                response_format={"type": "json_object"}, 
                temperature=temperature,
            )

            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("LLM returned empty response.")

            # 3. Validate and Parse
            # pydantic.model_validate_json handles the string parsing and type checking
            return response_model.model_validate_json(content)

        except ValidationError as e:
            print(f"Validation Error: {str(e)}")
            print(f"Raw Output: {content}") # Debug print to see what the LLM actually tried to output
            raise RuntimeError(f"LLM failed to generate valid {response_model.__name__} JSON.")
            
        except Exception as e:
            raise RuntimeError(f"Structured Generation Error: {str(e)}")

# --- Dependency Injection ---
# Use this function to get the client instance in your agents
_client_instance: Optional[GroqClient] = None

async def get_llm_client() -> GroqClient:
    global _client_instance
    if _client_instance is None:
        # Import settings inside the function to avoid circular imports
        from app.config import settings
        _client_instance = GroqClient(api_key=settings.groq_api_key)
        await _client_instance.initialize()
    return _client_instance