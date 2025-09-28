from arango import ArangoClient
from arango.database import StandardDatabase
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Singleton database manager for ArangoDB connections."""
    
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_database(self) -> StandardDatabase:
        """Get or create database connection."""
        if self._db is None:
            self._connect()
        return self._db
    
    def _connect(self) -> None:
        """Establish connection to ArangoDB."""
        try:
            client = ArangoClient(hosts=settings.ARANGO_URL)
            
            # Connect to system database for setup
            sys_db = client.db(
                '_system',
                username=settings.ARANGO_USERNAME,
                password=settings.ARANGO_PASSWORD
            )
            
            # Create application database if needed
            if not sys_db.has_database(settings.ARANGO_DATABASE):
                sys_db.create_database(settings.ARANGO_DATABASE)
                logger.info(f"Created database: {settings.ARANGO_DATABASE}")
            
            # Connect to application database
            self._db = client.db(
                settings.ARANGO_DATABASE,
                username=settings.ARANGO_USERNAME,
                password=settings.ARANGO_PASSWORD
            )
            
            self._ensure_collections()
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _ensure_collections(self) -> None:
        """Create required collections if they don't exist."""
        collections = [
            'users', 'problems', 'submissions', 'progress', 'questions', 'assessments',
            'problem_solving_sessions', 'user_activities', 'user_stats',
            'behavior_tracking_sessions', 'session_analyses', 'behavior_summaries',
            'roadmap'  # Comprehensive LeetCode questions from A2Z roadmap
        ]
        
        for collection_name in collections:
            if not self._db.has_collection(collection_name):
                self._db.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")

# Database dependency for FastAPI
def get_db() -> StandardDatabase:
    """FastAPI dependency to get database instance."""
    return DatabaseManager().get_database()
