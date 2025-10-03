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
    print(f"\n{'='*80}")
    print(f"🎯 ORCHESTRATED HINT REQUEST")
    print(f"User: {current_user.key}")
    print(f"Question: {request.question_id}")
    print(f"Session: {request.session_id}")
    print(f"Code length: {len(request.code) if request.code else 0}")
    print(f"{'='*80}\n")
    
    logger.info(
        f"🎯 Orchestrated hint request from user {current_user.key}: "
        f"Question={request.question_id}, Level={request.hint_level}"
    )
    logger.info(f"🔍 DEBUG - Request data: question_id={request.question_id}, session_id={request.session_id}, code_length={len(request.code) if request.code else 0}")
    
    try:
        # 1. Get session and check hint limit
        from app.models.session import CodingSessionUpdate
        session_crud = SessionCRUD(get_db())
        
        logger.info(f"🔍 DEBUG - Fetching session with ID: {request.session_id}")
        session = session_crud.get_session(request.session_id) if request.session_id else None
        
        if not session:
            logger.error(f"❌ DEBUG - Session not found! session_id={request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active session found"
            )
        
        logger.info(f"✅ DEBUG - Session found: {session.session_id}, state={session.state}")
        
        # Check current hints used and calculate next level
        analytics = session.analytics if session.analytics else {}
        current_hints_used = analytics.get('hints_used', 0)
        
        logger.info(f"🔍 DEBUG - Session analytics: {analytics}")
        logger.info(f"🔍 DEBUG - Current hints used: {current_hints_used}")
        
        # Enforce 5-hint limit
        if current_hints_used >= 5:
            logger.warning(f"⚠️ DEBUG - Hint limit reached: {current_hints_used}/5")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 5 hints per session reached"
            )
        
        # Auto-calculate hint level (1-5)
        hint_level = current_hints_used + 1
        
        logger.info(f"📊 Session hints: {current_hints_used}/5 used, generating level {hint_level}")
        
        # 2. Fetch question
        logger.info(f"🔍 DEBUG - Fetching question: {request.question_id}")
        question_doc = roadmap_crud.collection.get(request.question_id)
        if not question_doc:
            logger.error(f"❌ DEBUG - Question not found: {request.question_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question {request.question_id} not found"
            )
        
        from app.models.roadmap import RoadmapItem
        question = RoadmapItem.model_validate(question_doc)
        
        problem_statement = question.problem_statement_text or question.original_title or ''
        logger.info(f"✅ DEBUG - Question loaded: {question.original_title}, problem_length={len(problem_statement)}")
        
        # 3. Prepare context for orchestrator with calculated hint level
        context = {
            "problem_statement": problem_statement,
            "code": request.code,
            "error_message": None,
            "hint_level": hint_level,  # Use calculated level, not request level
            "topics": question.topics or []
        }
        
        logger.info(f"🔍 DEBUG - Orchestrator context: hint_level={hint_level}, code_length={len(request.code) if request.code else 0}, topics={question.topics}")
        
        # 3. Invoke orchestrator (async)
        logger.info(f"🔍 DEBUG - Invoking orchestrator for user {current_user.key}...")
        print(f"🔍 About to call orchestrator.ainvoke()")
        orchestrator = get_orchestrator()
        print(f"🔍 Got orchestrator: {orchestrator}")
        result = await orchestrator.ainvoke(
            user_key=current_user.key,
            trigger="hint_request",
            context=context
        )
        print(f"🔍 Orchestrator returned: {type(result)}, keys: {result.keys() if result else 'None'}")
        
        logger.info(f"🔍 DEBUG - Orchestrator result keys: {result.keys()}")
        
        # 4. Extract results
        if result.get("errors"):
            logger.error(f"❌ DEBUG - Orchestrator errors: {result['errors']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Hint generation failed: {result['errors']}"
            )
        
        logger.info(f"🔍 DEBUG - Agent outputs: {result.get('agent_outputs', {}).keys()}")
        
        hint_data = result["agent_outputs"].get("hint", {})
        proficiency = result["agent_outputs"].get("proficiency", {})
        
        print(f"🔍 HINT DATA RECEIVED FROM ORCHESTRATOR:")
        print(f"  - hint_data keys: {hint_data.keys() if hint_data else 'None'}")
        print(f"  - hint_data full: {hint_data}")
        
        logger.info(f"🔍 DEBUG - Hint data: success={hint_data.get('success')}, hint_text_length={len(hint_data.get('hint_text', ''))}, hint_level={hint_data.get('hint_level')}")
        
        if not hint_data.get("success"):
            logger.error(f"❌ DEBUG - Hint generation failed, hint_data={hint_data}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Hint generation failed"
            )
        
        # 5. Update session analytics and save hint to chat history
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
            
            # Save hint to chat history
            session_crud.add_chat_message(
                request.session_id,
                role="assistant",
                content=hint_data['hint_text'],
                metadata={
                    "type": "hint",
                    "hint_level": hint_level,
                    "level_name": hint_data['level_name'],
                    "hints_used": hint_level
                }
            )
                
        except Exception as e:
            logger.exception(f"❌ Error updating session: {e}")
            # Don't fail the request if analytics update fails
            pass
        
        logger.info(
            f"✅ Adaptive hint generated: Level {hint_data['hint_level']}, "
            f"Proficiency {proficiency.get('overall_score', 0):.2f}"
        )
        
        response = HintResponse(
            hint_text=hint_data['hint_text'],
            hint_level=hint_level,  # Return the calculated level
            level_name=hint_data['level_name'],
            hints_used_total=hint_level,  # Total hints used including this one
            hints_remaining=5 - hint_level,
            success=True
        )
        
        print(f"\n{'='*80}")
        print(f"📤 RETURNING HINT RESPONSE")
        print(f"Hint text length: {len(response.hint_text)}")
        print(f"Hint level: {response.hint_level}")
        print(f"Hints remaining: {response.hints_remaining}")
        print(f"Hint preview: {response.hint_text[:100]}...")
        print(f"{'='*80}\n")
        
        logger.info(f"🔍 DEBUG - Response: hint_text_length={len(response.hint_text)}, hint_level={response.hint_level}, hints_remaining={response.hints_remaining}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ EXCEPTION in orchestrated hint: {type(e).__name__}: {str(e)}")
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
    Uses learner profiling to adapt responses to student's level.
    
    Args:
        request: Chat request with message, question_id, code, session_id, and history
        current_user: Authenticated user
        
    Returns:
        AI assistant's response adapted to student's proficiency
    """
    logger.info(f"💬 Chat request from user {current_user.key}")
    
    try:
        message = request.get("message", "")
        question_id = request.get("question_id")
        code = request.get("code", "")
        session_id = request.get("session_id")
        history = request.get("history", [])
        
        logger.info(f"📝 Chat request - Code length: {len(code)} characters")
        
        if not message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Get learner state and calculate proficiency
        from app.crud.learner_state import LearnerStateCRUD
        from app.crud.roadmap import RoadmapCRUD
        from app.utils.user_profiling import calculate_user_proficiency
        
        db = get_db()
        learner_crud = LearnerStateCRUD(db)
        roadmap_crud = RoadmapCRUD(db)
        
        learner_state = learner_crud.get_or_initialize(current_user.key)
        
        # Attach learner state to user object for proficiency calculation
        current_user.learner_state = learner_state
        
        # Get question data for proficiency calculation and context
        question_topics = []
        question_data = None
        if question_id:
            try:
                question_doc = roadmap_crud.collection.get(question_id)
                if question_doc:
                    if question_doc.get('topics'):
                        question_topics = question_doc['topics']
                    question_data = question_doc
            except Exception as e:
                logger.warning(f"Could not fetch question data: {e}")
        
        # Calculate user proficiency (0.0 to 1.0)
        proficiency_data = calculate_user_proficiency(
            current_user,
            question_topics
        )
        proficiency_score = proficiency_data.get('overall_score', 0.5)
        
        logger.info(f"📊 User proficiency: {proficiency_score:.2f}")
        
        # Analyze code state - check if user has written meaningful code
        stripped_code = code.strip()
        has_code = bool(stripped_code and len(stripped_code) > 10)  # Lowered threshold to catch early code
        
        # Format conversation history
        conversation_history = "No prior conversation"
        if history:
            history_lines = [f"{msg.get('role', 'user')}: {msg.get('content', '')[:100]}" for msg in history[-2:]]
            conversation_history = "\n".join(history_lines)
        
        # Format question section
        question_section = ""
        if question_data:
            title = question_data.get('title', 'Unknown Problem')
            difficulty = question_data.get('difficulty', 'Unknown')
            description = question_data.get('description', '')[:500]  # Truncate if too long
            
            question_section = f"""**Problem:** {title} ({difficulty})
