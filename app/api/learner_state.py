"""
Learner State API Endpoints.

Provides access to the centralized learner state for the
Intelligent Tutoring System.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.db.database import get_db
from app.models.user import User
from app.models.learner_state import LearnerState, TopicStatistics, create_default_learner_state
from app.crud.learner_state import LearnerStateCRUD
from app.crud.user import UserCRUD
from app.api.auth import get_current_user

router = APIRouter(prefix="/learner-state", tags=["learner-state"])


def get_learner_state_crud():
    """Dependency to get learner state CRUD instance."""
    db = get_db()
    return LearnerStateCRUD(db)


def get_user_crud():
    """Dependency to get user CRUD instance."""
    db = get_db()
    return UserCRUD(db)


@router.get("", response_model=LearnerState)
async def get_learner_state(
    current_user: User = Depends(get_current_user),
    learner_crud: LearnerStateCRUD = Depends(get_learner_state_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """
    Get current learner state for the authenticated user.
    
    If learner state doesn't exist, it will be initialized from
    submission history.
    """
    # Check if user has learner state
    if current_user.learner_state is None:
        # Initialize from history
        print(f"📊 Initializing learner state for user {current_user.key}")
        learner_state = learner_crud.initialize_from_history(current_user.key)
        
        # Save to user document (use mode='json' to serialize datetime objects)
        user_crud.update_user_fields(current_user.key, {
            'learner_state': learner_state.model_dump(mode='json')
        })
        
        return learner_state
    
    return current_user.learner_state


@router.post("/recalculate", response_model=LearnerState)
async def recalculate_learner_state(
    current_user: User = Depends(get_current_user),
    learner_crud: LearnerStateCRUD = Depends(get_learner_state_crud),
    user_crud: UserCRUD = Depends(get_user_crud)
):
    """
    Recalculate learner state from scratch based on submission history.
    
    Useful for:
    - Fixing corrupted state
    - Testing new calculation algorithms
    - Manual state refresh
    """
    print(f"🔄 Recalculating learner state for user {current_user.key}")
    
    learner_state = learner_crud.initialize_from_history(current_user.key)
    
    # Save to user document (use mode='json' to serialize datetime objects)
    user_crud.update_user_fields(current_user.key, {
        'learner_state': learner_state.model_dump(mode='json')
    })
    
    return learner_state


@router.get("/topics/{topic}", response_model=TopicStatistics)
async def get_topic_statistics(
    topic: str,
    current_user: User = Depends(get_current_user),
    learner_crud: LearnerStateCRUD = Depends(get_learner_state_crud)
):
    """
    Get detailed statistics for a specific topic.
    
    Returns:
    - Mastery level
    - Total attempts
    - Problems solved
    - Success rate
    - Common errors
    - Whether topic needs review
    """
    return learner_crud.get_topic_statistics(current_user.key, topic)


@router.get("/reviews/due", response_model=List[dict])
async def get_due_reviews(
    current_user: User = Depends(get_current_user),
    learner_crud: LearnerStateCRUD = Depends(get_learner_state_crud)
):
    """
    Get questions that are due for spaced repetition review.
    
    Returns list of ReviewItems sorted by due date.
    """
    if current_user.learner_state is None:
        return []
    
    due_reviews = learner_crud.get_due_reviews(current_user.learner_state)
    
    return [
        {
            "question_id": r.question_id,
            "topics": r.topics,
            "due_date": r.due_date.isoformat(),
            "days_overdue": (r.due_date.date() - r.due_date.date()).days
        }
        for r in due_reviews
    ]


@router.get("/summary")
async def get_learner_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Get a summary of the learner's current state.
    
    Returns:
    - Topics practiced
    - Average mastery
    - Current streak
    - Reviews due count
    """
    if current_user.learner_state is None:
        return {
            "topics_practiced": 0,
            "average_mastery": 0.0,
            "current_streak": 0,
            "reviews_due": 0,
            "strongest_topics": [],
            "needs_improvement": []
        }
    
    state = current_user.learner_state
    
    # Calculate summary metrics
    mastery_values = list(state.mastery.values())
    avg_mastery = sum(mastery_values) / len(mastery_values) if mastery_values else 0.0
    
    # Get top 3 strongest and weakest topics
    sorted_topics = sorted(state.mastery.items(), key=lambda x: x[1], reverse=True)
    strongest = [{"topic": t, "mastery": m} for t, m in sorted_topics[:3]]
    weakest = [{"topic": t, "mastery": m} for t, m in sorted_topics[-3:] if m < 0.7]
    
    # Count due reviews
    from datetime import datetime
    now = datetime.utcnow()
    reviews_due = len([r for r in state.reviews if r.due_date <= now])
    
    return {
        "topics_practiced": len(state.mastery),
        "average_mastery": round(avg_mastery, 2),
        "current_streak": state.streak,
        "reviews_due": reviews_due,
        "strongest_topics": strongest,
        "needs_improvement": weakest
    }

