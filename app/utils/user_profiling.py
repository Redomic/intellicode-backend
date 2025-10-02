"""
User Profiling Utilities for Adaptive Agent Behavior.

This module calculates user proficiency scores that agents use to adjust
their behavior (e.g., hint difficulty, feedback detail level).

The proficiency score ranges from 0.0 (beginner) to 1.0 (expert) and is
calculated from multiple weighted metrics.
"""

from typing import Dict, List, Optional
import logging
from app.models.user import User
from app.models.learner_state import LearnerState

logger = logging.getLogger(__name__)


# ============================================================================
# WEIGHTING CONFIGURATION
# ============================================================================

# Weights for proficiency calculation (must sum to 1.0)
WEIGHTS = {
    "topic_mastery": 0.40,      # 40% - Most important indicator
    "expertise_rank": 0.25,     # 25% - Overall skill level
    "skill_level": 0.20,        # 20% - Self-reported proficiency
    "submission_success": 0.10, # 10% - Recent performance
    "streak": 0.05             # 5% - Engagement/consistency
}

# Rank thresholds (chess-style rating system)
RANK_BEGINNER_MAX = 800
RANK_INTERMEDIATE_MAX = 1500
RANK_EXPERT_MIN = 2000

# Skill level mapping
SKILL_LEVEL_SCORES = {
    "beginner": 0.2,
    "intermediate": 0.5,
    "professional": 0.8,
    None: 0.3  # Default if not set
}


# ============================================================================
# PROFICIENCY CALCULATOR
# ============================================================================

