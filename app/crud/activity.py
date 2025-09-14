from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from arango.database import StandardDatabase
import statistics
from collections import defaultdict

from app.models.activity import (
    ProblemSolvingSessionCreate, ProblemSolvingSessionInDB, ProblemSolvingSession,
    UserActivityCreate, UserActivityInDB, UserActivity,
    UserStatsInDB, UserStats, UserStreakInfo,
    ContributionDay, ContributionHeatmapData, DashboardStats,
    ActivityType, DifficultyLevel
)

class ActivityCRUD:
    """Activity and progress tracking database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.sessions_collection = db.collection('problem_solving_sessions')
        self.activity_collection = db.collection('user_activities')
        self.stats_collection = db.collection('user_stats')
        
        # Rank titles based on expertise_rank
        self.RANK_TITLES = {
            (0, 700): "Newbie",
            (700, 900): "Apprentice", 
            (900, 1200): "Specialist",
            (1200, 1500): "Expert",
            (1500, 1800): "Candidate Master",
            (1800, 2100): "Master",
            (2100, 2400): "International Master",
            (2400, 3000): "Grandmaster"
        }
    
    def create_problem_solving_session(self, session: ProblemSolvingSessionCreate) -> ProblemSolvingSessionInDB:
        """Create a new problem solving session."""
        now = datetime.utcnow()
        
        session_data = {
            "user_key": session.user_key,
            "question_key": session.question_key,
            "difficulty": session.difficulty.value,
            "is_correct": session.is_correct,
            "time_taken_seconds": session.time_taken_seconds,
            "points_earned": session.points_earned,
            "session_date": session.session_date.isoformat(),
            "created_at": now.isoformat(),
            "hints_used": 0,
            "attempts_count": 1
        }
        
        result = self.sessions_collection.insert(session_data, return_new=True)
        new_session_data = result['new'].copy()
        new_session_data['created_at'] = now
        new_session_data['session_date'] = session.session_date
        
        # Update user's daily activity
        self._update_daily_activity(session.user_key, session.session_date, session)
        
        return ProblemSolvingSessionInDB(**new_session_data)
    
    def get_user_sessions(self, user_key: str, start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 100) -> List[ProblemSolvingSessionInDB]:
        """Get problem solving sessions for a user within date range."""
        query_filters = ["s.user_key == @user_key"]
        bind_vars = {"user_key": user_key, "limit": limit}
        
        if start_date:
            query_filters.append("s.session_date >= @start_date")
            bind_vars["start_date"] = start_date.isoformat()
        
        if end_date:
            query_filters.append("s.session_date <= @end_date")
            bind_vars["end_date"] = end_date.isoformat()
        
        query = f"""
        FOR s IN problem_solving_sessions
        FILTER {" AND ".join(query_filters)}
        SORT s.session_date DESC, s.created_at DESC
        LIMIT @limit
        RETURN s
        """
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        sessions = []
        for session_data in cursor:
            session_data = session_data.copy()
            
            # Convert datetime strings
            if 'created_at' in session_data and isinstance(session_data['created_at'], str):
                session_data['created_at'] = datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00'))
            if 'updated_at' in session_data and isinstance(session_data['updated_at'], str):
                session_data['updated_at'] = datetime.fromisoformat(session_data['updated_at'].replace('Z', '+00:00'))
            if 'session_date' in session_data and isinstance(session_data['session_date'], str):
                session_data['session_date'] = date.fromisoformat(session_data['session_date'])
            
            sessions.append(ProblemSolvingSessionInDB(**session_data))
        
        return sessions
    
    def _update_daily_activity(self, user_key: str, activity_date: date, session: ProblemSolvingSessionCreate):
        """Update or create daily activity record."""
        # Try to get existing activity for the date
        query = """
        FOR a IN user_activities
        FILTER a.user_key == @user_key AND a.activity_date == @activity_date
        RETURN a
        """
        
        cursor = self.db.aql.execute(query, bind_vars={
            "user_key": user_key,
            "activity_date": activity_date.isoformat()
        })
        
        existing_activities = list(cursor)
        now = datetime.utcnow()
        
        if existing_activities:
            # Update existing activity
            activity_data = existing_activities[0]
            activity_key = activity_data['_key']
            
            # Calculate new values
            new_problems_solved = activity_data.get('problems_solved', 0) + (1 if session.is_correct else 0)
            new_points_earned = activity_data.get('points_earned', 0) + session.points_earned
            new_time_spent = activity_data.get('time_spent_minutes', 0) + (session.time_taken_seconds / 60)
            new_total_sessions = activity_data.get('total_sessions', 0) + 1
            
            # Update difficulty breakdown
            difficulty_breakdown = activity_data.get('difficulty_breakdown', {})
            difficulty_key = session.difficulty.value
            difficulty_breakdown[difficulty_key] = difficulty_breakdown.get(difficulty_key, 0) + 1
            
            update_data = {
                "problems_solved": new_problems_solved,
                "points_earned": new_points_earned,
                "time_spent_minutes": int(new_time_spent),
                "total_sessions": new_total_sessions,
                "difficulty_breakdown": difficulty_breakdown,
                "updated_at": now.isoformat()
            }
            
            self.activity_collection.update(activity_key, update_data)
        else:
            # Create new activity record
            activity_data = {
                "user_key": user_key,
                "activity_date": activity_date.isoformat(),
                "problems_solved": 1 if session.is_correct else 0,
                "points_earned": session.points_earned,
                "time_spent_minutes": int(session.time_taken_seconds / 60),
                "total_sessions": 1,
                "difficulty_breakdown": {session.difficulty.value: 1},
                "activity_types": [ActivityType.PROBLEM_SOLVED.value],
                "created_at": now.isoformat()
            }
            
            self.activity_collection.insert(activity_data)
        
        # Update user's overall statistics
        self._update_user_stats(user_key, session)
        
        # Update streak information
        self._update_user_streak(user_key, activity_date)
    
    def _update_user_stats(self, user_key: str, session: ProblemSolvingSessionCreate):
        """Update user's overall statistics."""
        # Try to get existing stats
        query = """
        FOR s IN user_stats
        FILTER s.user_key == @user_key
        RETURN s
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"user_key": user_key})
        existing_stats = list(cursor)
        now = datetime.utcnow()
        
        if existing_stats:
            # Update existing stats
            stats_data = existing_stats[0]
            stats_key = stats_data['_key']
            
            new_total_problems = stats_data.get('total_problems_solved', 0) + (1 if session.is_correct else 0)
            new_total_points = stats_data.get('total_points_earned', 0) + session.points_earned
            new_total_time = stats_data.get('total_time_spent_minutes', 0) + (session.time_taken_seconds / 60)
            
            # Calculate acceptance rate
            # This is a simplified calculation - in practice you'd track attempts vs successes
            total_attempts = stats_data.get('total_attempts', 0) + 1
            acceptance_rate = (new_total_problems / total_attempts * 100) if total_attempts > 0 else 0
            
            update_data = {
                "total_problems_solved": new_total_problems,
                "total_points_earned": new_total_points,
                "total_time_spent_minutes": int(new_total_time),
                "total_attempts": total_attempts,
                "acceptance_rate": round(acceptance_rate, 1),
                "updated_at": now.isoformat()
            }
            
            self.stats_collection.update(stats_key, update_data)
        else:
            # Create new stats record
            stats_data = {
                "user_key": user_key,
                "total_problems_solved": 1 if session.is_correct else 0,
                "total_points_earned": session.points_earned,
                "total_time_spent_minutes": int(session.time_taken_seconds / 60),
                "total_attempts": 1,
                "acceptance_rate": 100.0 if session.is_correct else 0.0,
                "difficulty_stats": {},
                "monthly_stats": {},
                "skill_category_stats": {},
                "created_at": now.isoformat()
            }
            
            self.stats_collection.insert(stats_data)
    
    def _update_user_streak(self, user_key: str, activity_date: date):
        """Update user's streak information."""
        # Get user's recent activities to calculate streak
        end_date = activity_date
        start_date = activity_date - timedelta(days=365)  # Check last year for streak calculation
        
        query = """
        FOR a IN user_activities
        FILTER a.user_key == @user_key AND a.activity_date >= @start_date AND a.activity_date <= @end_date
        SORT a.activity_date DESC
        RETURN a
        """
        
        cursor = self.db.aql.execute(query, bind_vars={
            "user_key": user_key,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        activities = list(cursor)
        
        # Calculate current streak
        current_streak = 0
        current_date = activity_date
        
        for activity in activities:
            activity_date_obj = date.fromisoformat(activity['activity_date'])
            if activity_date_obj == current_date and activity.get('problems_solved', 0) > 0:
                current_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Update the latest activity record with streak info
        if activities:
            latest_activity = activities[0]
            activity_key = latest_activity['_key']
            
            update_data = {
                "streak_count": current_streak,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.activity_collection.update(activity_key, update_data)
    
    def get_user_streak_info(self, user_key: str) -> UserStreakInfo:
        """Get comprehensive streak information for a user."""
        # Get all user activities sorted by date
        query = """
        FOR a IN user_activities
        FILTER a.user_key == @user_key AND a.problems_solved > 0
        SORT a.activity_date DESC
        RETURN a
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"user_key": user_key})
        activities = list(cursor)
        
        if not activities:
            return UserStreakInfo(
                current_streak=0,
                longest_streak=0,
                total_active_days=0
            )
        
        # Calculate current streak
        current_streak = 0
        today = date.today()
        current_date = today
        
        # Check if user was active today or yesterday (allow 1 day gap)
        activity_dates = {date.fromisoformat(a['activity_date']) for a in activities}
        
        if today in activity_dates:
            current_date = today
        elif (today - timedelta(days=1)) in activity_dates:
            current_date = today - timedelta(days=1)
        else:
            current_streak = 0
        
        if current_streak != 0:  # Only calculate if there's a potential streak
            for activity in activities:
                activity_date = date.fromisoformat(activity['activity_date'])
                if activity_date == current_date:
                    current_streak += 1
                    current_date -= timedelta(days=1)
                elif activity_date == current_date - timedelta(days=1):
                    # Allow for one day gap
                    current_date = activity_date
                else:
                    break
        
        # Calculate longest streak
        longest_streak = 0
        temp_streak = 0
        prev_date = None
        
        for activity in reversed(activities):  # Go chronologically
            activity_date = date.fromisoformat(activity['activity_date'])
            
            if prev_date is None or activity_date == prev_date + timedelta(days=1):
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
            
            prev_date = activity_date
        
        # Get last activity date
        last_activity_date = date.fromisoformat(activities[0]['activity_date']) if activities else None
        
        return UserStreakInfo(
            current_streak=current_streak,
            longest_streak=longest_streak,
            last_activity_date=last_activity_date,
            total_active_days=len(activities)
        )
    
    def get_contribution_heatmap_data(self, user_key: str, days: int = 365) -> ContributionHeatmapData:
        """Get contribution heatmap data for the specified number of days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        # Get activities for the date range
        query = """
        FOR a IN user_activities
        FILTER a.user_key == @user_key AND a.activity_date >= @start_date AND a.activity_date <= @end_date
        SORT a.activity_date ASC
        RETURN a
        """
        
        cursor = self.db.aql.execute(query, bind_vars={
            "user_key": user_key,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        activities = {date.fromisoformat(a['activity_date']): a for a in cursor}
        
        # Generate all days in range
        contribution_days = []
        current_date = start_date
        
        while current_date <= end_date:
            activity = activities.get(current_date)
            
            if activity:
                count = activity.get('problems_solved', 0)
                points = activity.get('points_earned', 0)
                sessions = activity.get('total_sessions', 0)
            else:
                count = 0
                points = 0
                sessions = 0
            
            # Calculate intensity level (0-4)
            level = 0
            if count > 0:
                if count >= 5:
                    level = 4
                elif count >= 3:
                    level = 3
                elif count >= 2:
                    level = 2
                else:
                    level = 1
            
            contribution_days.append(ContributionDay(
                date=current_date.isoformat(),
                count=count,
                level=level,
                points=points,
                sessions=sessions
            ))
            
            current_date += timedelta(days=1)
        
        # Calculate summary statistics
        total_contributions = sum(day.count for day in contribution_days)
        active_days = sum(1 for day in contribution_days if day.count > 0)
        best_day = max((day.count for day in contribution_days), default=0)
        daily_average = total_contributions / len(contribution_days) if contribution_days else 0
        
        # Get streak info
        streak_info = self.get_user_streak_info(user_key)
        
        return ContributionHeatmapData(
            days=contribution_days,
            total_contributions=total_contributions,
            active_days=active_days,
            current_streak=streak_info.current_streak,
            longest_streak=streak_info.longest_streak,
            best_day=best_day,
            daily_average=round(daily_average, 1)
        )
    
    def get_rank_title(self, expertise_rank: int) -> str:
        """Get rank title based on expertise rank."""
        for (min_rank, max_rank), title in self.RANK_TITLES.items():
            if min_rank <= expertise_rank < max_rank:
                return title
        return "Grandmaster"  # For ranks above 2400
    
    def calculate_user_rankings(self, user_key: str) -> Tuple[Optional[int], Optional[int]]:
        """Calculate global and country rankings for a user."""
        # Get user's expertise rank
        from app.crud.user import UserCRUD
        user_crud = UserCRUD(self.db)
        user = user_crud.get_user_by_key(user_key)
        
        if not user:
            return None, None
        
        user_rank = user.expertise_rank
        
        # Calculate global rank
        global_rank_query = """
        FOR u IN users
        FILTER u.expertise_rank > @user_rank
        COLLECT WITH COUNT INTO higher_ranked_count
        RETURN higher_ranked_count
        """
        
        cursor = self.db.aql.execute(global_rank_query, bind_vars={"user_rank": user_rank})
        global_rank = list(cursor)[0] + 1  # +1 because rank is 1-indexed
        
        # For country rank, we'd need country information in user profile
        # For now, return a placeholder calculation
        country_rank = max(1, global_rank // 10)  # Simplified country rank
        
        return global_rank, country_rank
    
    def get_dashboard_stats(self, user_key: str) -> Optional[DashboardStats]:
        """Get comprehensive dashboard statistics for a user."""
        from app.crud.user import UserCRUD
        user_crud = UserCRUD(self.db)
        user = user_crud.get_user_by_key(user_key)
        
        if not user:
            return None
        
        # Get user statistics
        stats_query = """
        FOR s IN user_stats
        FILTER s.user_key == @user_key
        RETURN s
        """
        
        cursor = self.db.aql.execute(stats_query, bind_vars={"user_key": user_key})
        stats_list = list(cursor)
        
        if stats_list:
            stats = stats_list[0]
            problems_solved = stats.get('total_problems_solved', 0)
            acceptance_rate = stats.get('acceptance_rate', 0.0)
            total_points = stats.get('total_points_earned', 0)
        else:
            problems_solved = 0
            acceptance_rate = 0.0
            total_points = 0
        
        # Get streak information
        streak_info = self.get_user_streak_info(user_key)
        
        # Get rankings
        global_rank, country_rank = self.calculate_user_rankings(user_key)
        
        # Get recent activity (last 7 days)
        recent_end = date.today()
        recent_start = recent_end - timedelta(days=6)
        recent_heatmap = self.get_contribution_heatmap_data(user_key, days=7)
        
        # Calculate monthly average
        monthly_activities = self.get_user_sessions(user_key, 
                                                  start_date=date.today() - timedelta(days=30),
                                                  end_date=date.today())
        monthly_problems = len([s for s in monthly_activities if s.is_correct])
        monthly_average = monthly_problems / 30.0 * 30  # Problems per month
        
        # Get skill analysis (simplified)
        skill_strengths = []
        areas_for_improvement = []
        
        if acceptance_rate >= 80:
            skill_strengths.append("Problem Solving")
        if problems_solved >= 50:
            skill_strengths.append("Consistency")
        if streak_info.current_streak >= 7:
            skill_strengths.append("Daily Practice")
        
        if acceptance_rate < 60:
            areas_for_improvement.append("Accuracy")
        if problems_solved < 20:
            areas_for_improvement.append("Volume")
        if streak_info.current_streak < 3:
            areas_for_improvement.append("Consistency")
        
        return DashboardStats(
            expertise_rank=user.expertise_rank,
            rank_title=self.get_rank_title(user.expertise_rank),
            peak_rank=user.peak_rank or user.expertise_rank,
            global_rank=global_rank,
            country_rank=country_rank,
            problems_solved=problems_solved,
            acceptance_rate=acceptance_rate,
            current_streak=streak_info.current_streak,
            longest_streak=streak_info.longest_streak,
            total_active_days=streak_info.total_active_days,
            total_points=total_points,
            monthly_average=round(monthly_average, 1),
            recent_activity=recent_heatmap.days,
            skill_strengths=skill_strengths,
            areas_for_improvement=areas_for_improvement
        )
