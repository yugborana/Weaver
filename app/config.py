"""Configuration management for the research app."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Supabase Configuration
    supabase_url: str = Field(default="http://localhost:8000")
    supabase_key: str = Field(default="test-key")
    supabase_service_role_key: Optional[str] = Field(default=None)  # Use for backend operations
    
    # Groq API Configuration
    groq_api_key: str = Field(default="test-key")
    groq_model: str = Field(default="qwen-2.5-72b")
    
    # Application Settings
    debug: bool = Field(default=False)
    max_retries: int = Field(default=3)
    research_timeout: int = Field(default=300)
    
    # Research Tools API Keys
    tavily_api_key: Optional[str] = Field(default=None)  # For web search
    serpapi_key: Optional[str] = Field(default=None)  # Alternative web search


# Create settings instance, allowing for test overrides
def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


settings = get_settings()
