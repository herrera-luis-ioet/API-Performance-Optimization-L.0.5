"""Database connection and session management module."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from ..config import settings

# Create engine with connection pool using settings
engine = create_engine(
    settings.get_database_url(),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=10,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=1800,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create thread-safe session factory
db_session = scoped_session(SessionLocal)

# Create base class for models
Base = declarative_base()

# PUBLIC_INTERFACE
def get_db():
    """Get database session.
    
    This function provides a database session that automatically closes when done.
    It should be used as a dependency in FastAPI endpoints.
    
    Returns:
        Session: Database session
    """
    db = db_session()
    try:
        yield db
    finally:
        db.close()