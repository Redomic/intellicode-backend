from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class BehaviorEventType(str, Enum):
    """Types of behavior events that can be tracked."""
    KEYSTROKE = "KEYSTROKE"
    PAUSE = "PAUSE"
    BURST = "BURST"
    CODE_EXECUTION = "CODE_EXECUTION"
    TAB_SWITCH = "TAB_SWITCH"
    SCROLL = "SCROLL"
    COPY_PASTE = "COPY_PASTE"
    UNDO_REDO = "UNDO_REDO"

class KeystrokeEventBase(BaseModel):
    """Base model for individual keystroke events."""
    user_key: str
    session_id: str  # Links multiple events to a coding session
    question_key: Optional[str] = None  # Question being worked on
    timestamp: datetime
    key_pressed: str
    key_code: int
    is_printable: bool  # Whether the key adds visible content
    cursor_position: Optional[Dict[str, int]] = None  # {"line": 1, "column": 5}
    text_length: int = 0  # Total length of code at this point

class KeystrokeEventCreate(KeystrokeEventBase):
    """Keystroke event creation model."""
    pass

class KeystrokeEventInDB(KeystrokeEventBase):
    """Keystroke event database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    
    # Additional computed fields
    time_since_last_keystroke: Optional[float] = None  # milliseconds
    is_backspace: bool = False
    is_delete: bool = False
    is_navigation: bool = False  # arrow keys, home, end, etc.
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class KeystrokeEvent(KeystrokeEventBase):
    """Keystroke event API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    time_since_last_keystroke: Optional[float] = None
    is_backspace: bool = False
    is_delete: bool = False
    is_navigation: bool = False
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class TypingSessionBase(BaseModel):
    """Base model for typing session analytics."""
    user_key: str
    session_id: str
    question_key: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Core metrics
    total_keystrokes: int = 0
    productive_keystrokes: int = 0  # Excludes backspace, delete, navigation
    typing_speed_cpm: float = 0.0  # Characters per minute
    typing_speed_wpm: float = 0.0  # Words per minute (assuming 5 chars = 1 word)
    
    # Pause analysis
    total_pauses: int = 0
    average_pause_duration: float = 0.0  # milliseconds
    longest_pause_duration: float = 0.0  # milliseconds
    pause_threshold: float = 500.0  # milliseconds to be considered a pause
    
    # Burst analysis
    total_bursts: int = 0
    average_burst_length: float = 0.0  # keystrokes per burst
    longest_burst_length: int = 0
    burst_threshold: float = 150.0  # milliseconds between keys for a burst
    
    # Code quality metrics
    backspace_count: int = 0
    delete_count: int = 0
    correction_ratio: float = 0.0  # (backspace + delete) / total_keystrokes

class TypingSessionCreate(TypingSessionBase):
    """Typing session creation model."""
    pass

class TypingSessionInDB(TypingSessionBase):
    """Typing session database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Advanced analytics
    rhythm_consistency: Optional[float] = None  # 0-100, how consistent the typing rhythm is
    hesitation_points: List[Dict[str, Any]] = Field(default_factory=list)  # Moments of long pauses
    productivity_score: Optional[float] = None  # 0-100, overall typing productivity
    
    # Temporal patterns
    pause_frequency: float = 0.0  # pauses per minute
    burst_frequency: float = 0.0  # bursts per minute
    typing_flow_score: Optional[float] = None  # 0-100, measure of smooth vs choppy typing
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class TypingSession(TypingSessionBase):
    """Typing session API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    rhythm_consistency: Optional[float] = None
    hesitation_points: List[Dict[str, Any]] = Field(default_factory=list)
    productivity_score: Optional[float] = None
    pause_frequency: float = 0.0
    burst_frequency: float = 0.0
    typing_flow_score: Optional[float] = None
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class BehaviorEventBase(BaseModel):
    """Base model for general behavior events."""
    user_key: str
    session_id: str
    question_key: Optional[str] = None
    event_type: BehaviorEventType
    timestamp: datetime
    duration: Optional[float] = None  # milliseconds
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BehaviorEventCreate(BehaviorEventBase):
    """Behavior event creation model."""
    pass

class BehaviorEventInDB(BehaviorEventBase):
    """Behavior event database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class BehaviorEvent(BehaviorEventBase):
    """Behavior event API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class BehaviorInsightsBase(BaseModel):
    """Base model for aggregated behavior insights."""
    user_key: str
    analysis_period_start: datetime
    analysis_period_end: datetime
    
    # Typing patterns
    average_typing_speed_cpm: float = 0.0
    average_typing_speed_wpm: float = 0.0
    typing_consistency_score: float = 0.0  # 0-100
    
    # Problem-solving patterns
    average_pause_before_coding: float = 0.0  # milliseconds
    average_thinking_time: float = 0.0  # time between problem view and first keystroke
    debugging_ratio: float = 0.0  # ratio of correction keystrokes to total
    
    # Productivity metrics
    focused_coding_time: float = 0.0  # minutes of actual typing
    total_session_time: float = 0.0  # total time including pauses
    productivity_score: float = 0.0  # 0-100
    
    # Learning indicators
    skill_improvement_trend: Optional[str] = None  # "improving", "stable", "declining"
    confidence_level: Optional[float] = None  # 0-100 based on typing patterns
    problem_solving_approach: Optional[str] = None  # "methodical", "exploratory", "reactive"

class BehaviorInsightsInDB(BehaviorInsightsBase):
    """Behavior insights database model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Detailed analytics
    session_count: int = 0
    total_keystrokes: int = 0
    problem_categories_analyzed: List[str] = Field(default_factory=list)
    
    # Advanced metrics for future development
    cognitive_load_indicators: Dict[str, float] = Field(default_factory=dict)
    learning_velocity: Optional[float] = None
    behavioral_patterns: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class BehaviorInsights(BehaviorInsightsBase):
    """Behavior insights API model."""
    key: str = Field(alias="_key")
    created_at: datetime
    updated_at: Optional[datetime] = None
    session_count: int = 0
    total_keystrokes: int = 0
    problem_categories_analyzed: List[str] = Field(default_factory=list)
    cognitive_load_indicators: Dict[str, float] = Field(default_factory=dict)
    learning_velocity: Optional[float] = None
    behavioral_patterns: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }
    
    @property
    def _key(self) -> str:
        return self.key

class LiveBehaviorMetrics(BaseModel):
    """Real-time behavior metrics for live feedback."""
    session_id: str
    current_typing_speed_cpm: float
    current_typing_speed_wpm: float
    recent_pause_count: int  # pauses in last minute
    current_burst_length: int
    time_since_last_keystroke: float  # milliseconds
    is_in_flow_state: bool
    productivity_indicator: str  # "high", "medium", "low"
    suggestion: Optional[str] = None  # Real-time tip for user

class BehaviorSessionSummary(BaseModel):
    """Summary of a completed behavior tracking session."""
    session_id: str
    user_key: str
    question_key: Optional[str] = None
    duration_minutes: float
    
    # Performance summary
    total_keystrokes: int
    average_typing_speed: float
    peak_typing_speed: float
    productivity_score: float
    
    # Key insights
    main_challenges: List[str]  # "long_pauses", "many_corrections", etc.
    strengths: List[str]  # "consistent_speed", "few_errors", etc.
    improvement_suggestions: List[str]
    
    # Comparison to user's average
    speed_vs_average: float  # percentage difference
    productivity_vs_average: float  # percentage difference

