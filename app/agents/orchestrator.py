"""
Orchestrator for Multi-Agent Intelligent Tutoring System.

The orchestrator coordinates all 6 specialized agents using LangGraph's StateGraph.
It maintains a shared state that flows between agents and ensures atomic updates
to the user document.

Architecture:
    - StateGraph manages workflow
    - Each agent is a node in the graph
    - State flows through nodes sequentially or conditionally
    - Orchestrator is the only component that writes to the database

Triggers:
    - on_submission: After code submission
    - on_hint_request: User asks for help
    - on_session_check: Background engagement monitoring
"""

from typing import TypedDict, Optional, Dict, Any, Literal
from datetime import datetime
import logging

from langgraph.graph import StateGraph, END
from app.models.user import User
from app.models.learner_state import LearnerState
from app.crud.user import UserCRUD
from app.db.database import get_db
from app.agents.feedback_agent import get_feedback_agent
from app.utils.user_profiling import calculate_user_proficiency

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class OrchestratorState(TypedDict):
    """
    Shared state that flows through all agents.
    
    This is the single source of truth during agent execution.
    All agents read from and write to this state.
    """
    # Core identifiers
    user_key: str
    trigger: Literal["submission", "hint_request", "session_check"]
    
    # User data (loaded from database)
    user: Optional[User]
    learner_state: Optional[LearnerState]
    memory: Optional[str]
    agent_data: Optional[Dict[str, Any]]
    
    # Context for current workflow
    context: Dict[str, Any]  # Trigger-specific data (e.g., submission_id)
    
    # Agent outputs (accumulated during workflow)
    agent_outputs: Dict[str, Any]
    
    # Error handling
    errors: list[str]
    
    # Next action (for routing)
    next_action: Optional[str]


# ============================================================================
# ORCHESTRATOR CLASS
# ============================================================================

