from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from arango.database import StandardDatabase
from collections import defaultdict

from app.models.submission import (
    SubmissionCreate, SubmissionInDB, Submission,
    UserSubmissionStats, ContributionDay, ContributionHeatmapData,
    SubmissionStatus
)


class SubmissionCRUD:
    """Submission database operations."""
    
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.collection = db.collection('submissions')
    
    def create_submission(self, user_key: str, submission: SubmissionCreate) -> SubmissionInDB:
        """Create a new submission."""
        now = datetime.utcnow()
        
        submission_data = {
            "user_key": user_key,
            "question_key": submission.question_key,
            "question_title": submission.question_title,
            "code": submission.code,
            "language": submission.language,
            "status": submission.status.value,
            "runtime_ms": submission.runtime_ms,
            "memory_kb": submission.memory_kb,
            "total_test_cases": submission.total_test_cases,
            "passed_test_cases": submission.passed_test_cases,
            "failed_test_case_index": submission.failed_test_case_index,
            "error_message": submission.error_message,
            "runtime_percentile": submission.runtime_percentile,
            "memory_percentile": submission.memory_percentile,
            "session_id": submission.session_id,
            "time_taken_seconds": submission.time_taken_seconds,
            "attempts_count": submission.attempts_count,
            "hints_used": submission.hints_used,
            "roadmap_id": submission.roadmap_id,
            "difficulty": submission.difficulty,
            "points_earned": submission.points_earned,
            "solution_quality_score": submission.solution_quality_score,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        result = self.collection.insert(submission_data, return_new=True)
        new_submission = result['new'].copy()
        new_submission['created_at'] = now
        new_submission['updated_at'] = now
        
        return SubmissionInDB(**new_submission)
    
    def get_submission(self, key: str) -> Optional[SubmissionInDB]:
        """Get a submission by key."""
        try:
            submission_data = self.collection.get(key)
            if not submission_data:
                return None
            
            submission_data = submission_data.copy()
            
            # Convert datetime strings
            if 'created_at' in submission_data and isinstance(submission_data['created_at'], str):
                submission_data['created_at'] = datetime.fromisoformat(
                    submission_data['created_at'].replace('Z', '+00:00')
                )
            if 'updated_at' in submission_data and isinstance(submission_data['updated_at'], str):
                submission_data['updated_at'] = datetime.fromisoformat(
                    submission_data['updated_at'].replace('Z', '+00:00')
                )
            
            return SubmissionInDB(**submission_data)
        except Exception as e:
            print(f"Error getting submission: {e}")
            return None
    
    def get_user_submissions(
        self,
        user_key: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[SubmissionStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SubmissionInDB]:
        """Get submissions for a user with optional filters."""
        query_filters = ["s.user_key == @user_key"]
        bind_vars = {"user_key": user_key, "limit": limit, "offset": offset}
        
        if start_date:
            query_filters.append("DATE_FORMAT(s.created_at, '%yyyy-%mm-%dd') >= @start_date")
            bind_vars["start_date"] = start_date.isoformat()
        
        if end_date:
            query_filters.append("DATE_FORMAT(s.created_at, '%yyyy-%mm-%dd') <= @end_date")
            bind_vars["end_date"] = end_date.isoformat()
        
        if status:
            query_filters.append("s.status == @status")
            bind_vars["status"] = status.value
        
        query = f"""
        FOR s IN submissions
        FILTER {" AND ".join(query_filters)}
        SORT s.created_at DESC
        LIMIT @offset, @limit
        RETURN s
        """
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        
        submissions = []
        for submission_data in cursor:
            submission_data = submission_data.copy()
            
            # Convert datetime strings
            if 'created_at' in submission_data and isinstance(submission_data['created_at'], str):
                submission_data['created_at'] = datetime.fromisoformat(
                    submission_data['created_at'].replace('Z', '+00:00')
                )
            if 'updated_at' in submission_data and isinstance(submission_data['updated_at'], str):
                submission_data['updated_at'] = datetime.fromisoformat(
                    submission_data['updated_at'].replace('Z', '+00:00')
                )
            
            submissions.append(SubmissionInDB(**submission_data))
        
        return submissions
    
    def get_user_submission_stats(self, user_key: str) -> UserSubmissionStats:
        """Get comprehensive submission statistics for a user."""
        query = """
        LET submissions = (
            FOR s IN submissions
            FILTER s.user_key == @user_key
            RETURN s
        )
        
        LET accepted = (
            FOR s IN submissions
            FILTER s.status == "Accepted"
            RETURN s
        )
        
        LET unique_problems = (
            FOR s IN accepted
            COLLECT question = s.question_key
            RETURN question
        )
        
        LET difficulty_breakdown = (
            FOR s IN accepted
            FILTER s.difficulty != null
            COLLECT difficulty = s.difficulty WITH COUNT INTO count
            RETURN {difficulty: difficulty, count: count}
        )
        
        LET performance_metrics = (
            FOR s IN accepted
            FILTER s.runtime_percentile != null OR s.memory_percentile != null
            RETURN {
                runtime: s.runtime_percentile,
                memory: s.memory_percentile
            }
        )
        
        LET total_points = SUM(accepted[*].points_earned)
        
        LET submission_dates = (
            FOR s IN accepted
            COLLECT date = DATE_FORMAT(s.created_at, '%yyyy-%mm-%dd')
            RETURN date
        )
        
        RETURN {
            total_submissions: LENGTH(submissions),
            accepted_submissions: LENGTH(accepted),
            total_problems_solved: LENGTH(unique_problems),
            difficulty_breakdown: difficulty_breakdown,
            performance_metrics: performance_metrics,
            total_points: total_points,
            submission_dates: submission_dates,
            last_submission: MAX(submissions[*].created_at)
        }
        """
        
        cursor = self.db.aql.execute(query, bind_vars={"user_key": user_key})
        results = list(cursor)
        result = results[0] if results else {}
        
        if not result:
            return UserSubmissionStats()
        
        # Calculate acceptance rate
        total_subs = result.get('total_submissions', 0)
        accepted_subs = result.get('accepted_submissions', 0)
        acceptance_rate = (accepted_subs / total_subs * 100) if total_subs > 0 else 0.0
        
        # Parse difficulty breakdown
        difficulty_breakdown = result.get('difficulty_breakdown', [])
        easy_solved = 0
        medium_solved = 0
        hard_solved = 0
        
        for item in difficulty_breakdown:
            diff = item.get('difficulty', '').lower()
            count = item.get('count', 0)
            if 'easy' in diff or 'beginner' in diff:
                easy_solved = count
            elif 'medium' in diff or 'intermediate' in diff:
                medium_solved = count
            elif 'hard' in diff or 'advanced' in diff:
                hard_solved = count
        
        # Calculate average performance percentiles
        performance_metrics = result.get('performance_metrics', [])
        runtime_percentiles = [m['runtime'] for m in performance_metrics if m.get('runtime')]
        memory_percentiles = [m['memory'] for m in performance_metrics if m.get('memory')]
        
        avg_runtime = sum(runtime_percentiles) / len(runtime_percentiles) if runtime_percentiles else 0.0
        avg_memory = sum(memory_percentiles) / len(memory_percentiles) if memory_percentiles else 0.0
        
        # Calculate streak
        submission_dates = sorted(result.get('submission_dates', []))
        current_streak, longest_streak = self._calculate_streaks(submission_dates)
        
        # Parse last submission
        last_submission = result.get('last_submission')
        if last_submission and isinstance(last_submission, str):
            last_submission = datetime.fromisoformat(last_submission.replace('Z', '+00:00'))
        
        return UserSubmissionStats(
            total_submissions=total_subs,
            accepted_submissions=accepted_subs,
            acceptance_rate=round(acceptance_rate, 1),
            total_problems_solved=result.get('total_problems_solved', 0),
            easy_solved=easy_solved,
            medium_solved=medium_solved,
            hard_solved=hard_solved,
            average_runtime_percentile=round(avg_runtime, 1),
            average_memory_percentile=round(avg_memory, 1),
            total_points=result.get('total_points', 0),
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_active_days=len(submission_dates),
            last_submission=last_submission
        )
    
    def _calculate_streaks(self, submission_dates: List[str]) -> tuple[int, int]:
        """Calculate current and longest streaks from submission dates."""
        if not submission_dates:
            return 0, 0
        
        # Convert to date objects
        dates = [date.fromisoformat(d) if isinstance(d, str) else d for d in submission_dates]
        dates = sorted(set(dates))
        
        # Calculate current streak
        current_streak = 0
        today = date.today()
        
        if today in dates or (today - timedelta(days=1)) in dates:
            current_date = today if today in dates else (today - timedelta(days=1))
            
            for d in reversed(dates):
                if d == current_date:
                    current_streak += 1
                    current_date -= timedelta(days=1)
                elif d < current_date - timedelta(days=1):
                    break
        
        # Calculate longest streak
        longest_streak = 0
        temp_streak = 1
        
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        longest_streak = max(longest_streak, temp_streak)
        
        return current_streak, longest_streak
    
    def get_contribution_heatmap(
        self,
        user_key: str,
        days: int = 365
    ) -> ContributionHeatmapData:
        """Get contribution heatmap data for the specified number of days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        # Get accepted submissions for the date range
        query = """
        FOR s IN submissions
        FILTER s.user_key == @user_key 
            AND s.status == "Accepted"
            AND DATE_FORMAT(s.created_at, '%yyyy-%mm-%dd') >= @start_date 
            AND DATE_FORMAT(s.created_at, '%yyyy-%mm-%dd') <= @end_date
        COLLECT submission_date = DATE_FORMAT(s.created_at, '%yyyy-%mm-%dd')
        AGGREGATE 
            count = COUNT(1),
            points = SUM(s.points_earned)
        RETURN {
            date: submission_date,
            count: count,
            points: points
        }
        """
        
        cursor = self.db.aql.execute(query, bind_vars={
            "user_key": user_key,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        activities = {
            date.fromisoformat(a['date']) if isinstance(a['date'], str) else a['date']: a 
            for a in cursor
        }
        
        # Generate all days in range
        contribution_days = []
        current_date = start_date
        
        while current_date <= end_date:
            activity = activities.get(current_date)
            
            if activity:
                count = activity.get('count', 0)
                points = activity.get('points', 0)
            else:
                count = 0
                points = 0
            
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
                points=points
            ))
            
            current_date += timedelta(days=1)
        
        # Calculate summary statistics
        total_contributions = sum(day.count for day in contribution_days)
        active_days = sum(1 for day in contribution_days if day.count > 0)
        best_day = max((day.count for day in contribution_days), default=0)
        daily_average = total_contributions / len(contribution_days) if contribution_days else 0
        
        # Get streak info
        submission_dates = [day.date for day in contribution_days if day.count > 0]
        current_streak, longest_streak = self._calculate_streaks(submission_dates)
        
        return ContributionHeatmapData(
            days=contribution_days,
            total_contributions=total_contributions,
            active_days=active_days,
            current_streak=current_streak,
            longest_streak=longest_streak,
            best_day=best_day,
            daily_average=round(daily_average, 1)
        )
    
    def get_problems_solved_for_roadmap(
        self,
        user_key: str,
        roadmap_id: Optional[str] = None
    ) -> List[str]:
        """Get list of question keys solved by user for a specific roadmap."""
        query_filters = ["s.user_key == @user_key", "s.status == 'Accepted'"]
        bind_vars = {"user_key": user_key}
        
        if roadmap_id:
            query_filters.append("s.roadmap_id == @roadmap_id")
            bind_vars["roadmap_id"] = roadmap_id
        
        query = f"""
        FOR s IN submissions
        FILTER {" AND ".join(query_filters)}
        COLLECT question_key = s.question_key
        RETURN question_key
        """
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return list(cursor)
    
    def get_question_attempts_count(self, user_key: str, question_key: str) -> int:
        """Get the number of attempts for a specific question."""
        query = """
        FOR s IN submissions
        FILTER s.user_key == @user_key AND s.question_key == @question_key
        COLLECT WITH COUNT INTO attempts
        RETURN attempts
        """
        
        cursor = self.db.aql.execute(query, bind_vars={
            "user_key": user_key,
            "question_key": question_key
        })
        
        result = list(cursor)
        return result[0] if result else 0
    
    def get_latest_submission_for_question(
        self,
        user_key: str,
        question_key: str
    ) -> Optional[SubmissionInDB]:
        """Get the latest submission for a specific question."""
        query = """
        FOR s IN submissions
        FILTER s.user_key == @user_key AND s.question_key == @question_key
        SORT s.created_at DESC
        LIMIT 1
        RETURN s
        """
        
        cursor = self.db.aql.execute(query, bind_vars={
            "user_key": user_key,
            "question_key": question_key
        })
        
        result = list(cursor)
        if not result:
            return None
        
        submission_data = result[0].copy()
        
        # Convert datetime strings
        if 'created_at' in submission_data and isinstance(submission_data['created_at'], str):
            submission_data['created_at'] = datetime.fromisoformat(
                submission_data['created_at'].replace('Z', '+00:00')
            )
        if 'updated_at' in submission_data and isinstance(submission_data['updated_at'], str):
            submission_data['updated_at'] = datetime.fromisoformat(
                submission_data['updated_at'].replace('Z', '+00:00')
            )
        
        return SubmissionInDB(**submission_data)