class UserProfiler:
    """
    Calculates user proficiency scores for adaptive agent behavior.
    
    The proficiency score (0.0 - 1.0) determines:
    - Hint difficulty (higher score = more challenging hints)
    - Feedback detail (higher score = less hand-holding)
    - Problem recommendations (higher score = harder problems)
    """
    
    @staticmethod
    def calculate_proficiency(
        user: User,
        topics: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Calculate overall proficiency score and component breakdowns.
        
        Args:
            user: User object with learner_state
            topics: Optional list of topics to focus on (for topic-specific score)
            
        Returns:
            Dict containing:
            - overall_score: Weighted proficiency (0.0 - 1.0)
            - components: Individual component scores
            - recommendation: Textual interpretation
            
        Example:
            >>> profiler = UserProfiler()
            >>> result = profiler.calculate_proficiency(user, topics=["array"])
            >>> print(result["overall_score"])  # 0.67
            >>> print(result["recommendation"]) # "Intermediate-Advanced"
        """
        components = {}
        
        # 1. Topic Mastery Score (0.0 - 1.0)
        components["topic_mastery"] = UserProfiler._calculate_topic_mastery(
            user.learner_state, topics
        )
        
        # 2. Expertise Rank Score (0.0 - 1.0)
        components["expertise_rank"] = UserProfiler._normalize_rank(
            user.expertise_rank
        )
        
        # 3. Skill Level Score (0.0 - 1.0)
        components["skill_level"] = SKILL_LEVEL_SCORES.get(
            user.skill_level, 0.3
        )
        
        # 4. Submission Success Rate (0.0 - 1.0)
        components["submission_success"] = UserProfiler._estimate_success_rate(
            user.learner_state
        )
        
        # 5. Streak Score (0.0 - 1.0)
        components["streak"] = UserProfiler._normalize_streak(
            user.learner_state
        )
        
        # Calculate weighted overall score
        overall_score = sum(
            components[key] * WEIGHTS[key]
            for key in WEIGHTS.keys()
        )
        
        # Clamp to [0.0, 1.0]
        overall_score = max(0.0, min(1.0, overall_score))
        
        # Generate recommendation
        recommendation = UserProfiler._get_proficiency_label(overall_score)
        
        logger.info(
            f"📊 Proficiency calculated for user {user.key}: "
            f"{overall_score:.2f} ({recommendation})"
        )
        
        return {
            "overall_score": round(overall_score, 3),
            "components": {k: round(v, 3) for k, v in components.items()},
            "weights": WEIGHTS,
            "recommendation": recommendation
        }
    
    @staticmethod
    def _calculate_topic_mastery(
        learner_state: Optional[LearnerState],
        topics: Optional[List[str]]
    ) -> float:
        """
        Calculate average mastery for given topics.
        
        If no topics provided, calculate overall average mastery.
        """
        if not learner_state or not learner_state.mastery:
            return 0.0
        
        mastery_dict = learner_state.mastery
        
        if topics:
            # Average mastery for specific topics
            topic_scores = [
                mastery_dict.get(topic, 0.0) 
                for topic in topics
            ]
            if topic_scores:
                return sum(topic_scores) / len(topic_scores)
            return 0.0
        else:
            # Overall average mastery
            if mastery_dict:
                return sum(mastery_dict.values()) / len(mastery_dict)
            return 0.0
    
    @staticmethod
    def _normalize_rank(rank: int) -> float:
        """
        Normalize expertise rank to 0.0 - 1.0 scale.
        
        100-800: Beginner (0.0 - 0.3)
        800-1500: Intermediate (0.3 - 0.6)
        1500-2000: Advanced (0.6 - 0.85)
        2000-3000: Expert (0.85 - 1.0)
        """
        if rank < RANK_BEGINNER_MAX:
            # Map 100-800 to 0.0-0.3
            return (rank - 100) / (RANK_BEGINNER_MAX - 100) * 0.3
        elif rank < RANK_INTERMEDIATE_MAX:
            # Map 800-1500 to 0.3-0.6
            return 0.3 + (rank - RANK_BEGINNER_MAX) / (RANK_INTERMEDIATE_MAX - RANK_BEGINNER_MAX) * 0.3
        elif rank < RANK_EXPERT_MIN:
            # Map 1500-2000 to 0.6-0.85
            return 0.6 + (rank - RANK_INTERMEDIATE_MAX) / (RANK_EXPERT_MIN - RANK_INTERMEDIATE_MAX) * 0.25
        else:
            # Map 2000-3000 to 0.85-1.0
            return 0.85 + min((rank - RANK_EXPERT_MIN) / 1000, 1.0) * 0.15
    
    @staticmethod
    def _estimate_success_rate(learner_state: Optional[LearnerState]) -> float:
        """
        Estimate submission success rate from streak and mastery.
        
        Higher streak = better consistency = higher score.
        """
        if not learner_state:
            return 0.0
        
        # Use streak as proxy (assumes active users have higher success)
        streak = learner_state.streak or 0
        
        # Map streak to success rate
        # 0 days = 0.0, 7 days = 0.5, 30+ days = 0.9
        if streak == 0:
            return 0.0
        elif streak < 7:
            return streak / 7 * 0.5
        elif streak < 30:
            return 0.5 + (streak - 7) / 23 * 0.4
        else:
            return 0.9
    
    @staticmethod
    def _normalize_streak(learner_state: Optional[LearnerState]) -> float:
        """
        Normalize streak to 0.0 - 1.0.
        
        0 days = 0.0, 30+ days = 1.0
        """
        if not learner_state:
            return 0.0
        
        streak = learner_state.streak or 0
        return min(streak / 30.0, 1.0)
    
    @staticmethod
    def _get_proficiency_label(score: float) -> str:
        """Convert numeric score to human-readable label."""
        if score < 0.2:
            return "Early Beginner"
        elif score < 0.4:
            return "Beginner"
        elif score < 0.6:
            return "Intermediate"
        elif score < 0.8:
            return "Advanced"
        else:
            return "Expert"
    
    @staticmethod
    def adjust_hint_level(
        base_level: int,
        proficiency_score: float
    ) -> int:
        """
        Adjust hint level based on user proficiency.
        
        Args:
            base_level: Requested hint level (1-5)
            proficiency_score: User proficiency (0.0 - 1.0)
            
        Returns:
            Adjusted hint level (1-5)
            
        Logic:
        - Low proficiency (< 0.3): May give easier hint (level - 1)
        - High proficiency (> 0.7): May give harder hint (level + 1)
        - Medium proficiency: Keep as requested
        """
        if proficiency_score < 0.3 and base_level > 1:
            # Make it easier for beginners
            return max(1, base_level - 1)
        elif proficiency_score > 0.7 and base_level < 5:
            # Make it harder for experts
            return min(5, base_level + 1)
        else:
            # Keep as requested
            return base_level


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def calculate_user_proficiency(
    user: User,
    topics: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Convenience function to calculate user proficiency.
    
    Args:
        user: User object
        topics: Optional topics to focus on
        
    Returns:
        Proficiency data dict
    """
    profiler = UserProfiler()
    return profiler.calculate_proficiency(user, topics)


def get_hint_difficulty_prompt(proficiency_score: float) -> str:
    """
    Generate a prompt modifier based on proficiency score.
    
    This gets appended to hint generation prompts to adjust difficulty.
    """
    if proficiency_score < 0.3:
        return "\n\nUser is a beginner. Be extra patient and explain concepts clearly with simple examples."
    elif proficiency_score < 0.5:
        return "\n\nUser has basic understanding. You can use some technical terms but explain them."
    elif proficiency_score < 0.7:
        return "\n\nUser is intermediate. Assume familiarity with common algorithms and data structures."
    else:
        return "\n\nUser is advanced. Be concise, use technical terminology, and assume strong fundamentals."

