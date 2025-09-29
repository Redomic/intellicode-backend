from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SubmissionStatus(str, Enum):
    """Submission status enum."""
    ACCEPTED = "Accepted"
    WRONG_ANSWER = "Wrong Answer"
    TIME_LIMIT_EXCEEDED = "Time Limit Exceeded"
    MEMORY_LIMIT_EXCEEDED = "Memory Limit Exceeded"
    RUNTIME_ERROR = "Runtime Error"
    COMPILE_ERROR = "Compile Error"


class SubmissionBase(BaseModel):
    """Base model for code submissions (LeetCode-style)."""
    user_key: str
    question_key: str
    question_title: Optional[str] = None
    
    # Code details
    code: str
    language: str = "python"
    
    # Submission results
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    
    # Test case results
    total_test_cases: int = 0
    passed_test_cases: int = 0
    failed_test_case_index: Optional[int] = None
    error_message: Optional[str] = None
    
    # Performance metrics
    runtime_percentile: Optional[float] = None
    memory_percentile: Optional[float] = None
    
    # Session context
    session_id: Optional[str] = None
    time_taken_seconds: int = 0  # Time spent solving
    attempts_count: int = 1  # Number of attempts for this question
    hints_used: int = 0
    
    # Roadmap context
    roadmap_id: Optional[str] = None
    difficulty: Optional[str] = None
    
    # Points and scoring
    points_earned: int = 0
    solution_quality_score: Optional[float] = None  # 0-100 based on code quality


class SubmissionCreate(BaseModel):
    """Model for creating a submission."""
    question_key: str
    question_title: Optional[str] = None
    code: str
    language: str = "python"
    status: SubmissionStatus
    runtime_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    total_test_cases: int = 0
    passed_test_cases: int = 0
    failed_test_case_index: Optional[int] = None
    error_message: Optional[str] = None
    runtime_percentile: Optional[float] = None
    memory_percentile: Optional[float] = None
    session_id: Optional[str] = None
    time_taken_seconds: int = 0
    attempts_count: int = 1
    hints_used: int = 0
    roadmap_id: Optional[str] = None
    difficulty: Optional[str] = None
    points_earned: int = 0
    solution_quality_score: Optional[float] = None


class SubmissionInDB(SubmissionBase):
    """Submission database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key
    
    @property
    def is_accepted(self) -> bool:
        """Check if submission was accepted."""
        return self.status == SubmissionStatus.ACCEPTED


class Submission(SubmissionBase):
    """Submission API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key
    
    @property
    def is_accepted(self) -> bool:
        """Check if submission was accepted."""
        return self.status == SubmissionStatus.ACCEPTED


class UserSubmissionStats(BaseModel):
    """User submission statistics."""
    total_submissions: int = 0
    accepted_submissions: int = 0
    acceptance_rate: float = 0.0
    total_problems_solved: int = 0  # Unique problems solved
    
    # Difficulty breakdown
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    
    # Performance metrics
    average_runtime_percentile: float = 0.0
    average_memory_percentile: float = 0.0
    
    # Activity metrics
    total_points: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    total_active_days: int = 0
    
    # Recent activity
    last_submission: Optional[datetime] = None


class ContributionDay(BaseModel):
    """Single day contribution data for heatmap."""
    date: str  # YYYY-MM-DD format
    count: int  # Number of submissions/problems solved
    level: int  # Intensity level 0-4
    points: int = 0


class ContributionHeatmapData(BaseModel):
    """Contribution heatmap data."""
    days: List[ContributionDay]
    total_contributions: int
    active_days: int
    current_streak: int
    longest_streak: int
    best_day: int
    daily_average: float
