"""
Audit Log Model for Gr8 Agent
"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class OperationType(enum.Enum):
    """Operation type enumeration"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"

class AuditLog(Base):
    """Audit Log model"""
    __tablename__ = 'audit_logs'
    
    # Primary key
    id = Column(String(50), primary_key=True)
    
    # Audit details
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(50), nullable=False, index=True)
    operation = Column(Enum(OperationType), nullable=False)
    
    # User information
    user_id = Column(String(50), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Data changes
    old_data = Column(JSON, nullable=True)
    new_data = Column(JSON, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id='{self.id}', entity='{self.entity_type}', operation='{self.operation}', timestamp='{self.timestamp}')>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'operation': self.operation.value if self.operation else None,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'old_data': self.old_data,
            'new_data': self.new_data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
