from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import glob
from pathlib import Path

# Import the Eval Runner and Adapter
from evals.runner import EvalRunner
from evals.agent_adapter import ResearchAgentAdapter

router = APIRouter()

# --- Models ---

class EvalConfig(BaseModel):
    agent_model: str
    judge_model: str

class DatasetInfo(BaseModel):
    name: str
    file: str
    count: int
    path: str

class GraderInfo(BaseModel):
    id: str
    name: str
    description: str

class RunEvalRequest(BaseModel):
    dataset: str
    grader: str

# --- Routes ---

@router.get("/config")
async def get_config():
    # In a real app, fetch from settings
    return {
        "agent_model": "llama-3.3-70b-versatile",
        "judge_model": "llama-3.1-8b-instant"
    }

@router.get("/eval/datasets")
async def get_datasets():
    datasets = []
    # Search for json files in root and evals dir
    files = glob.glob("*.json") + glob.glob("evals/*.json")
    
    for f in files:
        if "package" in f or "lock" in f or "tsconfig" in f:
            continue
            
        try:
            path = Path(f)
            content = json.loads(path.read_text())
            if isinstance(content, list) and len(content) > 0 and "input" in content[0]:
                datasets.append({
                    "name": path.stem.replace("_", " ").title(),
                    "file": f,
                    "count": len(content),
                    "path": str(path.absolute())
                })
        except:
            pass
            
    return {"datasets": datasets}

@router.get("/eval/graders")
async def get_graders():
    """Return the single unified grader (no selection needed)."""
    return {"graders": [
        {"id": "unified", "name": "Unified (All-in-One)", "description": "Comprehensive evaluation: content, tools, sources, reasoning"},
    ]}

@router.post("/eval/run")
async def run_eval(request: RunEvalRequest):
    try:
        from evals.graders import UnifiedGrader
        
        # Always use the Unified grader
        grader = UnifiedGrader(pass_threshold=0.6)
        
        # Load dataset and run
        runner = EvalRunner.from_json(
            name="Manual Run",
            agent=ResearchAgentAdapter(),
            path=request.dataset,
            grader=grader,
        )
        
        # Run
        summary = await runner.run()
        
        return summary.to_dict()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


