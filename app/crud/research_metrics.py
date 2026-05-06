"""
Research Metrics CRUD.

Append-only write helpers for all study instrumentation collections.
Every function inserts a single record; nothing here ever updates or deletes.

Collections:
  mastery_history     — per-submission mastery delta (learning trajectory)
  hint_outcomes       — hint text + link to next submission (effectiveness)
  daily_snapshots     — end-of-day mastery vector + engagement stats
  content_policy_log  — what problem was served and why (40/50/10 audit)
  review_log          — scheduled vs completed SM-2 reviews
  calibration_pairs   — (predicted_mastery_t, actual_outcome_t+1) for Brier/ECE
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
import logging

from arango.database import StandardDatabase

logger = logging.getLogger(__name__)


class ResearchMetricsCRUD:
    def __init__(self, db: StandardDatabase):
        self.db = db
        self.mastery_history = db.collection('mastery_history')
        self.hint_outcomes = db.collection('hint_outcomes')
        self.daily_snapshots = db.collection('daily_snapshots')
        self.content_policy_log = db.collection('content_policy_log')
        self.review_log = db.collection('review_log')
        self.calibration_pairs = db.collection('calibration_pairs')

    # ------------------------------------------------------------------
    # mastery_history
    # ------------------------------------------------------------------

    def log_mastery_update(
        self,
        user_key: str,
        topic: str,
        mastery_before: float,
        mastery_after: float,
        trigger: str,
        question_key: str,
        outcome: int,
        hints_used: int,
        difficulty: Optional[str] = None,
    ) -> None:
        """Append one mastery-delta record after every submission."""
        try:
            self.mastery_history.insert({
                "user_key": user_key,
                "timestamp": datetime.utcnow().isoformat(),
                "topic": topic,
                "mastery_before": round(mastery_before, 6),
                "mastery_after": round(mastery_after, 6),
                "delta": round(mastery_after - mastery_before, 6),
                "trigger": trigger,
                "question_key": question_key,
                "outcome": outcome,
                "hints_used": hints_used,
                "difficulty": difficulty,
            })
        except Exception as e:
            logger.error(f"mastery_history insert failed for {user_key}/{topic}: {e}")

    # ------------------------------------------------------------------
    # hint_outcomes
    # ------------------------------------------------------------------

    def log_hint(
        self,
        user_key: str,
        session_key: str,
        question_key: str,
        hint_level: int,
        hint_text: str,
        proficiency_at_time: float,
    ) -> str:
        """
        Log a hint generation event.  Returns the inserted document _key so
        the caller can later link it to the subsequent submission.
        """
        try:
            doc = self.hint_outcomes.insert({
                "user_key": user_key,
                "session_key": session_key,
                "question_key": question_key,
                "hint_request_timestamp": datetime.utcnow().isoformat(),
                "hint_level": hint_level,
                "hint_text": hint_text,
                "proficiency_at_time": round(proficiency_at_time, 6),
                # These are filled in later by link_hint_to_outcome()
                "next_submission_key": None,
                "next_submission_outcome": None,
                "time_to_next_submission_s": None,
            })
            return doc["_key"]
        except Exception as e:
            logger.error(f"hint_outcomes insert failed for {user_key}: {e}")
            return ""

    def link_hint_to_outcome(
        self,
        hint_doc_key: str,
        submission_key: str,
        outcome: int,
        time_to_submission_s: float,
    ) -> None:
        """Backfill the outcome fields on an existing hint record."""
        if not hint_doc_key:
            return
        try:
            self.hint_outcomes.update({
                "_key": hint_doc_key,
                "next_submission_key": submission_key,
                "next_submission_outcome": outcome,
                "time_to_next_submission_s": round(time_to_submission_s, 2),
            })
        except Exception as e:
            logger.error(f"hint_outcomes link failed for {hint_doc_key}: {e}")

    # ------------------------------------------------------------------
    # daily_snapshots
    # ------------------------------------------------------------------

    def upsert_daily_snapshot(
        self,
        user_key: str,
        snapshot_date: date,
        mastery_vector: Dict[str, float],
        overall_proficiency: float,
        expertise_rank: int,
        problems_attempted: int,
        problems_solved: int,
        hints_requested: int,
        session_duration_s: int,
        active: bool,
        streak_day: int,
    ) -> None:
        """
        Write (or overwrite) the daily snapshot for a user.
        Running multiple times on the same day is idempotent via AQL upsert.
        """
        date_str = snapshot_date.isoformat()
        try:
            self.db.aql.execute(
                """
                UPSERT { user_key: @user_key, date: @date }
                INSERT @doc
                UPDATE @doc
                IN daily_snapshots
                """,
                bind_vars={
                    "user_key": user_key,
                    "date": date_str,
                    "doc": {
                        "user_key": user_key,
                        "date": date_str,
                        "mastery_vector": {k: round(v, 6) for k, v in mastery_vector.items()},
                        "overall_proficiency": round(overall_proficiency, 6),
                        "expertise_rank": expertise_rank,
                        "problems_attempted": problems_attempted,
                        "problems_solved": problems_solved,
                        "hints_requested": hints_requested,
                        "session_duration_s": session_duration_s,
                        "active": active,
                        "streak_day": streak_day,
                        "recorded_at": datetime.utcnow().isoformat(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"daily_snapshots upsert failed for {user_key} on {date_str}: {e}")

    # ------------------------------------------------------------------
    # content_policy_log
    # ------------------------------------------------------------------

    def log_content_served(
        self,
        user_key: str,
        question_key: str,
        topic: str,
        difficulty: str,
        category: str,
        mastery_at_serve_time: float,
        session_key: str,
        review_due_date: Optional[str] = None,
    ) -> None:
        """Log each problem that was served and why (40/50/10 audit)."""
        try:
            self.content_policy_log.insert({
                "user_key": user_key,
                "timestamp": datetime.utcnow().isoformat(),
                "question_key": question_key,
                "topic": topic,
                "difficulty": difficulty,
                "category": category,  # "review" | "growth" | "challenge"
                "mastery_at_serve_time": round(mastery_at_serve_time, 6),
                "review_due_date": review_due_date,
                "session_key": session_key,
            })
        except Exception as e:
            logger.error(f"content_policy_log insert failed for {user_key}: {e}")

    # ------------------------------------------------------------------
    # review_log
    # ------------------------------------------------------------------

    def log_review_scheduled(
        self,
        user_key: str,
        question_key: str,
        topic: str,
        scheduled_due_date: str,
        ease_factor_before: float,
        interval_before_days: int,
    ) -> str:
        """Log a newly scheduled SM-2 review. Returns the doc _key."""
        try:
            doc = self.review_log.insert({
                "user_key": user_key,
                "question_key": question_key,
                "topic": topic,
                "scheduled_due_date": scheduled_due_date,
                "served_at": None,
                "completed_at": None,
                "outcome": None,
                "ease_factor_before": round(ease_factor_before, 4),
                "ease_factor_after": None,
                "interval_before_days": interval_before_days,
                "interval_after_days": None,
            })
            return doc["_key"]
        except Exception as e:
            logger.error(f"review_log insert failed for {user_key}/{question_key}: {e}")
            return ""

    def log_review_completed(
        self,
        user_key: str,
        question_key: str,
        outcome: int,
        ease_factor_after: float,
        interval_after_days: int,
    ) -> None:
        """Mark the most recent open review for this question as completed."""
        try:
            self.db.aql.execute(
                """
                FOR r IN review_log
                  FILTER r.user_key == @user_key
                    AND r.question_key == @question_key
                    AND r.completed_at == null
                  SORT r.scheduled_due_date DESC
                  LIMIT 1
                  UPDATE r WITH {
                    completed_at: @now,
                    outcome: @outcome,
                    ease_factor_after: @efa,
                    interval_after_days: @iad
                  } IN review_log
                """,
                bind_vars={
                    "user_key": user_key,
                    "question_key": question_key,
                    "now": datetime.utcnow().isoformat(),
                    "outcome": outcome,
                    "efa": round(ease_factor_after, 4),
                    "iad": interval_after_days,
                },
            )
        except Exception as e:
            logger.error(f"review_log complete failed for {user_key}/{question_key}: {e}")

    # ------------------------------------------------------------------
    # calibration_pairs
    # ------------------------------------------------------------------

    def log_calibration_pair(
        self,
        user_key: str,
        topic: str,
        predicted_mastery_t: float,
        actual_outcome_t1: int,
    ) -> None:
        """
        Record (predicted mastery at t, actual outcome at t+1) for Brier/ECE.

        Call this immediately after a submission: predicted_mastery_t is the
        mastery value BEFORE the update; actual_outcome_t1 is the outcome
        of the submission just processed.
        """
        try:
            self.calibration_pairs.insert({
                "user_key": user_key,
                "topic": topic,
                "timestamp_t": datetime.utcnow().isoformat(),
                "predicted_mastery_t": round(predicted_mastery_t, 6),
                "actual_outcome_t1": actual_outcome_t1,
            })
        except Exception as e:
            logger.error(f"calibration_pairs insert failed for {user_key}/{topic}: {e}")


# ---------------------------------------------------------------------------
# Module-level helper — mirrors the singleton pattern used elsewhere
# ---------------------------------------------------------------------------

def get_research_metrics(db: StandardDatabase) -> ResearchMetricsCRUD:
    return ResearchMetricsCRUD(db)
