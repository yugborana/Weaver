"""
FastAPI routes for the Deep Research Agent.
Refactored for non-blocking background execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel

# Import your Coordinator and Models
# Assumes you have a way to get the global coordinator instance
from app.orchestrator.coordinator import ResearchCoordinator
from app.models.research import ResearchQuery, ResearchTask, ResearchStatus

# --- Pydantic Models ---

class ResearchRequest(BaseModel):
    topic: str
    subtopics: List[str] = []
    depth_level: int = 3
    requirements: Optional[str] = None

class ResearchResponse(BaseModel):
    task_id: str
    status: str
    message: str
    created_at: datetime
    monitoring_url: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Dict[str, Any]
    current_stage: str # e.g. "browsing_web", "writing_report"
    result: Optional[Dict] = None # The final report if ready

# --- App Setup ---

app = FastAPI(
    title="Deep Research Agent API",
    version="1.0.0"
)

# Singleton Pattern for Coordinator
_coordinator: Optional[ResearchCoordinator] = None

async def get_coordinator() -> ResearchCoordinator:
    """Dependency to get the active coordinator instance."""
    global _coordinator
    if not _coordinator:
        _coordinator = ResearchCoordinator()
        await _coordinator.initialize()
    return _coordinator

@app.on_event("startup")
async def startup_event():
    # Initialize DB pools, etc.
    await get_coordinator()

# --- Routes ---

@app.post("/research", response_model=ResearchResponse, status_code=202)
async def start_research_task(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    coordinator: ResearchCoordinator = Depends(get_coordinator)
):
    """
    Starts a research task asynchronously.
    Returns a Task ID immediately.
    """
    try:
        # 1. Generate ID and Create Pending Task in DB
        # We do NOT run the research yet. We just reserve the slot.
        query = ResearchQuery(**request.model_dump())
        
        # You need to implement 'create_task' in coordinator to just write to DB
        task_id = await coordinator.create_task(query) 
        
        # 2. Schedule the heavy lifting
        # background_tasks runs AFTER the response is sent
        background_tasks.add_task(coordinator.start_workflow, task_id)
        
        return ResearchResponse(
            task_id=task_id,
            status="pending",
            message="Research task scheduled successfully.",
            created_at=datetime.utcnow(),
            monitoring_url=f"/research/{task_id}/status"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")

@app.get("/research/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    coordinator: ResearchCoordinator = Depends(get_coordinator)
):
    """
    Poll this endpoint to check progress.
    """
    task = await coordinator.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task ID not found.")
    
    # Construct a useful progress summary
    progress_info = {
        "messages_logged": len(task.agent_logs),
        "revisions": task.revision_count,
    }
    
    # Determine current stage for UI
    current_stage = "initializing"
    if task.status == ResearchStatus.PLANNING:
        current_stage = "planning_strategy"
    elif task.status == ResearchStatus.IN_PROGRESS:
        current_stage = "gathering_data"
    elif task.status == ResearchStatus.REVIEWING:
        current_stage = "critiquing_draft"
    elif task.status == ResearchStatus.COMPLETED:
        current_stage = "finished"

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status.value,
        progress=progress_info,
        current_stage=current_stage,
        result=task.current_report.model_dump() if task.current_report else None
    )

@app.delete("/research/{task_id}")
async def cancel_task(
    task_id: str,
    coordinator: ResearchCoordinator = Depends(get_coordinator)
):
    """Optional: Endpoint to stop a running agent."""
    success = await coordinator.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or already finished")
    return {"message": "Task cancelled"}