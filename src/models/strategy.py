"""
Strategy Model for Gr8 Agent
"""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class StrategyType(enum.Enum):
    """Strategy type enumeration"""
    MANUAL = "manual"
    ALGORITHMIC = "algorithmic"
    HYBRID = "hybrid"

class StrategyStatus(enum.Enum):
    """Strategy status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    ARCHIVED = "archived"

class Strategy(Base):
    """Strategy model"""
    __tablename__ = 'strategies'
    
    # Primary key
    id = Column(String(50), primary_key=True)
    
    # Strategy details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(Enum(StrategyType), default=StrategyType.MANUAL)
    status = Column(Enum(StrategyStatus), default=StrategyStatus.ACTIVE)
    
    # Strategy parameters (stored as JSON)
    parameters = Column(JSON, nullable=True)
    
    # Performance metrics (stored as JSON)
    performance_metrics = Column(JSON, nullable=True)
    
    # Risk settings
    max_risk_per_trade = Column(Float, default=0.02)  # 2% max risk per trade
    max_daily_risk = Column(Float, default=0.05)  # 5% max daily risk
    max_positions = Column(Float, default=10)  # Max concurrent positions
    
    # Backtesting results (stored as JSON)
    backtest_results = Column(JSON, nullable=True)
    
    # User and settings
    user_id = Column(String(50), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Strategy(id='{self.id}', name='{self.name}', type='{self.strategy_type}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'strategy_type': self.strategy_type.value if self.strategy_type else None,
            'status': self.status.value if self.status else None,
            'parameters': self.parameters,
            'performance_metrics': self.performance_metrics,
            'max_risk_per_trade': self.max_risk_per_trade,
            'max_daily_risk': self.max_daily_risk,
            'max_positions': self.max_positions,
            'backtest_results': self.backtest_results,
            'user_id': self.user_id,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
