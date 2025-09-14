from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import Enum

class ActivityType(str, Enum):
    """Types of user activities."""
    PROBLEM_SOLVED = "PROBLEM_SOLVED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    DAILY_CHALLENGE = "DAILY_CHALLENGE"
    STREAK_MAINTAINED = "STREAK_MAINTAINED"

class DifficultyLevel(str, Enum):
    """Problem difficulty levels."""
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

class ProblemSolvingSessionBase(BaseModel):
    """Base model for problem solving sessions."""
    user_key: str
    question_key: str
    difficulty: DifficultyLevel
    is_correct: bool
    time_taken_seconds: int
    points_earned: int = 0
    session_date: date

class ProblemSolvingSessionCreate(ProblemSolvingSessionBase):
    """Problem solving session creation model."""
    pass

class ProblemSolvingSessionInDB(ProblemSolvingSessionBase):
    """Problem solving session database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Additional metadata
    hints_used: int = 0
    attempts_count: int = 1
    programming_language: Optional[str] = None
    solution_quality_score: Optional[float] = None  # 0-100, based on code efficiency, style, etc.
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class ProblemSolvingSession(ProblemSolvingSessionBase):
    """Problem solving session API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    hints_used: int = 0
    attempts_count: int = 1
    programming_language: Optional[str] = None
    solution_quality_score: Optional[float] = None
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class UserActivityBase(BaseModel):
    """Base model for user daily activity tracking."""
    user_key: str
    activity_date: date
    problems_solved: int = 0
    points_earned: int = 0
    time_spent_minutes: int = 0
    streak_count: int = 0

class UserActivityCreate(UserActivityBase):
    """User activity creation model."""
    pass

class UserActivityInDB(UserActivityBase):
    """User activity database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Activity breakdown
    activity_types: List[ActivityType] = Field(default_factory=list)
    difficulty_breakdown: Dict[str, int] = Field(default_factory=dict)  # {"BEGINNER": 2, "INTERMEDIATE": 1}
    
    # Session metadata
    total_sessions: int = 0
    average_session_duration: float = 0.0  # minutes
    best_session_score: int = 0
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class UserActivity(UserActivityBase):
    """User activity API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    activity_types: List[ActivityType] = Field(default_factory=list)
    difficulty_breakdown: Dict[str, int] = Field(default_factory=dict)
    total_sessions: int = 0
    average_session_duration: float = 0.0
    best_session_score: int = 0
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class UserStreakInfo(BaseModel):
    """User streak information."""
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[date] = None
    total_active_days: int
    streak_freeze_count: int = 0  # Number of streak freezes available

class UserStatsBase(BaseModel):
    """Base model for aggregated user statistics."""
    user_key: str
    total_problems_solved: int = 0
    total_points_earned: int = 0
    total_time_spent_minutes: int = 0
    acceptance_rate: float = 0.0  # Percentage of problems solved correctly
    
    # Ranking information
    global_rank: Optional[int] = None
    country_rank: Optional[int] = None
    ranking_last_updated: Optional[datetime] = None

class UserStatsInDB(UserStatsBase):
    """User statistics database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Detailed breakdowns
    difficulty_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    # {"BEGINNER": {"solved": 10, "attempted": 12}, "INTERMEDIATE": {...}}
    
    monthly_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    # {"2024-01": {"problems": 15, "points": 150}, "2024-02": {...}}
    
    skill_category_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    # {"arrays": {"problems_solved": 5, "accuracy": 80.0}, "trees": {...}}
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class UserStats(UserStatsBase):
    """User statistics API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    difficulty_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    monthly_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    skill_category_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class ContributionDay(BaseModel):
    """Single day contribution data for heatmap."""
    date: str  # YYYY-MM-DD format
    count: int  # Number of problems solved
    level: int  # Intensity level 0-4
    points: int = 0
    sessions: int = 0

class ContributionHeatmapData(BaseModel):
    """Contribution heatmap data for frontend."""
    days: List[ContributionDay]
    total_contributions: int
    active_days: int
    current_streak: int
    longest_streak: int
    best_day: int
    daily_average: float

class DashboardStats(BaseModel):
    """Complete dashboard statistics."""
    # Profile header data
    expertise_rank: int
    rank_title: str  # "Expert", "Master", etc.
    peak_rank: int
    global_rank: Optional[int]
    country_rank: Optional[int]
    problems_solved: int
    acceptance_rate: float
    
    # Streak information
    current_streak: int
    longest_streak: int
    
    # Activity summary
    total_active_days: int
    total_points: int
    monthly_average: float
    
    # Recent performance
    recent_activity: List[ContributionDay]  # Last 7 days
    skill_strengths: List[str]
    areas_for_improvement: List[str]
