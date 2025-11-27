from fastapi import HTTPException, status
from app.models.user import User
from app.crud.user import UserCRUD

# Constants
AI_CALL_LIMIT = 20
QUESTION_LIMIT = 3

def check_and_increment_llm_usage(user: User, user_crud: UserCRUD) -> None:
    """
    Check if user has reached the LLM usage limit and increment if not.
    
    Args:
        user: The current user object
        user_crud: UserCRUD instance for database updates
        
    Raises:
        HTTPException: If limit is reached (403 Forbidden)
    """
    if user.llm_usage_count >= AI_CALL_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Demo limit reached: You can only use {AI_CALL_LIMIT} AI Assistant calls in this demo version."
        )
    
    # Increment usage
    user_crud.increment_llm_usage(user.key)

def check_question_interaction_limit(user: User, question_id: str) -> None:
    """
    Check if user has reached the question interaction limit for a NEW question.
    Does NOT increment/add the question (that happens on submission).
    
    Args:
        user: The current user object
        question_id: The ID of the question being accessed
        
    Raises:
        HTTPException: If limit is reached (403 Forbidden)
    """
    # If question already interacted with, no limit check needed
    if question_id in user.interacted_questions:
        return

    # If new question, check if limit reached
    if len(user.interacted_questions) >= QUESTION_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Demo limit reached: You can only interact with {QUESTION_LIMIT} questions in this demo version."
        )

def register_question_interaction(user: User, user_crud: UserCRUD, question_id: str) -> None:
    """
    Register a question interaction (on submission).
    Also checks limit one last time to be safe.
    
    Args:
        user: The current user object
        user_crud: UserCRUD instance
        question_id: The ID of the question being submitted
    """
    # Check limit first
    check_question_interaction_limit(user, question_id)
    
    # Add to interacted questions if not present
    if question_id not in user.interacted_questions:
        user_crud.add_interacted_question(user.key, question_id)

