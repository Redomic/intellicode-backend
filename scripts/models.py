"""
Data models for scraped question information.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

class DifficultyLevel(str, Enum):
    """Difficulty levels for coding problems."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNKNOWN = "unknown"

class Platform(str, Enum):
    """Supported platforms."""
    LEETCODE = "leetcode"
    GEEKSFORGEEKS = "geeksforgeeks"
    CODINGNINJAS = "codingninjas"
    TAKEUFORWARD = "takeuforward"

class TestCase(BaseModel):
    """Model for a test case."""
    input: str = ""
    output: str = ""
    explanation: Optional[str] = None

class QuestionLinks(BaseModel):
    """Links associated with a question."""
    post_link: Optional[str] = None
    yt_link: Optional[str] = None
    plus_link: Optional[str] = None
    editorial_link: Optional[str] = None
    gfg_link: Optional[str] = None
    cs_link: Optional[str] = None
    lc_link: Optional[str] = None

class ScrapedQuestion(BaseModel):
    """Model for a scraped coding question."""
    
    # Original A2Z data
    id: str
    step_no: int
    sub_step_no: int
    sl_no: int
    step_title: str
    sub_step_title: str
    question_title: str
    difficulty: int
    ques_topic: str
    company_tags: Optional[str] = None
    links: QuestionLinks
    
    # Scraped content
    scraped_content: Dict[str, Any] = Field(default_factory=dict)
    scraping_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('links', pre=True)
    def validate_links(cls, v):
        if isinstance(v, dict):
            return QuestionLinks(**v)
        return v

class ScrapedQuestionContent(BaseModel):
    """Detailed content scraped from a platform."""
    
    # Basic info
    platform: Platform
    url: str
    title: str = ""
    problem_statement: str = ""
    
    # Difficulty and categorization
    difficulty: DifficultyLevel = DifficultyLevel.UNKNOWN
    tags: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    
    # Problem details
    constraints: List[str] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    examples: List[Dict[str, str]] = Field(default_factory=list)
    
    # Code templates
    code_templates: Dict[str, str] = Field(default_factory=dict)  # language -> template
    
    # Additional metadata
    hints: List[str] = Field(default_factory=list)
    editorial_url: Optional[str] = None
    discussion_count: Optional[int] = None
    likes: Optional[int] = None
    dislikes: Optional[int] = None
    
    # Scraping metadata
    scraped_at: datetime = Field(default_factory=datetime.now)
    scraping_duration: Optional[float] = None
    scraping_success: bool = True
    error_message: Optional[str] = None

class ScrapingResult(BaseModel):
    """Result of a scraping operation."""
    
    question_id: str
    success: bool
    platforms_scraped: List[Platform] = Field(default_factory=list)
    content: Dict[Platform, ScrapedQuestionContent] = Field(default_factory=dict)
    errors: Dict[Platform, str] = Field(default_factory=dict)
    
    total_duration: Optional[float] = None
    scraped_at: datetime = Field(default_factory=datetime.now)

class ScrapingStats(BaseModel):
    """Statistics for the scraping session."""
    
    total_questions: int = 0
    successful_scrapes: int = 0
    failed_scrapes: int = 0
    platform_stats: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration: Optional[float] = None
    
    def add_result(self, result: ScrapingResult):
        """Add a scraping result to the statistics."""
        self.total_questions += 1
        
        if result.success:
            self.successful_scrapes += 1
        else:
            self.failed_scrapes += 1
        
        # Update platform stats
        for platform in result.platforms_scraped:
            platform_name = platform.value
            if platform_name not in self.platform_stats:
                self.platform_stats[platform_name] = {"success": 0, "failed": 0}
            
            if platform in result.content:
                self.platform_stats[platform_name]["success"] += 1
            else:
                self.platform_stats[platform_name]["failed"] += 1
    
    def finalize(self):
        """Finalize the statistics."""
        self.end_time = datetime.now()
        if self.start_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()