**Description:** {description}"""
            
            # Add examples if available
            if question_data.get('examples'):
                examples = question_data['examples']
                if isinstance(examples, list) and len(examples) > 0:
                    example = examples[0]
                    if isinstance(example, dict):
                        input_val = example.get('input', '')
                        output_val = example.get('output', '')
                        question_section += f"\n**Example:** Input: {input_val} → Output: {output_val}"
        else:
            question_section = "**Problem:** (Question not loaded)"
        
        # Format code section - always show code if it exists, even if minimal
        code_section = ""
        if has_code:
            code_section = f"\n**Student's Current Code:**\n```\n{stripped_code[:400]}\n```\n"
            logger.info(f"✅ Including user's code in chat context ({len(stripped_code)} chars)")
        elif stripped_code:
            # Even if code is minimal/boilerplate, show it
            code_section = f"\n**Student's Current Code:**\n```\n{stripped_code}\n```\n(Note: This appears to be starting code or boilerplate)\n"
            logger.info(f"✅ Including minimal/boilerplate code in chat context ({len(stripped_code)} chars)")
        else:
            logger.info("ℹ️ No code provided in chat request")
        
        # Build adaptive pedagogical prompt
        prompt = f"""You are an AI teaching assistant helping a student with a coding problem. Adapt your teaching style to their level.

