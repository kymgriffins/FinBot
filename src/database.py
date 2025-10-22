"""
Database configuration for Gr8 Agent
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///gr8_agent.db')

# Create engine
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        echo=False
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db_session() -> Session:
    """Get database session"""
    return SessionLocal()

def init_database():
    """Initialize database tables"""
    try:
        # Import all models to ensure they are registered
        from .models.trade_journal import TradeJournal
        from .models.portfolio import Portfolio
        from .models.strategy import Strategy
        from .models.audit_log import AuditLog
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def drop_database():
    """Drop all database tables"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Error dropping database: {e}")
        raise

def reset_database():
    """Reset database (drop and recreate)"""
    try:
        drop_database()
        init_database()
        logger.info("Database reset successfully")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise
