from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from .question import SkillCategory, DifficultyLevel

class AssessmentStatus(str, Enum):
    """Assessment status options."""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"

class AssessmentType(str, Enum):
    """Types of assessments."""
    ONBOARDING = "ONBOARDING"
    SKILL_CHECK = "SKILL_CHECK"
    PRACTICE = "PRACTICE"

class UserAnswerBase(BaseModel):
    """Base model for user answers."""
    question_key: str
    time_taken_seconds: int
    is_correct: bool
    points_earned: int = 0

class UserAnswer(UserAnswerBase):
    """User answer with response data."""
    answer_data: Dict[str, Any] = Field(default_factory=dict)  # Flexible storage for different answer types
    submitted_at: datetime

class UserAnswerCreate(BaseModel):
    """User answer creation model."""
    question_key: str
    time_taken_seconds: int
    is_correct: bool = False  # Will be calculated by backend
    points_earned: int = 0    # Will be calculated by backend
    answer_data: Dict[str, Any] = Field(default_factory=dict)

class AssessmentBase(BaseModel):
    """Base assessment model."""
    user_key: str
    assessment_type: AssessmentType
    total_questions: int
    questions_answered: int = 0
    status: AssessmentStatus = AssessmentStatus.IN_PROGRESS

class AssessmentCreate(AssessmentBase):
    """Assessment creation model."""
    question_keys: List[str]  # Questions assigned to this assessment

class AssessmentInDB(AssessmentBase):
    """Assessment model for database storage."""
    key: str = Field(alias="_key")
    question_keys: List[str]
    user_answers: List[UserAnswer] = Field(default_factory=list)
    
    # Scoring and performance metrics
    total_points_possible: int = 0
    total_points_earned: int = 0
    accuracy_percentage: float = 0.0
    average_time_per_question: float = 0.0
    
    # Skill breakdown
    skill_performance: Dict[str, Dict[str, Union[int, float]]] = Field(default_factory=dict)
    
    # Ranking calculation
    calculated_expertise_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    rank_change: Optional[int] = None
    
    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class Assessment(AssessmentBase):
    """Assessment model for API responses."""
    key: str = Field(alias="_key")
    question_keys: List[str]
    user_answers: List[UserAnswer] = Field(default_factory=list)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    # Performance metrics
    total_points_possible: int = 0
    total_points_earned: int = 0
    accuracy_percentage: float = 0.0
    average_time_per_question: float = 0.0
    
    # Skill performance breakdown
    skill_performance: Dict[str, Dict[str, Union[int, float]]] = Field(default_factory=dict)
    
    # Ranking information
    calculated_expertise_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    rank_change: Optional[int] = None
    
    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class AssessmentUpdate(BaseModel):
    """Assessment update model."""
    status: Optional[AssessmentStatus] = None
    questions_answered: Optional[int] = None
    total_points_earned: Optional[int] = None
    accuracy_percentage: Optional[float] = None
    average_time_per_question: Optional[float] = None
    skill_performance: Optional[Dict[str, Dict[str, Union[int, float]]]] = None
    calculated_expertise_rank: Optional[int] = None
    completed_at: Optional[datetime] = None

class AssessmentResult(BaseModel):
    """Assessment result summary for frontend."""
    assessment_key: str
    user_key: str
    assessment_type: AssessmentType
    status: AssessmentStatus
    
    # Performance summary
    total_questions: int
    questions_answered: int
    accuracy_percentage: float
    total_points_earned: int
    total_points_possible: int
    average_time_per_question: float
    
    # Ranking information
    calculated_expertise_rank: int
    previous_rank: Optional[int] = None
    rank_change: Optional[int] = None
    
    # Skill breakdown for feedback
    skill_performance: Dict[str, Dict[str, Union[int, float]]]
    strongest_skills: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    
    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None

class RankingCalculationData(BaseModel):
    """Data structure for ranking calculations."""
    base_rank: int  # Based on claimed skill level
    accuracy_score: float  # 0-100
    time_efficiency_score: float  # 0-100, based on time taken vs expected
    difficulty_bonus: float  # Bonus for harder questions
    skill_consistency_score: float  # How consistent across different skills
    total_score: float
    final_rank: int
