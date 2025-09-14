from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# Request schemas for behavior tracking API

class KeystrokeEventRequest(BaseModel):
    """Request model for submitting keystroke events."""
    session_id: str
    question_key: Optional[str] = None
    timestamp: datetime
    key_pressed: str
    key_code: int
    is_printable: bool
    cursor_position: Optional[Dict[str, int]] = None
    text_length: int = 0

class BehaviorEventRequest(BaseModel):
    """Request model for submitting general behavior events."""
    session_id: str
    question_key: Optional[str] = None
    event_type: str  # Will be validated against BehaviorEventType enum
    timestamp: datetime
    duration: Optional[float] = None
    metadata: Dict[str, Any] = {}

class StartSessionRequest(BaseModel):
    """Request model for starting a new behavior tracking session."""
    question_key: Optional[str] = None
    session_config: Optional[Dict[str, Any]] = None

class EndSessionRequest(BaseModel):
    """Request model for ending a behavior tracking session."""
    end_timestamp: datetime

class BatchKeystrokeRequest(BaseModel):
    """Request model for submitting multiple keystroke events in batch."""
    session_id: str
    events: List[KeystrokeEventRequest]

# Response schemas

class StartSessionResponse(BaseModel):
    """Response model for session start."""
    session_id: str
    start_time: datetime
    tracking_enabled: bool
    privacy_mode: bool = False

class LiveMetricsResponse(BaseModel):
    """Response model for live behavior metrics."""
    session_id: str
    typing_speed_cpm: float
    typing_speed_wpm: float
    recent_pauses: int
    productivity_level: str  # "high", "medium", "low"
    flow_state: bool
    suggestion: Optional[str] = None

class SessionAnalyticsResponse(BaseModel):
    """Response model for session analytics."""
    session_id: str
    duration_minutes: float
    total_keystrokes: int
    productive_keystrokes: int
    
    # Speed metrics
    average_typing_speed_cpm: float
    average_typing_speed_wpm: float
    peak_typing_speed_cpm: float
    
    # Pause analysis
    total_pauses: int
    average_pause_duration: float
    longest_pause_duration: float
    
    # Burst analysis
    total_bursts: int
    average_burst_length: float
    longest_burst_length: int
    
    # Quality metrics
    correction_ratio: float
    productivity_score: float
    rhythm_consistency: Optional[float] = None

class BehaviorInsightsResponse(BaseModel):
    """Response model for behavior insights."""
    user_key: str
    analysis_period: str  # e.g., "last_week", "last_month"
    
    # Overall metrics
    average_typing_speed_cpm: float
    typing_consistency_score: float
    productivity_score: float
    
    # Trends
    improvement_trend: str  # "improving", "stable", "declining"
    confidence_level: float
    
    # Patterns
    peak_performance_hours: List[int]  # Hours of day when user performs best
    common_struggle_areas: List[str]
    strengths: List[str]
    
    # Recommendations
    personalized_tips: List[str]
    next_focus_areas: List[str]

class UserBehaviorProfile(BaseModel):
    """Response model for user's behavior profile."""
    user_key: str
    profile_created: datetime
    last_updated: datetime
    
    # Typing characteristics
    typical_typing_speed_range: Dict[str, float]  # {"min": 40, "max": 80}
    preferred_coding_pace: str  # "fast", "moderate", "deliberate"
    error_correction_style: str  # "immediate", "batch", "minimal"
    
    # Learning patterns
    learning_style: str  # "methodical", "exploratory", "trial_error"
    concentration_patterns: List[str]  # ["morning_focused", "needs_breaks"]
    problem_solving_approach: str
    
    # Recommendations
    optimal_session_length: int  # minutes
    recommended_break_frequency: int  # minutes
    personalized_difficulty_progression: str

class BehaviorComparisonResponse(BaseModel):
    """Response model for comparing user behavior to benchmarks."""
    user_key: str
    comparison_period: str
    
    # Speed comparison
    typing_speed_percentile: float  # 0-100
    speed_vs_skill_level: str  # "above_average", "average", "below_average"
    
    # Productivity comparison
    productivity_percentile: float
    error_rate_percentile: float
    
    # Skill level indicators
    estimated_skill_level: str  # "beginner", "intermediate", "advanced"
    skill_confidence: float  # 0-100
    
    # Growth metrics
    improvement_rate: float  # percentage per week/month
    consistency_score: float  # 0-100
    
    # Peer comparison (anonymized)
    similar_users_average_speed: float
    similar_users_average_productivity: float

class PrivacyControlsRequest(BaseModel):
    """Request model for updating privacy controls."""
    enable_tracking: bool = True
    anonymize_data: bool = True
    share_insights_for_research: bool = False
    data_retention_period_days: int = 90

class PrivacyControlsResponse(BaseModel):
    """Response model for privacy controls."""
    user_key: str
    tracking_enabled: bool
    anonymization_enabled: bool
    research_participation: bool
    data_retention_days: int
    data_deletion_scheduled: Optional[datetime] = None

# Analytics and dashboard schemas

class BehaviorDashboardData(BaseModel):
    """Complete behavior dashboard data."""
    user_key: str
    date_range: str
    
    # Summary cards
    total_coding_time: float  # hours
    average_daily_typing_speed: float
    productivity_trend: str  # "up", "down", "stable"
    focus_score: float  # 0-100
    
    # Charts data
    daily_typing_speeds: List[Dict[str, Any]]  # For speed trend chart
    hourly_productivity: List[Dict[str, Any]]  # For productivity heatmap
    session_durations: List[Dict[str, Any]]  # For session length analysis
    
    # Recent insights
    recent_achievements: List[str]
    areas_of_improvement: List[str]
    weekly_goals_progress: Dict[str, float]  # {"typing_speed": 0.8, "consistency": 0.6}
    
    # AI-generated insights
    ai_insights: List[str]
    personalized_recommendations: List[str]

class ExportDataRequest(BaseModel):
    """Request model for exporting behavior data."""
    start_date: datetime
    end_date: datetime
    data_types: List[str]  # ["keystrokes", "sessions", "insights"]
    format: str = "json"  # "json", "csv"
    include_raw_data: bool = False

class ExportDataResponse(BaseModel):
    """Response model for data export."""
    export_id: str
    status: str  # "processing", "ready", "failed"
    download_url: Optional[str] = None
    file_size_mb: Optional[float] = None
    expires_at: Optional[datetime] = None
