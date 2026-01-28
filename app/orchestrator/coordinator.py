"""
Multi-agent research coordinator.
Orchestrates the lifecycle: Plan -> Research -> Critique -> Revise.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional
import uuid

# Import Agents
from app.agents.researcher import ResearcherAgent
from app.agents.critic import CriticAgent
from app.agents.reviser import ReviserAgent

# Import Infrastructure
from app.database.connection import db_manager
from app.llm.client import get_llm_client

# Import Models
from app.models.research import (
    ResearchTask,
    ResearchQuery,
    ResearchStatus,
    AgentMessage,
    AgentType
)

logger = logging.getLogger(__name__)

class ResearchCoordinator:
    """
    The 'Brain' of the operation. 
    Manages the state machine and data persistence.
    """
    
    def __init__(self):
        # Initialize Agents
        self.researcher = ResearcherAgent()
        self.critic = CriticAgent()
        self.reviser = ReviserAgent()
        
        # Configuration
        self.min_quality_score = 6.5  # Lowered from 7.5 for more reliable completion
        self.db = db_manager 
        
        # Observers for real-time updates (e.g. WebSockets)
        self._observers = []

    def register_observer(self, callback):
        """Register a callback for real-time events."""
        self._observers.append(callback)

    async def _notify_observers(self, event_type: str, data: dict):
        """Notify all observers of an event."""
        for callback in self._observers:
            await callback(event_type, data) 

    async def initialize(self) -> bool:
        """Warm up the LLM and DB connections."""
        try:
            # 1. Init LLM
            client = await get_llm_client()
            if not await client.initialize():
                return False
                
            # 2. Init DB
            if not await self.db.initialize():
                return False
                
            return True
        except Exception as e:
            logger.error(f"Coordinator Initialization Failed: {e}")
            return False

    # --- Phase 1: API Call (Fast) ---
    async def create_task(self, query: ResearchQuery) -> str:
        """
        Creates the task record in DB and returns ID immediately.
        """
        # Create the initial state object
        task = ResearchTask(
            query=query,
            status=ResearchStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        
        # Persist to DB (this generates the UUID)
        task_id = await self.db.create_task(task)
        
        if not task_id:
            raise RuntimeError("Failed to create task in DB")
            
        logger.info(f"Task created: {task_id}")
        return task_id

    # --- Phase 2: Background Worker (Slow) ---
    async def start_workflow(self, task_id: str):
        """
        The main loop. Runs in the background (fire-and-forget).
        """
        logger.info(f"Starting workflow for Task {task_id}")
        
        # 1. Re-hydrate Task from DB
        task = await self.db.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found! Aborting.")
            return

        try:
            # --- PHASE 1: RESEARCH ---
            await self._update_status(task_id, ResearchStatus.IN_PROGRESS)
            await self._log(task_id, AgentType.RESEARCHER, "Starting Deep Research...")
            
            # The Researcher now modifies the task object directly (adds plan & current_report)
            report = await self.researcher.process(task)
            
            # Persist Plan (generated during research)
            if task.plan:
                await self.db.save_plan(task_id, task.plan)
                await self._log(task_id, AgentType.RESEARCHER, f"Research plan saved: {len(task.plan.search_queries)} queries")
            
            # Log tools called (for evaluation tracking)
            if task.tools_called:
                tool_names = [t.tool_name for t in task.tools_called]
                await self._log(task_id, AgentType.RESEARCHER, f"[TOOLS_USED] {', '.join(tool_names)}")
                for tool_record in task.tools_called:
                    await self._log(task_id, AgentType.RESEARCHER, 
                        f"[TOOL_CALL] {tool_record.tool_name}({tool_record.query[:50]}...) -> {tool_record.result_count} results")
            
            # Persist Raw Search Results
            if task.raw_search_results:
                await self.db.save_raw_search_results(task_id, task.raw_search_results)
                await self._log(task_id, AgentType.RESEARCHER, f"Saved {len(task.raw_search_results)} raw search results")
            
            # Persist Draft
            await self.db.save_report(task_id, report)
            await self._log(task_id, AgentType.RESEARCHER, "Draft v1 generated.")

            # Update local task object for the next phase
            task.current_report = report

            # --- PHASE 2: CRITIQUE / REVISE LOOP ---
            await self._enter_refinement_loop(task)
            
            # --- PHASE 3: FINALIZE ---
            await self._update_status(task_id, ResearchStatus.COMPLETED)
            await self._log(task_id, AgentType.RESEARCHER, "Workflow Completed Successfully.")
            
        except Exception as e:
            logger.error(f"Workflow Failed: {e}")
            traceback.print_exc()
            await self._update_status(task_id, ResearchStatus.FAILED)
            await self._log(task_id, AgentType.RESEARCHER, f"CRITICAL ERROR: {str(e)}")

    async def _enter_refinement_loop(self, task: ResearchTask):
        """
        Cycles between Critic and Reviser until quality is met.
        """
        loop_count = 0
        max_loops = 1  # Single revision only
        
        while loop_count < max_loops:
            try:
                # 1. CRITIQUE
                await self._update_status(task.id, ResearchStatus.REVIEWING)
                
                # Critic reads task.current_report
                feedback = await self.critic.process(task)
                
                # Save feedback & Update local state
                await self.db.save_feedback(task.id, feedback)
                task.feedback_history.append(feedback)
                
                await self._log(task.id, AgentType.CRITIC, f"Round {loop_count+1} Score: {feedback.overall_score}/10")

                # Check Exit Condition
                if feedback.overall_score >= self.min_quality_score:
                    await self._log(task.id, AgentType.CRITIC, "Quality Gate Passed.")
                    return

                # 2. REVISE
                await self._update_status(task.id, ResearchStatus.REVISING)
                await self._log(task.id, AgentType.REVISER, "Implementing improvements...")
                
                # Reviser reads task.current_report + task.feedback_history
                new_report = await self.reviser.process(task)
                
                # Save New Draft & Update local state
                await self.db.save_report(task.id, new_report)
                task.current_report = new_report
                
                # Increment revision count in database
                await self.db.increment_revision_count(task.id)
                task.revision_count += 1
                await self._log(task.id, AgentType.REVISER, f"Revision {task.revision_count} completed.")
                
                loop_count += 1
                
            except Exception as e:
                logger.error(f"Error in refinement loop (round {loop_count + 1}): {e}")
                await self._log(task.id, AgentType.CRITIC, f"Refinement error: {str(e)[:100]}. Continuing with current report.")
                # Break out of loop on error but don't fail the entire workflow
                break

        await self._log(task.id, AgentType.RESEARCHER, "Refinement phase completed. Finalizing report.")

    # --- Helpers ---

    async def _update_status(self, task_id: str, status: ResearchStatus):
        await self.db.update_task_status(task_id, status)
        await self._notify_observers("status_update", {
            "task_id": task_id,
            "status": status.value
        })

    async def _log(self, task_id: str, agent: AgentType, msg: str):
        entry = AgentMessage(
            agent_type=agent, 
            message=msg,
            timestamp=datetime.now(timezone.utc)
        )
        await self.db.log_agent_message(task_id, entry)
        await self._notify_observers("log_message", {
            "task_id": task_id,
            "agent": agent.value,
            "message": msg,
            "timestamp": entry.timestamp.isoformat()
        })

    async def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """ReadOnly access for the API polling endpoint."""
        return await self.db.get_task(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancels a running task by updating its status to 'failed' (or 'cancelled').
        Note: Python asyncio tasks are hard to kill externally. 
        This mostly just flags it in the DB so the UI stops polling.
        """
        task = await self.db.get_task(task_id)
        if not task or task.status in [ResearchStatus.COMPLETED, ResearchStatus.FAILED]:
            return False
            
        # Update DB status
        await self._update_status(task_id, ResearchStatus.FAILED)
        await self._log(task_id, AgentType.PLANNER, "Task cancelled by user request.")
        return True