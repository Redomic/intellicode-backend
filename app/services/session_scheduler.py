import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..db.database import get_db
from ..crud.session import SessionCRUD

logger = logging.getLogger(__name__)


class SessionScheduler:
    """
    Background service to handle session cleanup and auto-expiration
    """
    
    def __init__(self):
        self.is_running = False
        self.cleanup_interval = 300  # 5 minutes
        self.task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the session scheduler"""
        if self.is_running:
            logger.warning("Session scheduler is already running")
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Session scheduler started")
        
    async def stop(self):
        """Stop the session scheduler"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Session scheduler stopped")
        
    async def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info(f"Session scheduler running with {self.cleanup_interval}s interval")
        
        while self.is_running:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session scheduler: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            db = get_db()
            session_crud = SessionCRUD(db)
            
            expired_count = session_crud.cleanup_expired_sessions()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            
    async def cleanup_now(self):
        """Manually trigger cleanup (for API endpoint)"""
        try:
            await self._cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Manual cleanup failed: {e}")
            raise


# Global scheduler instance
session_scheduler = SessionScheduler()


async def start_session_scheduler():
    """Start the session scheduler service"""
    await session_scheduler.start()


async def stop_session_scheduler():
    """Stop the session scheduler service"""
    await session_scheduler.stop()


async def manual_cleanup():
    """Manually trigger session cleanup"""
    await session_scheduler.cleanup_now()
