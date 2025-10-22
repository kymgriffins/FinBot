"""
Trade Journal Model for Gr8 Agent
"""

from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class TradeStatus(enum.Enum):
    """Trade status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class TradeType(enum.Enum):
    """Trade type enumeration"""
    LONG = "long"
    SHORT = "short"

class TradeJournal(Base):
    """Trade Journal model"""
    __tablename__ = 'trade_journal'
    
    # Primary key
    id = Column(String(50), primary_key=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    trade_type = Column(Enum(TradeType), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    position_size = Column(Float, nullable=False)
    
    # Timing
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_time = Column(DateTime, nullable=True)
    
    # Financial metrics
    pnl = Column(Float, nullable=True)
    fees = Column(Float, default=0.0)
    
    # Additional information
    notes = Column(Text, nullable=True)
    strategy_id = Column(String(50), nullable=True, index=True)
    portfolio_id = Column(String(50), nullable=True, index=True)
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN)
    
    # Risk metrics (stored as JSON)
    risk_metrics = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradeJournal(id='{self.id}', symbol='{self.symbol}', type='{self.trade_type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'trade_type': self.trade_type.value if self.trade_type else None,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'position_size': self.position_size,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl': self.pnl,
            'fees': self.fees,
            'notes': self.notes,
            'strategy_id': self.strategy_id,
            'portfolio_id': self.portfolio_id,
            'status': self.status.value if self.status else None,
            'risk_metrics': self.risk_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
