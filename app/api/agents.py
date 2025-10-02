"""
API endpoints for AI agents.

This module provides HTTP endpoints for interacting with the multi-agent system.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.models.user import User
from app.api.auth import get_current_user
from app.crud.roadmap import RoadmapCRUD
from app.crud.session import SessionCRUD
from app.db.database import get_db
from app.agents.feedback_agent import get_feedback_agent
from app.agents.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class HintRequest(BaseModel):
    """Request for a hint."""
    question_id: str = Field(description="Question/problem ID from roadmap")
    code: str = Field(description="User's current code", default="")
    hint_level: int = Field(description="Hint level (1-5)", ge=1, le=5)
    session_id: Optional[str] = Field(default=None, description="Active session ID")


class HintResponse(BaseModel):
    """Response containing the generated hint."""
    hint_text: str
    hint_level: int
    level_name: str
    hints_used_total: int = Field(description="Total hints used in this session")
    hints_remaining: int = Field(default=0, description="Hints remaining in this session")
    success: bool


# ============================================================================
# DEPENDENCIES
# ============================================================================

def get_roadmap_crud():
    """Get RoadmapCRUD instance."""
    db = get_db()
    return RoadmapCRUD(db)


def get_session_crud():
    """Get SessionCRUD instance."""
    db = get_db()
    return SessionCRUD(db)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/hint", response_model=HintResponse)
async def get_hint(
    request: HintRequest,
    current_user: User = Depends(get_current_user),
    roadmap_crud: RoadmapCRUD = Depends(get_roadmap_crud),
    session_crud: SessionCRUD = Depends(get_session_crud)
):
    """
    Generate a pedagogical hint for the user's code.
    
    The hint level determines the specificity:
    - Level 1: Metacognitive (problem type)
    - Level 2: Conceptual (data structures/algorithms)
    - Level 3: Strategic (approach/technique)
    - Level 4: Structural (code structure)
    - Level 5: Targeted (specific code issues)
    
    Args:
        request: Hint request with question ID, code, and level
        current_user: Authenticated user
        
    Returns:
        Generated hint and metadata
    """
    logger.info(
        f"🤔 Hint request from user {current_user.key}: "
        f"Question={request.question_id}, Level={request.hint_level}"
    )
    
    try:
        # 1. Fetch question from roadmap (using _key directly)
        try:
            question_doc = roadmap_crud.collection.get(request.question_id)
            if question_doc:
                from app.models.roadmap import RoadmapItem
                question = RoadmapItem.model_validate(question_doc)
            else:
                question = None
        except Exception as e:
            logger.warning(f"Failed to fetch question: {e}")
            question = None
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question {request.question_id} not found"
            )
        
        # 2. Extract problem statement
        problem_statement = question.problem_statement_text or question.original_title or ''
        
        if not problem_statement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question has no problem statement"
            )
        
        # 3. Get last error message if session exists
        error_message = None
        if request.session_id:
            try:
                session = session_crud.get_session(request.session_id)
                if session and hasattr(session, 'last_error'):
                    error_message = session.last_error
            except Exception as e:
                logger.warning(f"Could not fetch session error: {e}")
        
        # 4. Get feedback agent
        feedback_agent = get_feedback_agent()
        
        # 5. Generate hint
        hint_result = await feedback_agent.generate_hint(
            problem_statement=problem_statement,
            user_code=request.code,
            error_message=error_message,
            hint_level=request.hint_level,
            topics=question.topics or []
        )
        
        if not hint_result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate hint"
            )
        
        # 6. Track hint usage in session (if session exists)
        hints_used = 1
        if request.session_id:
            try:
                from app.models.session import CodingSessionUpdate
                session = session_crud.get_session(request.session_id)
                if session:
                    analytics = session.analytics.copy() if session.analytics else {}
                    hints_used = analytics.get('hints_used', 0) + 1
                    analytics['hints_used'] = hints_used
                    
                    update_data = CodingSessionUpdate(
                        analytics=analytics,
                        last_activity=datetime.utcnow()
                    )
                    session_crud.update_session(request.session_id, update_data)
            except Exception as e:
                logger.warning(f"Could not update hint count: {e}")
        
        logger.info(
            f"✅ Hint generated for user {current_user.key}: "
            f"Level {request.hint_level} ({len(hint_result['hint_text'])} chars)"
        )
        
        return HintResponse(
            hint_text=hint_result['hint_text'],
            hint_level=hint_result['hint_level'],
            level_name=hint_result['level_name'],
            hints_used_total=hints_used,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error generating hint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate hint: {str(e)}"
        )


@router.post("/hint-orchestrated", response_model=HintResponse)
async def get_hint_orchestrated(
    request: HintRequest,
    current_user: User = Depends(get_current_user),
    roadmap_crud: RoadmapCRUD = Depends(get_roadmap_crud)
):
    """
    Generate an ADAPTIVE pedagogical hint via orchestrator.
    
    This endpoint uses the orchestrator to:
    1. Calculate user proficiency from multiple metrics
    2. Adjust hint difficulty based on proficiency
    3. Generate personalized hint
    
    Proficiency calculation weighs:
    - Topic mastery (40%)
    - Expertise rank (25%)
    - Skill level (20%)
    - Success rate (10%)
    - Streak (5%)
    
    Args:
        request: Hint request with question ID, code, and level
        current_user: Authenticated user
        
    Returns:
        Adaptive hint with proficiency metadata
    """
    logger.info(
        f"🎯 Orchestrated hint request from user {current_user.key}: "
        f"Question={request.question_id}, Level={request.hint_level}"
    )
    
    try:
        # 1. Get session and check hint limit
        from app.models.session import CodingSessionUpdate
        session_crud = SessionCRUD(get_db())
        session = session_crud.get_session(request.session_id) if request.session_id else None
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active session found"
            )
        
        # Check current hints used and calculate next level
        analytics = session.analytics if session.analytics else {}
        current_hints_used = analytics.get('hints_used', 0)
        
        # Enforce 5-hint limit
        if current_hints_used >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 5 hints per session reached"
            )
        
        # Auto-calculate hint level (1-5)
        hint_level = current_hints_used + 1
        
        logger.info(f"📊 Session hints: {current_hints_used}/5 used, generating level {hint_level}")
        
        # 2. Fetch question
        question_doc = roadmap_crud.collection.get(request.question_id)
        if not question_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question {request.question_id} not found"
            )
        
        from app.models.roadmap import RoadmapItem
        question = RoadmapItem.model_validate(question_doc)
        
        problem_statement = question.problem_statement_text or question.original_title or ''
        
        # 3. Prepare context for orchestrator with calculated hint level
        context = {
            "problem_statement": problem_statement,
            "code": request.code,
            "error_message": None,
            "hint_level": hint_level,  # Use calculated level, not request level
            "topics": question.topics or []
        }
        
        # 3. Invoke orchestrator (async)
        orchestrator = get_orchestrator()
        result = await orchestrator.ainvoke(
            user_key=current_user.key,
            trigger="hint_request",
            context=context
        )
        
        # 4. Extract results
        if result.get("errors"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Hint generation failed: {result['errors']}"
            )
        
        hint_data = result["agent_outputs"].get("hint", {})
        proficiency = result["agent_outputs"].get("proficiency", {})
        
        if not hint_data.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Hint generation failed"
            )
        
        # 5. Update session analytics with new hint count
        try:
            analytics_update = analytics.copy()
            analytics_update['hints_used'] = hint_level  # Set to the level we just used
            
            update_data = CodingSessionUpdate(
                analytics=analytics_update,
                last_activity=datetime.utcnow()
            )
            updated_session = session_crud.update_session(request.session_id, update_data)
            
            if not updated_session:
                logger.error(f"Failed to update session {request.session_id}")
            else:
                logger.info(f"✅ Session updated: hints_used = {hint_level}")
                
        except Exception as e:
            logger.exception(f"❌ Error updating hint count: {e}")
            # Don't fail the request if analytics update fails
            pass
        
        logger.info(
            f"✅ Adaptive hint generated: Level {hint_data['hint_level']}, "
            f"Proficiency {proficiency.get('overall_score', 0):.2f}"
        )
        
        return HintResponse(
            hint_text=hint_data['hint_text'],
            hint_level=hint_level,  # Return the calculated level
            level_name=hint_data['level_name'],
            hints_used_total=hint_level,  # Total hints used including this one
            hints_remaining=5 - hint_level,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error in orchestrated hint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate hint: {str(e)}"
        )


@router.post("/chat")
async def chat_with_assistant(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the AI assistant about the coding problem.
    
    Args:
        request: Chat request with message, question_id, code, and history
        current_user: Authenticated user
        
    Returns:
        AI assistant's response
    """
    logger.info(f"💬 Chat request from user {current_user.key}")
    
    try:
        message = request.get("message", "")
        question_id = request.get("question_id")
        code = request.get("code", "")
        history = request.get("history", [])
        
        if not message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Build context for the chat
        context_parts = [
            "You are an AI teaching assistant helping a student with coding problems.",
            "Be helpful, concise, and pedagogical. Guide them towards the solution without giving it away.",
            ""
        ]
        
        if question_id:
            context_parts.append(f"Current problem ID: {question_id}")
        
        if code:
            context_parts.append(f"Student's current code:\n```\n{code}\n```\n")
        
        context_parts.append(f"Student's question: {message}")
        
        # Add conversation history for context
        if history:
            context_parts.append("\nPrevious conversation:")
            for msg in history[-3:]:  # Last 3 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_parts.append(f"{role.capitalize()}: {content}")
        
        prompt = "\n".join(context_parts)
        
        # Use Gemini to generate response
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.core.config import settings
        
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            api_key=settings.GEMINI_API_KEY,
            temperature=0.7
        )
        
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()
        
        logger.info(f"✅ Chat response generated for user {current_user.key}")
        
        return {
            "success": True,
            "message": response_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error in chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Check if AI agents are configured and healthy.
    
    Returns:
        Status of agent configuration
    """
    from app.core.config import settings
    
    return {
        "gemini_configured": settings.GEMINI_API_KEY is not None,
        "model": settings.GEMINI_MODEL,
        "agents_available": ["feedback", "chat"],
        "orchestrator_ready": True
    }

