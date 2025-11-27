from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from .learner_state import LearnerState

class UserBase(BaseModel):
    email: EmailStr
    name: str
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDB(UserBase):
    key: str = Field(alias="_key", serialization_alias="key")
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    skill_level: Optional[str] = None
    onboarding_completed: bool = False
    
    # Expertise ranking system (100-3000, like chess rating)
    expertise_rank: int = Field(default=600, description="User's DSA expertise ranking")
    initial_rank: Optional[int] = None  # Rank assigned after onboarding assessment
    peak_rank: Optional[int] = None  # Highest rank achieved
    
    # Onboarding data
    onboarding_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    assessment_results: Optional[List[str]] = Field(default_factory=list)  # Assessment keys
    
    # Learning preferences and progress
    learning_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    skill_strengths: Optional[List[str]] = Field(default_factory=list)
    areas_for_improvement: Optional[List[str]] = Field(default_factory=list)
    
    # Course activation tracking (single course only)
    active_course: Optional[str] = Field(default=None, description="Currently active course ID for the user")
    
    # AI Tutoring System - Centralized learner state
    learner_state: Optional[LearnerState] = Field(
        default=None,
        description="Centralized state for AI tutoring agents (initialized on first activity)"
    )
    
    # ============================================================================
    # MULTI-AGENT SYSTEM FIELDS
    # ============================================================================
    
    memory: Optional[str] = Field(
        default=None,
        description="Long-term learning insights maintained by AI agents"
    )
    
    agent_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Agent-specific metadata"
    )
    
    recommendations: Optional[List[str]] = Field(
        default_factory=list,
        description="Daily recommended question keys"
    )
    
    recommendations_updated_at: Optional[datetime] = Field(
        default=None,
        description="When recommendations were last generated"
    )
    
    gamification: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="XP, badges, level, achievements"
    )

    # Usage Tracking
    llm_usage_count: int = Field(default=0, description="Number of LLM calls made by the user")
    interacted_questions: List[str] = Field(default_factory=list, description="List of question keys interacted with")
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key
    
class User(UserBase):
    key: str = Field(alias="_key", serialization_alias="key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    skill_level: Optional[str] = None
    onboarding_completed: bool = False
    
    # Expertise ranking system (100-3000, like chess rating)
    expertise_rank: int = Field(default=600, description="User's DSA expertise ranking")
    initial_rank: Optional[int] = None  # Rank assigned after onboarding assessment
    peak_rank: Optional[int] = None  # Highest rank achieved
    
    # Onboarding data (excluding sensitive information)
    learning_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    skill_strengths: Optional[List[str]] = Field(default_factory=list)
    areas_for_improvement: Optional[List[str]] = Field(default_factory=list)
    
    # Course activation tracking (single course only)
    active_course: Optional[str] = Field(default=None, description="Currently active course ID for the user")
    
    # AI Tutoring System - Centralized learner state
    learner_state: Optional[LearnerState] = Field(
        default=None,
        description="Centralized state for AI tutoring agents (initialized on first activity)"
    )
    
    # ============================================================================
    # MULTI-AGENT SYSTEM FIELDS
    # ============================================================================
    
    memory: Optional[str] = Field(
        default=None,
        description="Long-term learning insights maintained by AI agents"
    )
    
    agent_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Agent-specific metadata"
    )
    
    recommendations: Optional[List[str]] = Field(
        default_factory=list,
        description="Daily recommended question keys"
    )
    
    recommendations_updated_at: Optional[datetime] = Field(
        default=None,
        description="When recommendations were last generated"
    )
    
    gamification: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="XP, badges, level, achievements"
    )

    # Usage Tracking
    llm_usage_count: int = Field(default=0, description="Number of LLM calls made by the user")
    interacted_questions: List[str] = Field(default_factory=list, description="List of question keys interacted with")
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key
