"""
Learner State Models for Intelligent Tutoring System.

This module defines the centralized learner state that tracks:
- Knowledge mastery per topic
- Error patterns for targeted feedback
- Spaced repetition review schedule
- Engagement metrics

The learner state is stored in the user document and serves as the
single source of truth for all AI tutoring agents.
"""

from typing import Dict, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field


# ============================================================================
# KNOWLEDGE MASTERY MODELS
# ============================================================================

class TopicMastery(BaseModel):
    """
    Tracks mastery for a single DSA topic.
    
    Mastery level is calculated from submission history:
    - Increases on successful submissions
    - Decreases on failures
    - Weighted by recency
    """
    level: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Mastery level from 0.0 (novice) to 1.0 (expert)"
    )
    attempts: int = Field(
        default=0,
        ge=0,
        description="Total submission attempts for this topic"
    )
    solved: int = Field(
        default=0,
        ge=0,
        description="Number of successfully solved problems"
    )
    last_practiced: Optional[datetime] = Field(
        default=None,
        description="Most recent practice timestamp"
    )


# ============================================================================
# ERROR PATTERN TRACKING
# ============================================================================

class ErrorPattern(BaseModel):
    """
    Records a recurring error pattern for targeted feedback.
    
    Helps the Pedagogical Feedback Agent identify misconceptions
    and provide specific hints.
    """
    pattern: str = Field(
        description="Error pattern identifier (e.g., 'off-by-one', 'null-check')"
    )
    count: int = Field(
        default=1,
        ge=1,
        description="Number of times this error occurred"
    )
    last_seen: datetime = Field(
        description="Most recent occurrence"
    )
    example_question_ids: List[str] = Field(
        default_factory=list,
        description="Question IDs where this error occurred (max 3 for context)"
    )


# ============================================================================
# SPACED REPETITION SCHEDULE
# ============================================================================

class ReviewItem(BaseModel):
    """
    A question scheduled for spaced repetition review.
    
    Uses simplified SM-2 algorithm:
    - interval_days: Days until next review
    - ease_factor: How "easy" the user finds this (1.3-2.5)
    """
    question_id: str = Field(description="Question to review")
    topics: List[str] = Field(description="All topics covered by this question")
    due_date: datetime = Field(description="When review is due")
    interval_days: int = Field(
        default=1,
        ge=1,
        description="Days between reviews (SM-2 interval)"
    )
    ease_factor: float = Field(
        default=2.5,
        ge=1.3,
        le=2.5,
        description="SM-2 ease factor"
    )


# ============================================================================
# MAIN LEARNER STATE MODEL
# ============================================================================

class LearnerState(BaseModel):
    """
    Centralized learner state for the Intelligent Tutoring System.
    
    This is the single source of truth for all AI agents:
    - Learner Profiler: Updates mastery levels
    - Skill Assessor: Analyzes submissions
    - Pedagogical Feedback: Uses error patterns
    - Content Curator: Uses mastery + reviews for suggestions
    - Progress Synthesizer: Manages review schedule
    - Engagement Orchestrator: Tracks activity
    
    Stored in user document. Updated by orchestrator after agent execution.
    """
    
    # Versioning for future schema migrations
    version: str = Field(
        default="1.0",
        description="Schema version for migration handling"
    )
    updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last state update timestamp"
    )
    
    # Topic mastery tracking (core metric)
    mastery: Dict[str, float] = Field(
        default_factory=dict,
        description="Map of topic -> mastery level (0.0-1.0)"
    )
    
    # Error pattern tracking
    common_errors: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Map of topic -> list of error patterns"
    )
    
    # Spaced repetition schedule
    reviews: List[ReviewItem] = Field(
        default_factory=list,
        description="Questions scheduled for review"
    )
    
    # Engagement tracking
    streak: int = Field(
        default=0,
        ge=0,
        description="Current daily activity streak"
    )
    last_seen: date = Field(
        default_factory=date.today,
        description="Last activity date"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


# ============================================================================
# HELPER MODELS
# ============================================================================

class LearnerStateUpdate(BaseModel):
    """
    Partial update to learner state.
    Used by agents to return state changes.
    """
    mastery: Optional[Dict[str, float]] = None
    common_errors: Optional[Dict[str, List[str]]] = None
    reviews: Optional[List[ReviewItem]] = None
    streak: Optional[int] = None
    last_seen: Optional[date] = None


class TopicStatistics(BaseModel):
    """
    Statistics for a single topic (derived from learner state).
    """
    topic: str
    mastery_level: float
    total_attempts: int
    problems_solved: int
    success_rate: float
    last_practiced: Optional[datetime]
    needs_review: bool
    common_errors: List[str]


def create_default_learner_state() -> LearnerState:
    """
    Create a default learner state for new users.
    
    Returns:
        LearnerState with empty/default values
    """
    return LearnerState(
        version="1.0",
        updated=datetime.utcnow(),
        mastery={},
        common_errors={},
        reviews=[],
        streak=0,
        last_seen=date.today()
    )


