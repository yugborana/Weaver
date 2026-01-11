"""
Supabase Database Manager.
Optimized for Document-Oriented Architecture (JSONB).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from supabase import create_client, Client
from app.config import settings
from app.models.research import (
    ResearchTask,
    ResearchReport,
    CritiqueFeedback,
    AgentMessage,
    ResearchStatus
)

logger = logging.getLogger(__name__)

class SupabaseManager:
    """
    Manages Supabase operations.
    Treats 'ResearchTask' as the single source of truth (Document Store pattern).
    """
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the client."""
        try:
            key = settings.supabase_service_role_key or settings.supabase_key
            self.client = create_client(settings.supabase_url, key)
            self._initialized = True
            logger.info("Supabase Connected.")
            return True
        except Exception as e:
            logger.error(f"Supabase Init Failed: {e}")
            return False

    def _ensure_initialized(self):
        if not self._initialized:
            raise RuntimeError("DB Not Initialized.")

    # --- TASK OPERATIONS ---

    async def create_task(self, task: ResearchTask) -> Optional[str]:
        """
        Creates a new task. Returns the Task ID.
        """
        self._ensure_initialized()
        try:
            # CRITICAL FIX: Explicitly exclude fields that are NOT in the 'research_tasks' table
            # 1. 'id': Let the database generate the UUID
            # 2. 'agent_messages': These belong in the separate 'task_logs' table
            # 3. 'agent_logs': Just in case your model uses this name alias
            data = task.model_dump(
                mode='json', 
                exclude={'id', 'agent_messages', 'agent_logs'} 
            ) 
            
            # Insert and return ID
            res = self.client.table("research_tasks").insert(data).execute()
            
            if res.data:
                new_id = res.data[0]['id']
                logger.info(f"Task Created: {new_id}")
                return new_id
            
            # Log the full error response from Supabase if it fails
            logger.error(f"Supabase Insert Failed. Response: {res}")
            return None
            
        except Exception as e:
            logger.error(f"Create Task Exception: {e}") 
            return None

    async def get_task(self, task_id: str) -> Optional[ResearchTask]:
        try:
            # Fetch task from research_tasks table
            res = self.client.table("research_tasks")\
                .select("*")\
                .eq("id", task_id)\
                .single()\
                .execute()

            if res.data:
                # Note: agent_logs are stored in separate task_logs table, not fetched here
                task = ResearchTask(**res.data)
                return task
            return None
        except Exception as e:
            logger.error(f"Get Task Failed: {e}")
            return None

    async def update_task_status(self, task_id: str, status: ResearchStatus):
        """Simple status update."""
        self._ensure_initialized()
        try:
            self.client.table("research_tasks").update({
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", task_id).execute()
        except Exception as e:
            logger.error(f"Status Update Failed: {e}")

    # --- STATE UPDATES (Report & Feedback) ---
    
    async def save_report(self, task_id: str, report: ResearchReport):
        """
        Updates the 'current_report' JSONB column.
        """
        self._ensure_initialized()
        try:
            # Dump the report to a dict
            report_json = report.model_dump(mode='json')
            
            self.client.table("research_tasks").update({
                "current_report": report_json,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", task_id).execute()
            
            logger.info(f"Report saved for Task {task_id}")
            
        except Exception as e:
            logger.error(f"Save Report Failed: {e}")

    async def save_feedback(self, task_id: str, feedback: CritiqueFeedback):
        """
        Appends feedback to the 'feedback_history' array.
        Uses a read-modify-write approach (Simpler for this scale).
        """
        self._ensure_initialized()
        try:
            # 1. Fetch current history (Optimistic locking is overkill here)
            # In a high-concurrency app, use a Postgres RPC function instead.
            task = await self.get_task(task_id)
            if not task:
                return

            # 2. Append new feedback
            current_history = task.feedback_history
            current_history.append(feedback)
            
            # 3. Update DB
            history_json = [f.model_dump(mode='json') for f in current_history]
            
            self.client.table("research_tasks").update({
                "feedback_history": history_json,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", task_id).execute()
            
            logger.info(f"Feedback saved for Task {task_id}")

        except Exception as e:
            logger.error(f"Save Feedback Failed: {e}")

    # --- LOGGING ---

    async def log_agent_message(self, task_id: str, message: AgentMessage):
        """
        Inserts into the separate 'task_logs' table.
        """
        self._ensure_initialized()
        try:
            # Map AgentMessage fields to table columns
            data = {
                'task_id': task_id,
                'agent_type': message.agent_type.value,  # Enum to string
                'message': message.message,
                'metadata': {
                    'step_name': message.step_name,
                    'timestamp': message.timestamp.isoformat()
                }
            }

            # Ensure we use the correct table name from schema
            self.client.table("task_logs").insert(data).execute()

        except Exception as e:
            # Don't crash the app if logging fails
            logger.warning(f"Logging Failed: {e}")

# Global Instance
db_manager = SupabaseManager()