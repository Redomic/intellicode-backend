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
    roadmap_crud: RoadmapCRUD = Depends(get_roadmap_crud)
):
    """
    Generate an adaptive pedagogical hint using the full ITS orchestrator.
    
    This endpoint:
    - Calculates user proficiency from 5 weighted metrics (40% topic mastery, 25% rank, etc.)
    - Auto-increments hint level (1→2→3→4→5) based on session hints_used
    - Enforces 5-hint limit per session
    - Includes last_run test failure context for accurate feedback
    - Updates learner state and memory
    
    Hint Levels (auto-calculated):
    1. Metacognitive - Problem type identification
    2. Conceptual - Data structures/algorithms  
    3. Strategic - Solution approach
    4. Structural - Code structure issues
    5. Targeted - Specific line-level feedback
    
    Returns:
        Adaptive hint with proficiency-adjusted difficulty
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
        
        # 3. Get last_run state from session (EXACTLY like chat endpoint)
        last_run_state = None
        if session and hasattr(session, 'last_run') and session.last_run:
            last_run_state = session.last_run  # Pass directly
            logger.info(f"📊 ORCHESTRATED - Retrieved last_run state: {last_run_state.get('status')}, {last_run_state.get('passed_count')}/{last_run_state.get('total_count')} passed")
            logger.info(f"📊 ORCHESTRATED - Test results: {last_run_state.get('test_results')}")
        else:
            logger.warning("⚠️ ORCHESTRATED - No last_run in session")
        
        # 4. Prepare context for orchestrator with calculated hint level
        context = {
            "problem_statement": problem_statement,
            "code": request.code,
            "error_message": None,
            "hint_level": hint_level,  # Use calculated level, not request level
            "topics": question.topics or [],
            "last_run_state": last_run_state  # Add last_run_state to context
        }
        
        logger.info(f"🔍 DEBUG - Orchestrator context: hint_level={hint_level}, code_length={len(request.code) if request.code else 0}, topics={question.topics}, has_last_run={last_run_state is not None}")
        
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
        code = request.get("code")
        session_id = request.get("session_id")
        history = request.get("history", [])
        
        logger.info(f"📝 Chat request received - message_length={len(message)}, code={'None' if code is None else len(code)}, question_id={question_id}, session_id={session_id}")
        
        if not message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # REQUIRE code - frontend should ALWAYS send code (at minimum boilerplate)
        if code is None or not code.strip():
            logger.error(f"❌ No code provided in chat request! Code value: {repr(code)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code is required. Frontend must send current code (including boilerplate)."
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
        
        # Code is guaranteed to exist at this point (validated above)
        stripped_code = code.strip()
        
        logger.info(f"💻 Code analysis: original_length={len(code)}, stripped_length={len(stripped_code)}")
        logger.info(f"💻 Code preview (first 100 chars): {stripped_code[:100]}")
        
        # Get last_run state from session if available
        last_run_context = ""
        if session_id:
            try:
                from app.crud.session import SessionCRUD
                from app.utils.user_profiling import format_last_run_context
                session_crud = SessionCRUD(db)
                session = session_crud.get_session(session_id)
                
                if session and hasattr(session, 'last_run') and session.last_run:
                    last_run_context = format_last_run_context(session.last_run)
                    if last_run_context:
                        logger.info(f"📊 Added last_run context to chat: {session.last_run.get('status')}")
            except Exception as e:
                logger.warning(f"Could not fetch last_run from session: {e}")
        
        # Format conversation history
        conversation_history = "No prior conversation"
        if history:
            history_lines = [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[-2:]]
            conversation_history = "\n".join(history_lines)
        
        # Format question section with correct field names for roadmap items
        question_section = ""
        if question_data:
            # Use correct roadmap field names
            title = question_data.get('leetcode_title') or question_data.get('original_title', 'Unknown Problem')
            difficulty = question_data.get('leetcode_difficulty', 'Unknown')
            description = question_data.get('problem_statement_text', '')[:800]  # Increased limit
            
            question_section = f"""<Problem>
Title: {title}
Difficulty: {difficulty}
Description: {description}"""
            
            # Add examples if available
            if question_data.get('examples'):
                examples = question_data['examples']
                if isinstance(examples, list) and len(examples) > 0:
                    example = examples[0]
                    if isinstance(example, dict):
                        input_val = example.get('input', '')
                        output_val = example.get('output', '')
                        question_section += f"\nExample: Input: {input_val} → Output: {output_val}"
            question_section += "\n</Problem>"
        else:
            question_section = "<Problem>(Question not loaded)</Problem>"
        
        # Format code section - code is REQUIRED and guaranteed to exist
        code_section = f"\n<StudentCode>\n{stripped_code}\n</StudentCode>\n"
        logger.info(f"✅ Including user's FULL code in chat context ({len(stripped_code)} chars)")
        
        # Build adaptive pedagogical prompt
        prompt = f"""You are an AI teaching assistant helping a student with a coding problem. Adapt your teaching style to their level.

<StudentProfile>
- Proficiency: {proficiency_score:.2f}/1.0
- Skill Level: {current_user.skill_level or 'intermediate'}
- Expertise Rank: {current_user.expertise_rank or 'N/A'}
</StudentProfile>

<AdaptationGuidelines>
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
</AdaptationGuidelines>

<Context>
{question_section}
{code_section}{last_run_context}

<RecentConversation>
{conversation_history}
</RecentConversation>

<StudentQuestion>
{message}
</StudentQuestion>
</Context>

<Guidelines>
- Keep responses concise (2-4 sentences)
- Match complexity to their proficiency level
- You already know the problem, don't ask what they're working on
- **IMPORTANT: If code is provided above, ALWAYS reference and analyze it specifically**
- If code is empty or minimal, guide them on where to start
- Don't give away solutions, guide discovery
- Be specific about what you observe in their code or approach
</Guidelines>

Respond now:"""
        
        # Use Gemini to generate response
        from langchain_google_genai import ChatGoogleGenerativeAI
        from app.core.config import settings
        
        # Try to disable thinking mode via generation_config
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 1024,
            "thinking_budget": 0  # Disable adaptive thinking
        }
        
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            api_key=settings.GEMINI_API_KEY,
            generation_config=generation_config
        )
        
        # Print complete prompt before sending to LLM
        print(f"\n{'='*80}")
        print(f"📤 COMPLETE PROMPT BEING SENT TO GEMINI (Chat Assistant)")
        print(f"{'='*80}")
        print(prompt)
        print(f"{'='*80}")
        print(f"Total prompt length: {len(prompt)} characters")
        print(f"{'='*80}\n")
        
        response = await llm.ainvoke(prompt)
        
        # Print response
        print(f"\n{'='*80}")
        print(f"📥 RECEIVED FROM GEMINI (Chat Assistant)")
        print(f"{'='*80}")
        print(f"Response type: {type(response)}")
        print(f"Response content length: {len(response.content) if response.content else 0}")
        print(f"Response preview: {response.content[:200] if response.content else 'EMPTY'}...")
        print(f"{'='*80}\n")
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

