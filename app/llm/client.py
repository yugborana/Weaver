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
        Uses Groq's native JSON mode with model-specific examples.
        """
        await self._ensure_initialized()

        # Get model-specific example based on the response model name
        model_name = response_model.__name__
        example = self._get_model_example(model_name)
        
        schema_instruction = f"""
You must respond with a valid JSON object.

{example}

RULES:
- Output ONLY the JSON object, no markdown or extra text
- Fill in ALL required fields with actual data based on the user's request
- Follow the exact structure shown in the example above
"""
        
        full_system_prompt = f"{system_prompt}\n\n{schema_instruction}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": full_system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}, 
                temperature=temperature,
            )

            content = response.choices[0].message.content
            
            if not content:
                raise ValueError("LLM returned empty response.")

            # Try to extract from "properties" if the LLM still wraps it
            try:
                parsed = json.loads(content)
                if "properties" in parsed and isinstance(parsed["properties"], dict):
                    content = json.dumps(parsed["properties"])
            except:
                pass

            return response_model.model_validate_json(content)

        except ValidationError as e:
            print(f"Validation Error: {str(e)}")
            print(f"Raw Output: {content}")
            raise RuntimeError(f"LLM failed to generate valid {response_model.__name__} JSON.")
            
        except Exception as e:
            raise RuntimeError(f"Structured Generation Error: {str(e)}")

    def _get_model_example(self, model_name: str) -> str:
        """Returns a concrete example for each model type."""
        examples = {
            "ResearchPlan": '''
Output a JSON object with this exact structure:
{
    "main_topic": "The main research topic",
    "subtopics": ["Subtopic 1", "Subtopic 2", "Subtopic 3"],
    "search_queries": ["search query 1", "search query 2", "search query 3"],
    "required_data_points": ["Data point 1", "Data point 2"]
}''',
            "ResearchReport": '''
Output a JSON object with this exact structure:
{
    "title": "Report Title",
    "abstract": "A brief summary of the report...",
    "sections": [
        {
            "title": "Section Title",
            "content": "Detailed content of this section...",
            "source_ids": []
        }
    ],
    "conclusion": "Final conclusions...",
    "references": [
        {
            "id": null,
            "title": "Source Title",
            "url": "https://example.com",
            "content": "Excerpt from source...",
            "relevance_score": 0.0,
            "credibility_score": 0.9
        }
    ],
    "metadata": {}
}''',
            "CritiqueFeedback": '''
Output a JSON object with this EXACT structure (arrays contain STRINGS ONLY):
{
    "overall_score": 5.5,
    "critique_round": 1,
    "strengths": ["Good coverage of main topic", "Well-structured report"],
    "weaknesses": ["Lacks depth in analysis", "Missing recent data"],
    "missing_information": ["Statistics on the topic", "More historical context"],
    "actionable_suggestions": ["Add more data", "Expand analysis section"],
    "decision": "revise"
}

CRITICAL - DO NOT USE OBJECTS:
- WRONG: "strengths": [{"description": "...", "evidence": "..."}]
- CORRECT: "strengths": ["The report covers the topic well", "Good sources"]
- All arrays must contain PLAIN TEXT STRINGS only
- decision must be "approve" or "revise"
- overall_score: 0.0 to 10.0 (be strict, most reports score 4-6)'''
        }
        return examples.get(model_name, "Output a valid JSON object matching the requested structure.")

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