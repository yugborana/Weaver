"""Refined Research-related Pydantic models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# --- Enums ---

class AgentType(str, Enum):
    """Agent types in the system."""
    PLANNER = "planner"       # NEW: Break down complex topics
    RESEARCHER = "researcher" # Gather data
    CRITIC = "critic"         # Review drafts
    REVISER = "reviser"       # Fix based on critique


class ResearchStatus(str, Enum):
    """Research task status lifecycle."""
    PENDING = "pending"
    PLANNING = "planning"        # NEW: Generating search strategy
    IN_PROGRESS = "in_progress"  # Active searching/drafting
    REVIEWING = "reviewing"      # Critic is analyzing
    REVISING = "revising"        # Reviser is updating
    COMPLETED = "completed"
    FAILED = "failed"


# --- Core Data Structures ---

class ResearchQuery(BaseModel):
    """Initial user request."""
    topic: str = Field(..., description="Main research topic")
    subtopics: List[str] = Field(default_factory=list, description="Specific subtopics to explore")
    depth_level: int = Field(default=3, ge=1, le=5, description="Depth (1=Summary, 5=Deep Dive)")
    requirements: Optional[str] = Field(None, description="User constraints (e.g. 'focus on EU markets')")


class ResearchPlan(BaseModel):
    """NEW: The strategy generated before researching."""
    main_topic: str
    subtopics: List[str] = Field(..., description="List of specific angles to investigate")
    search_queries: List[str] = Field(..., description="Exact keywords to send to the search tool")
    required_data_points: List[str] = Field(..., description="Specific facts needed (e.g. 'GDP 2024')")


class ResearchSource(BaseModel):
    """A specific piece of gathered intelligence."""
    id: Optional[str] = Field(None, description="Unique ID (useful for vector DB referencing)")
    title: str
    url: Optional[str]
    content: str = Field(..., description="The extracted text snippet")
    relevance_score: float = Field(default=0.0, description="Vector similarity score (if using RAG)")
    credibility_score: float = Field(default=0.0, description="Domain authority score")


class ResearchSection(BaseModel):
    """A chapter of the report."""
    title: str
    content: str = Field(..., description="The written prose")
    # We store source IDs here to link back to the full ResearchSource list
    source_ids: List[str] = Field(default_factory=list, description="IDs of sources cited in this section")


class ResearchReport(BaseModel):
    """The Artifact: The final output."""
    title: str
    abstract: str
    sections: List[ResearchSection]
    conclusion: str
    # Sources are stored at the top level to avoid duplication
    references: List[ResearchSource] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    

class CritiqueFeedback(BaseModel):
    """Structured feedback from the Critic Agent."""
    overall_score: float = Field(..., ge=0.0, le=10.0)
    critique_round: int = Field(..., description="Which iteration is this?")
    strengths: List[str]
    weaknesses: List[str]
    missing_information: List[str] = Field(default_factory=list, description="Specific data gaps to fill")
    actionable_suggestions: List[str]
    decision: str = Field(..., description="'approve' or 'revise'")


# --- Orchestration & State ---

class AgentMessage(BaseModel):
    """Log of internal monologue or inter-agent chat."""
    agent_type: AgentType
    step_name: str = Field(default="general", description="e.g. 'search_query_generation'")
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchTask(BaseModel):
    """The Master State Object (Stored in Supabase)."""
    id: Optional[str] = Field(None, description="Supabase UUID")
    query: ResearchQuery
    status: ResearchStatus = Field(default=ResearchStatus.PENDING)
    
    # --- The Memory Stack ---
    plan: Optional[ResearchPlan] = Field(None, description="The agreed strategy")
    raw_search_results: List[Dict] = Field(default_factory=list, description="Unprocessed scraper data")
    current_report: Optional[ResearchReport] = Field(None, description="The latest draft")
    
    # --- Loop Control ---
    feedback_history: List[CritiqueFeedback] = Field(default_factory=list)
    agent_logs: List[AgentMessage] = Field(default_factory=list)
    
    revision_count: int = Field(default=0, description="Counter for Critic<->Reviser loops")
    max_revisions: int = Field(default=3, description="Circuit breaker for infinite loops")
    
    # --- Timestamps ---
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))