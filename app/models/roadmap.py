from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class RoadmapItemBase(BaseModel):
    """Base roadmap item model for comprehensive LeetCode questions."""
    
    # Course identifier
    course: str = Field(..., description="Course identifier (e.g., 'strivers-a2z')")
    
    # A2Z Striver metadata
    question_id: str = Field(..., description="Unique identifier from a2z dataset")
    original_title: str = Field(..., description="Original title from a2z dataset")
    a2z_step: str = Field(..., description="Main step in a2z roadmap")
    a2z_sub_step: str = Field(..., description="Sub-step in a2z roadmap")
    a2z_difficulty: int = Field(..., description="Difficulty level in a2z (0-5)")
    a2z_topics: str = Field(..., description="Topics as JSON string from a2z")
    lc_link: str = Field(..., description="LeetCode problem URL")
    step_number: int = Field(..., description="Sequential step number from a2z sl_no for proper ordering")
    
    # LeetCode comprehensive data
    leetcode_title: Optional[str] = None
    leetcode_title_slug: Optional[str] = None
    leetcode_difficulty: Optional[str] = None  # Easy, Medium, Hard
    leetcode_question_id: Optional[int] = None
    is_paid_only: Optional[bool] = False
    
    # Problem content
    problem_statement_html: Optional[str] = None
    problem_statement_text: Optional[str] = None
    
    # Examples and test cases
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    sample_test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    
    # Code templates and solutions
    code_templates: Dict[str, str] = Field(default_factory=dict)
    default_code: Optional[str] = None
    
    # Educational content
    hints: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    company_tags: List[str] = Field(default_factory=list)
    similar_questions: List[int] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    note_sections: List[str] = Field(default_factory=list)
    
    # Scraping metadata
    scraping_duration: Optional[float] = None
    scraped_at: Optional[datetime] = None
    scraping_success: bool = False
    scraping_error: Optional[str] = None


class RoadmapItemCreate(RoadmapItemBase):
    """Create roadmap item model."""
    pass


class RoadmapItemUpdate(BaseModel):
    """Update roadmap item model."""
    
    # Allow partial updates of any field
    original_title: Optional[str] = None
    a2z_step: Optional[str] = None
    a2z_sub_step: Optional[str] = None
    a2z_difficulty: Optional[int] = None
    a2z_topics: Optional[str] = None
    lc_link: Optional[str] = None
    step_number: Optional[int] = None
    
    leetcode_title: Optional[str] = None
    leetcode_title_slug: Optional[str] = None
    leetcode_difficulty: Optional[str] = None
    leetcode_question_id: Optional[int] = None
    is_paid_only: Optional[bool] = None
    
    problem_statement_html: Optional[str] = None
    problem_statement_text: Optional[str] = None
    
    examples: Optional[List[Dict[str, Any]]] = None
    sample_test_cases: Optional[List[Dict[str, Any]]] = None
    constraints: Optional[List[str]] = None
    
    code_templates: Optional[Dict[str, str]] = None
    default_code: Optional[str] = None
    
    hints: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    company_tags: Optional[List[str]] = None
    similar_questions: Optional[List[int]] = None
    follow_up_questions: Optional[List[str]] = None
    note_sections: Optional[List[str]] = None
    
    scraping_duration: Optional[float] = None
    scraped_at: Optional[datetime] = None
    scraping_success: Optional[bool] = None
    scraping_error: Optional[str] = None


class RoadmapItemInDB(RoadmapItemBase):
    """Roadmap item model for database storage."""
    key: str = Field(alias="_key")
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


class RoadmapItem(RoadmapItemBase):
    """Roadmap item model for API responses."""
    key: str = Field(alias="_key")
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


# Enums for filtering and categorization
class LeetCodeDifficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class A2ZDifficulty(int, Enum):
    LEVEL_0 = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5


# Statistics and summary models
class RoadmapStats(BaseModel):
    """Statistics about the roadmap collection."""
    total_questions: int
    successfully_scraped: int
    failed_scrapes: int
    success_rate: float
    
    # Difficulty distribution
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Content statistics
    total_examples: int
    total_test_cases: int
    total_hints: int
    total_topics: int
    
    # A2Z roadmap coverage
    steps_covered: List[str] = Field(default_factory=list)
    sub_steps_covered: List[str] = Field(default_factory=list)
    
    # Last update info
    last_scraped: Optional[datetime] = None
    average_scraping_duration: Optional[float] = None


class RoadmapSearchFilters(BaseModel):
    """Filters for searching roadmap items."""
    a2z_step: Optional[str] = None
    a2z_sub_step: Optional[str] = None
    a2z_difficulty: Optional[int] = None
    leetcode_difficulty: Optional[LeetCodeDifficulty] = None
    topics: Optional[List[str]] = None
    is_paid_only: Optional[bool] = None
    scraping_success: Optional[bool] = None
    has_examples: Optional[bool] = None
    has_hints: Optional[bool] = None
    company_tags: Optional[List[str]] = None
