import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from ..db.database import get_db
from ..crud.session import SessionCRUD

logger = logging.getLogger(__name__)


class SessionScheduler:
    """
    Background service that runs two periodic tasks:
      1. Session cleanup   — every 5 minutes
      2. Daily snapshot    — once per day (at next midnight boundary or at startup
                             if today's snapshot is missing)
    """

    def __init__(self):
        self.is_running = False
        self.cleanup_interval = 300        # 5 minutes
        self.snapshot_interval = 3600      # check every hour; write only once/day
        self._cleanup_task: Optional[asyncio.Task] = None
        self._snapshot_task: Optional[asyncio.Task] = None

    async def start(self):
        if self.is_running:
            logger.warning("Session scheduler is already running")
            return

        self.is_running = True
        self._cleanup_task = asyncio.create_task(self._run_cleanup_loop())
        self._snapshot_task = asyncio.create_task(self._run_snapshot_loop())
        logger.info("Session scheduler started (cleanup + daily-snapshot)")

    async def stop(self):
        if not self.is_running:
            return

        self.is_running = False
        for task in (self._cleanup_task, self._snapshot_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("Session scheduler stopped")

    # ------------------------------------------------------------------
    # Session cleanup loop
    # ------------------------------------------------------------------

    async def _run_cleanup_loop(self):
        logger.info(f"Cleanup loop running every {self.cleanup_interval}s")
        while self.is_running:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _cleanup_expired_sessions(self):
        try:
            db = get_db()
            session_crud = SessionCRUD(db)
            expired_count = session_crud.cleanup_expired_sessions()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")

    async def cleanup_now(self):
        """Manually trigger cleanup (for API endpoint)."""
        await self._cleanup_expired_sessions()

    # ------------------------------------------------------------------
    # Daily snapshot loop
    # ------------------------------------------------------------------

    async def _run_snapshot_loop(self):
        """
        Runs every hour.  Writes today's snapshot for every study participant
        who has been active since the last snapshot.  Using an hourly check
        (rather than a midnight-only trigger) means the snapshot is refreshed
        throughout the day so the final value at end-of-day is accurate.
        """
        logger.info("Daily-snapshot loop running (hourly check)")
        while self.is_running:
            try:
                await self._write_daily_snapshots()
                await asyncio.sleep(self.snapshot_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in snapshot loop: {e}")
                await asyncio.sleep(300)

    async def _write_daily_snapshots(self):
        """
        For every study participant, compute today's aggregate stats and
        upsert a daily_snapshots record.  Uses AQL to pull submission counts
        and session durations directly from the database so the snapshot task
        stays self-contained.
        """
        try:
            db = get_db()
            from ..crud.research_metrics import ResearchMetricsCRUD
            from ..utils.user_profiling import calculate_user_proficiency
            from ..crud.learner_state import LearnerStateCRUD
            from ..models.user import User

            metrics = ResearchMetricsCRUD(db)
            learner_crud = LearnerStateCRUD(db)
            today_str = date.today().isoformat()

            # Fetch all study participants
            cursor = db.aql.execute(
                "FOR u IN users FILTER u.is_study_participant == true RETURN u"
            )
            participants = list(cursor)

            if not participants:
                return

            logger.info(f"Writing daily snapshots for {len(participants)} study participants")

            for u_doc in participants:
                try:
                    user_key = u_doc["_key"]

                    # Today's submission stats
                    stats_cursor = db.aql.execute(
                        """
                        LET subs = (
                            FOR s IN submissions
                              FILTER s.user_key == @uk
                                AND DATE_FORMAT(s.created_at, "%yyyy-%mm-%dd") == @today
                              RETURN s
                        )
                        RETURN {
                            attempted: LENGTH(subs),
                            solved: LENGTH(subs[* FILTER CURRENT.status == "Accepted"]),
                            hints: SUM(subs[*].hints_used)
                        }
                        """,
                        bind_vars={"uk": user_key, "today": today_str},
                    )
                    stats = list(stats_cursor)
                    day_stats = stats[0] if stats else {"attempted": 0, "solved": 0, "hints": 0}

                    # Today's total session duration (seconds)
                    dur_cursor = db.aql.execute(
                        """
                        FOR s IN sessions
                          FILTER s.user_key == @uk
                            AND DATE_FORMAT(s.created_at, "%yyyy-%mm-%dd") == @today
                          RETURN DATE_DIFF(s.created_at, s.last_activity, "s", false)
                        """,
                        bind_vars={"uk": user_key, "today": today_str},
                    )
                    durations = [d for d in dur_cursor if d and d > 0]
                    session_duration_s = int(sum(durations))

                    # Learner state & proficiency
                    learner_state = learner_crud.get_or_initialize(user_key)

                    # Build a minimal user object for proficiency calc
                    user_obj = User.model_validate({
                        "_key": user_key,
                        "email": u_doc.get("email", ""),
                        "name": u_doc.get("name", ""),
                        "created_at": u_doc.get("created_at", datetime.utcnow().isoformat()),
                        "expertise_rank": u_doc.get("expertise_rank", 600),
                        "skill_level": u_doc.get("skill_level"),
                        "learner_state": learner_state.model_dump(mode="json") if learner_state else None,
                    })
                    proficiency_data = calculate_user_proficiency(user_obj, [])
                    overall_proficiency = proficiency_data.get("overall_score", 0.0)

                    metrics.upsert_daily_snapshot(
                        user_key=user_key,
                        snapshot_date=date.today(),
                        mastery_vector=learner_state.mastery if learner_state else {},
                        overall_proficiency=overall_proficiency,
                        expertise_rank=u_doc.get("expertise_rank", 600),
                        problems_attempted=day_stats.get("attempted", 0),
                        problems_solved=day_stats.get("solved", 0),
                        hints_requested=day_stats.get("hints", 0),
                        session_duration_s=session_duration_s,
                        active=day_stats.get("attempted", 0) > 0,
                        streak_day=learner_state.streak if learner_state else 0,
                    )
                except Exception as e:
                    logger.error(f"Snapshot failed for user {u_doc.get('_key')}: {e}")

        except Exception as e:
            logger.error(f"_write_daily_snapshots outer error: {e}")


# Global scheduler instance
session_scheduler = SessionScheduler()


async def start_session_scheduler():
    await session_scheduler.start()


async def stop_session_scheduler():
    await session_scheduler.stop()


async def manual_cleanup():
    await session_scheduler.cleanup_now()