class IntelliTOrchestrator:
    """
    Central orchestrator for the multi-agent system.
    
    Responsibilities:
    - Load user data from database
    - Route to appropriate agents based on trigger
    - Coordinate agent execution
    - Save updated state back to database
    - Handle errors gracefully
    """
    
    def __init__(self):
        """Initialize orchestrator with empty workflow."""
        self.workflow: Optional[StateGraph] = None
        self.compiled_workflow = None
        
        logger.info("🎯 Orchestrator initialized")
    
    def build_workflow(self):
        """
        Build the LangGraph StateGraph workflow.
        
        Workflow structure:
        
            START
              ↓
          load_user
              ↓
          route_trigger → submission_flow / hint_flow / session_flow
              ↓
          save_state
              ↓
            END
        
        Note: Actual agent nodes will be added in later phases.
        """
        workflow = StateGraph(OrchestratorState)
        
        # Add nodes
        workflow.add_node("load_user", self._load_user_node)
        workflow.add_node("route_trigger", self._route_trigger_node)
        workflow.add_node("feedback", self._feedback_node)
        workflow.add_node("save_state", self._save_state_node)
        
        # Add edges
        workflow.set_entry_point("load_user")
        workflow.add_edge("load_user", "route_trigger")
        
        # Conditional routing based on trigger
        workflow.add_conditional_edges(
            "route_trigger",
            self._should_run_feedback,
            {
                "feedback": "feedback",
                "skip": "save_state"
            }
        )
        
        workflow.add_edge("feedback", "save_state")
        workflow.add_edge("save_state", END)
        
        self.workflow = workflow
        self.compiled_workflow = workflow.compile()
        
        logger.info("✅ Workflow built successfully")
    
    # ========================================================================
    # WORKFLOW NODES
    # ========================================================================
    
    def _load_user_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        Load user data from database.
        
        Populates state with:
        - user: Full user object
        - learner_state: Current learning state
        - memory: Agent memory string
        - agent_data: Agent metadata
        """
        user_key = state["user_key"]
        
        logger.info(f"📥 Loading user: {user_key}")
        
        try:
            # Get database connection
            db = get_db()
            user_crud = UserCRUD(db)
            
            # Fetch user
            user_in_db = user_crud.get_user_by_key(user_key)
            
            if not user_in_db:
                logger.error(f"❌ User not found: {user_key}")
                return {
                    "errors": [*state.get("errors", []), f"User {user_key} not found"],
                    "next_action": "error"
                }
            
            # Convert UserInDB to User (API model)
            user = User.model_validate(user_in_db.model_dump())
            
            logger.info(f"✅ User loaded: {user.name} ({user.key})")
            
            return {
                "user": user,
                "learner_state": user.learner_state,
                "memory": user.memory,
                "agent_data": user.agent_data or {},
                "next_action": "route"
            }
            
        except Exception as e:
            logger.exception(f"❌ Error loading user: {e}")
            return {
                "errors": [*state.get("errors", []), f"Failed to load user: {str(e)}"],
                "next_action": "error"
            }
    
    def _route_trigger_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        Route to appropriate workflow based on trigger type.
        """
        trigger = state["trigger"]
        user = state.get("user")
        
        # Skip if user failed to load
        if not user:
            logger.error("❌ Cannot route - user not loaded")
            return {"next_action": "error"}
        
        logger.info(f"🔀 Routing trigger: {trigger} for user {user.key}")
        
        # Calculate user proficiency for adaptive behavior
        topics = state.get("context", {}).get("topics", [])
        proficiency_data = calculate_user_proficiency(user, topics)
        
        logger.info(
            f"📊 User proficiency: {proficiency_data['overall_score']:.2f} "
            f"({proficiency_data['recommendation']})"
        )
        
        return {
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                "routing": f"Triggered {trigger} workflow",
                "proficiency": proficiency_data
            },
            "next_action": trigger  # Will be used for conditional routing
        }
    
    def _should_run_feedback(self, state: OrchestratorState) -> str:
        """
        Conditional edge function to determine if feedback should run.
        """
        next_action = state.get("next_action")
        
        if next_action == "hint_request":
            return "feedback"
        else:
            return "skip"
    
    async def _feedback_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        Generate adaptive pedagogical hint using Feedback Agent.
        
        Uses user proficiency to adjust hint difficulty.
        """
        user = state["user"]
        context = state["context"]
        proficiency = state["agent_outputs"].get("proficiency", {})
        
        logger.info(f"💡 Running Feedback Agent for user {user.key}")
        
        try:
            # Get hint parameters from context
            problem_statement = context.get("problem_statement", "")
            user_code = context.get("code", "")
            error_message = context.get("error_message")
            hint_level = context.get("hint_level", 2)
            topics = context.get("topics", [])
            
            # Get feedback agent
            feedback_agent = get_feedback_agent()
            
            # Generate hint with proficiency adjustment
            hint_result = await feedback_agent.generate_hint(
                problem_statement=problem_statement,
                user_code=user_code,
                error_message=error_message,
                hint_level=hint_level,
                topics=topics,
                proficiency_score=proficiency.get("overall_score")
            )
            
            logger.info(
                f"✅ Hint generated: Level {hint_level} "
                f"(adjusted for proficiency {proficiency.get('overall_score', 0):.2f})"
            )
            
            return {
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    "hint": hint_result
                },
                "next_action": "save"
            }
            
        except Exception as e:
            logger.exception(f"❌ Feedback Agent failed: {e}")
            return {
                "errors": [
                    *state.get("errors", []),
                    f"Feedback generation failed: {str(e)}"
                ],
                "next_action": "error"
            }
    
    def _save_state_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        Save updated state back to database.
        
        Only saves if there were actual changes (detected by comparing state).
        This is the ONLY place where user document gets updated.
        """
        user = state["user"]
        
        # Check if there were errors
        if state.get("errors"):
            logger.warning(f"⚠️ Skipping save due to errors: {state['errors']}")
            return {"next_action": "complete"}
        
        logger.info(f"💾 Saving state for user: {user.key}")
        
        try:
            # Get database connection
            db = get_db()
            user_crud = UserCRUD(db)
            
            # Prepare updates
            updates = {}
            
            # Check what changed
            if state.get("learner_state") != user.learner_state:
                updates["learner_state"] = state["learner_state"].model_dump(mode='json') if state.get("learner_state") else None
            
            if state.get("memory") != user.memory:
                updates["memory"] = state.get("memory")
            
            if state.get("agent_data") != user.agent_data:
                updates["agent_data"] = state.get("agent_data")
            
            # Save if there are updates
            if updates:
                updates["updated_at"] = datetime.utcnow()
                user_crud.update_user_fields(user.key, updates)
                logger.info(f"✅ Saved {len(updates)} field(s) for user {user.key}")
            else:
                logger.info(f"ℹ️ No changes to save for user {user.key}")
            
            return {"next_action": "complete"}
            
        except Exception as e:
            logger.exception(f"❌ Error saving state: {e}")
            return {
                "errors": [*state.get("errors", []), f"Failed to save state: {str(e)}"],
                "next_action": "error"
            }
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    def invoke(
        self,
        user_key: str,
        trigger: Literal["submission", "hint_request", "session_check"],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke the orchestrator for a user (synchronous).
        
        For async workflows (like feedback), use ainvoke() instead.
        
        Args:
            user_key: User's database key
            trigger: What triggered this workflow
            context: Additional context (e.g., submission_id)
            
        Returns:
            Final state after workflow execution
        """
        if not self.compiled_workflow:
            raise RuntimeError("Workflow not built. Call build_workflow() first.")
        
        logger.info(f"🚀 Invoking orchestrator: {trigger} for {user_key}")
        
        # Initialize state
        initial_state: OrchestratorState = {
            "user_key": user_key,
            "trigger": trigger,
            "user": None,
            "learner_state": None,
            "memory": None,
            "agent_data": None,
            "context": context or {},
            "agent_outputs": {},
            "errors": [],
            "next_action": None
        }
        
        try:
            # Run workflow
            final_state = self.compiled_workflow.invoke(initial_state)
            
            logger.info(f"✅ Workflow completed for {user_key}")
            
            return final_state
            
        except Exception as e:
            logger.exception(f"❌ Workflow failed for {user_key}: {e}")
            return {
                **initial_state,
                "errors": [f"Workflow execution failed: {str(e)}"],
                "next_action": "error"
            }
    
    async def ainvoke(
        self,
        user_key: str,
        trigger: Literal["submission", "hint_request", "session_check"],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke the orchestrator for a user (asynchronous).
        
        Use this for workflows with async agents (like feedback).
        
        Args:
            user_key: User's database key
            trigger: What triggered this workflow
            context: Additional context
            
        Returns:
            Final state after workflow execution
        """
        if not self.compiled_workflow:
            raise RuntimeError("Workflow not built. Call build_workflow() first.")
        
        logger.info(f"🚀 Async invoking orchestrator: {trigger} for {user_key}")
        
        # Initialize state
        initial_state: OrchestratorState = {
            "user_key": user_key,
            "trigger": trigger,
            "user": None,
            "learner_state": None,
            "memory": None,
            "agent_data": None,
            "context": context or {},
            "agent_outputs": {},
            "errors": [],
            "next_action": None
        }
        
        try:
            # Run workflow asynchronously
            final_state = await self.compiled_workflow.ainvoke(initial_state)
            
            logger.info(f"✅ Async workflow completed for {user_key}")
            
            return final_state
            
        except Exception as e:
            logger.exception(f"❌ Async workflow failed for {user_key}: {e}")
            return {
                **initial_state,
                "errors": [f"Workflow execution failed: {str(e)}"],
                "next_action": "error"
            }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_orchestrator() -> IntelliTOrchestrator:
    """
    Factory function to create and build an orchestrator.
    
    Returns:
        Fully configured orchestrator ready to invoke
        
    Example:
        >>> orchestrator = create_orchestrator()
        >>> result = orchestrator.invoke("user123", "submission")
    """
    orchestrator = IntelliTOrchestrator()
    orchestrator.build_workflow()
    return orchestrator


# Global orchestrator instance (singleton pattern)
_orchestrator_instance: Optional[IntelliTOrchestrator] = None


def get_orchestrator() -> IntelliTOrchestrator:
    """
    Get or create the global orchestrator instance.
    
    This ensures we only compile the workflow once for performance.
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = create_orchestrator()
    
    return _orchestrator_instance

