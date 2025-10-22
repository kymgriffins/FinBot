"""
Portfolio Model for Gr8 Agent
"""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Portfolio(Base):
    """Portfolio model"""
    __tablename__ = 'portfolios'
    
    # Primary key
    id = Column(String(50), primary_key=True)
    
    # Portfolio details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Financial metrics
    initial_capital = Column(Float, nullable=False)
    current_value = Column(Float, nullable=True)
    total_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    
    # Portfolio settings
    risk_tolerance = Column(String(20), default='medium')  # low, medium, high
    max_position_size = Column(Float, default=0.1)  # 10% max per position
    max_drawdown_limit = Column(Float, default=0.2)  # 20% max drawdown
    
    # Performance metrics (stored as JSON)
    performance_metrics = Column(JSON, nullable=True)
    
    # User and settings
    user_id = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Portfolio(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'initial_capital': self.initial_capital,
            'current_value': self.current_value,
            'total_pnl': self.total_pnl,
            'total_fees': self.total_fees,
            'risk_tolerance': self.risk_tolerance,
            'max_position_size': self.max_position_size,
            'max_drawdown_limit': self.max_drawdown_limit,
            'performance_metrics': self.performance_metrics,
            'user_id': self.user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
