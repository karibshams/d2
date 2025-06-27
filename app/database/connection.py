"""
Database connection management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from config import settings
import logging

logger = logging.getLogger(__name__)

# Fix postgres:// to postgresql:// for SQLAlchemy compatibility
database_url = settings.postgres_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Create engine with connection pooling
engine = create_engine(
    database_url,
    poolclass=NullPool,  # For serverless/lambda compatibility
    echo=False,  # Set to True for SQL query logging
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from typing import Generator

def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False