**Student Profile:**
- Proficiency: {proficiency_score:.2f}/1.0
- Skill Level: {current_user.skill_level or 'intermediate'}
- Expertise Rank: {current_user.expertise_rank or 'N/A'}

**Adaptation Guidelines:**

▸ IF proficiency < 0.3 (BEGINNER):
  - Use simple, encouraging language
  - Avoid jargon, explain concepts from first principles
  - Give concrete examples and analogies
  - Focus on one concept at a time
  - Be patient and supportive

▸ IF 0.3 <= proficiency < 0.6 (INTERMEDIATE):
  - Use standard programming terminology
  - Reference common patterns and techniques
  - Ask guiding questions to develop problem-solving skills
  - Balance explanation with discovery

▸ IF proficiency >= 0.6 (ADVANCED):
  - Use technical language and CS concepts
  - Challenge them with optimization considerations
  - Be concise, assume foundational knowledge
  - Focus on edge cases and efficiency

---

{question_section}
{code_section}

**Recent Conversation:**
{conversation_history}

**Student's Question:** "{message}"

---

**Your Response Guidelines:**
- Keep responses concise (2-4 sentences)
- Match complexity to their proficiency level
- You already know the problem, don't ask what they're working on
- **IMPORTANT: If code is provided above, ALWAYS reference and analyze it specifically**
- If code is empty or minimal, guide them on where to start
- Don't give away solutions, guide discovery
- Be specific about what you observe in their code or approach

Respond now:"""
        
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
        
        # Save chat messages to session history
        if session_id:
            try:
                session_crud = SessionCRUD(get_db())
                
                # Save user message
                session_crud.add_chat_message(
                    session_id,
                    role="user",
                    content=message,
                    metadata={"type": "chat"}
                )
                
                # Save assistant response
                session_crud.add_chat_message(
                    session_id,
                    role="assistant",
                    content=response_text,
                    metadata={"type": "chat"}
                )
                
                logger.info(f"✅ Chat messages saved to session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to save chat to session: {e}")
        
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


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get chat history for a session.
    
    Args:
        session_id: Session ID
        current_user: Authenticated user
        
    Returns:
        List of chat messages
    """
    try:
        db = get_db()
        session_crud = SessionCRUD(db)
        
        # Verify session belongs to user
        session = session_crud.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_key != current_user.key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        chat_history = session_crud.get_chat_history(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "messages": chat_history,
            "total": len(chat_history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
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

