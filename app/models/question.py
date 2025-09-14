from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class DifficultyLevel(str, Enum):
    """Question difficulty levels."""
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE" 
    ADVANCED = "ADVANCED"

class QuestionType(str, Enum):
    """Types of assessment questions."""
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    CODING = "CODING"
    TRUE_FALSE = "TRUE_FALSE"

class SkillCategory(str, Enum):
    """Skill categories for DSA topics."""
    ARRAYS = "ARRAYS"
    STRINGS = "STRINGS"
    LINKED_LISTS = "LINKED_LISTS"
    STACKS_QUEUES = "STACKS_QUEUES"
    TREES = "TREES"
    GRAPHS = "GRAPHS"
    DYNAMIC_PROGRAMMING = "DYNAMIC_PROGRAMMING"
    SORTING_SEARCHING = "SORTING_SEARCHING"
    RECURSION = "RECURSION"
    HASH_TABLES = "HASH_TABLES"
    BASIC_PROGRAMMING = "BASIC_PROGRAMMING"

class QuestionExample(BaseModel):
    """Question example with input/output."""
    input: str
    output: str
    explanation: Optional[str] = None

class MultipleChoiceOption(BaseModel):
    """Multiple choice question option."""
    key: str  # A, B, C, D
    text: str
    is_correct: bool = False

class QuestionBase(BaseModel):
    """Base question model."""
    title: str
    description: str
    difficulty: DifficultyLevel
    question_type: QuestionType
    skill_categories: List[SkillCategory]
    estimated_time_minutes: int = 5
    points: int = Field(default=10, description="Points awarded for correct answer")
    
class QuestionCreate(QuestionBase):
    """Question creation model."""
    # Multiple choice specific
    options: Optional[List[MultipleChoiceOption]] = None
    correct_answer_key: Optional[str] = None
    
    # Coding question specific
    examples: Optional[List[QuestionExample]] = None
    constraints: Optional[List[str]] = None
    function_signature: Optional[Dict[str, str]] = None  # Language -> signature
    template_code: Optional[Dict[str, str]] = None  # Language -> template
    test_cases: Optional[List[Dict[str, Any]]] = None
    
    # True/False specific
    correct_answer: Optional[bool] = None
    explanation: Optional[str] = None

class QuestionInDB(QuestionBase):
    """Question model for database storage."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # User key who created the question
    
    # Question content (flexible storage)
    content: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class Question(QuestionBase):
    """Question model for API responses."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Question content based on type
    content: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        """Provide backward compatibility for _key access."""
        return self.key

class QuestionUpdate(BaseModel):
    """Question update model."""
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    skill_categories: Optional[List[SkillCategory]] = None
    estimated_time_minutes: Optional[int] = None
    points: Optional[int] = None
    content: Optional[Dict[str, Any]] = None
