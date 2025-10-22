"""
Base CRUD Controller for Gr8 Agent
Provides standardized CRUD operations for all entities
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """Types of CRUD operations"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"

@dataclass
class AuditLog:
    """Audit log entry"""
    id: str
    entity_type: str
    entity_id: str
    operation: OperationType
    user_id: Optional[str]
    timestamp: datetime
    old_data: Optional[Dict[str, Any]]
    new_data: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]

@dataclass
class ValidationError:
    """Validation error"""
    field: str
    message: str
    code: str

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]

@dataclass
class PaginationParams:
    """Pagination parameters"""
    page: int = 1
    per_page: int = 20
    max_per_page: int = 100

@dataclass
class PaginatedResult:
    """Paginated result"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

class BaseController(ABC):
    """Base CRUD controller with audit logging and validation"""

    def __init__(self, db_session, audit_logger=None):
        self.db = db_session
        self.audit_logger = audit_logger
        self.entity_name = self.__class__.__name__.replace('Controller', '').lower()

    @abstractmethod
    def _get_model_class(self):
        """Get the SQLAlchemy model class"""
        pass

    @abstractmethod
    def _validate_data(self, data: Dict[str, Any], operation: OperationType) -> ValidationResult:
        """Validate data for the given operation"""
        pass

    @abstractmethod
    def _serialize_entity(self, entity) -> Dict[str, Any]:
        """Serialize entity to dictionary"""
        pass

    def create(self, data: Dict[str, Any], user_id: Optional[str] = None,
               ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Create new entity"""
        try:
            # Validate data
            validation_result = self._validate_data(data, OperationType.CREATE)
            if not validation_result.is_valid:
                return {
                    'success': False,
                    'errors': [{'field': e.field, 'message': e.message, 'code': e.code}
                              for e in validation_result.errors]
                }

            # Add metadata
            data['id'] = data.get('id', str(uuid.uuid4()))
            data['created_at'] = datetime.now()
            data['updated_at'] = datetime.now()

            # Create entity
            model_class = self._get_model_class()
            entity = model_class(**data)

            self.db.add(entity)
            self.db.commit()

            # Log audit
            self._log_audit(OperationType.CREATE, entity.id, None, data,
                          user_id, ip_address, user_agent)

            logger.info(f"Created {self.entity_name} with ID: {entity.id}")

            return {
                'success': True,
                'data': self._serialize_entity(entity),
                'message': f'{self.entity_name.title()} created successfully'
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def read(self, entity_id: str, user_id: Optional[str] = None,
             ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Read entity by ID"""
        try:
            model_class = self._get_model_class()
            entity = self.db.query(model_class).filter_by(id=entity_id).first()

            if not entity:
                return {
                    'success': False,
                    'error': f'{self.entity_name.title()} not found'
                }

            # Log audit
            self._log_audit(OperationType.READ, entity_id, None, None,
                          user_id, ip_address, user_agent)

            return {
                'success': True,
                'data': self._serialize_entity(entity)
            }

        except Exception as e:
            logger.error(f"Error reading {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def update(self, entity_id: str, data: Dict[str, Any], user_id: Optional[str] = None,
               ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Update existing entity"""
        try:
            model_class = self._get_model_class()
            entity = self.db.query(model_class).filter_by(id=entity_id).first()

            if not entity:
                return {
                    'success': False,
                    'error': f'{self.entity_name.title()} not found'
                }

            # Store old data for audit
            old_data = self._serialize_entity(entity)

            # Validate data
            validation_result = self._validate_data(data, OperationType.UPDATE)
            if not validation_result.is_valid:
                return {
                    'success': False,
                    'errors': [{'field': e.field, 'message': e.message, 'code': e.code}
                              for e in validation_result.errors]
                }

            # Update entity
            data['updated_at'] = datetime.now()
            for key, value in data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            self.db.commit()

            # Log audit
            new_data = self._serialize_entity(entity)
            self._log_audit(OperationType.UPDATE, entity_id, old_data, new_data,
                          user_id, ip_address, user_agent)

            logger.info(f"Updated {self.entity_name} with ID: {entity_id}")

            return {
                'success': True,
                'data': new_data,
                'message': f'{self.entity_name.title()} updated successfully'
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def delete(self, entity_id: str, user_id: Optional[str] = None,
               ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Delete entity"""
        try:
            model_class = self._get_model_class()
            entity = self.db.query(model_class).filter_by(id=entity_id).first()

            if not entity:
                return {
                    'success': False,
                    'error': f'{self.entity_name.title()} not found'
                }

            # Store data for audit
            old_data = self._serialize_entity(entity)

            # Delete entity
            self.db.delete(entity)
            self.db.commit()

            # Log audit
            self._log_audit(OperationType.DELETE, entity_id, old_data, None,
                          user_id, ip_address, user_agent)

            logger.info(f"Deleted {self.entity_name} with ID: {entity_id}")

            return {
                'success': True,
                'message': f'{self.entity_name.title()} deleted successfully'
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def list(self, filters: Optional[Dict[str, Any]] = None,
             pagination: Optional[PaginationParams] = None,
             user_id: Optional[str] = None,
             ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """List entities with filtering and pagination"""
        try:
            model_class = self._get_model_class()
            query = self.db.query(model_class)

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Get total count
            total = query.count()

            # Apply pagination
            if pagination:
                offset = (pagination.page - 1) * pagination.per_page
                query = query.offset(offset).limit(pagination.per_page)

            # Execute query
            entities = query.all()

            # Serialize results
            data = [self._serialize_entity(entity) for entity in entities]

            # Calculate pagination info
            if pagination:
                total_pages = (total + pagination.per_page - 1) // pagination.per_page
                paginated_result = PaginatedResult(
                    data=data,
                    total=total,
                    page=pagination.page,
                    per_page=pagination.per_page,
                    total_pages=total_pages,
                    has_next=pagination.page < total_pages,
                    has_prev=pagination.page > 1
                )

                # Log audit
                self._log_audit(OperationType.LIST, None, None, {
                    'filters': filters,
                    'pagination': asdict(pagination)
                }, user_id, ip_address, user_agent)

                return {
                    'success': True,
                    'data': asdict(paginated_result)
                }
            else:
                return {
                    'success': True,
                    'data': data,
                    'total': total
                }

        except Exception as e:
            logger.error(f"Error listing {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query"""
        model_class = self._get_model_class()

        for field, value in filters.items():
            if hasattr(model_class, field):
                if isinstance(value, list):
                    query = query.filter(getattr(model_class, field).in_(value))
                elif isinstance(value, dict):
                    # Handle range filters
                    if 'gte' in value:
                        query = query.filter(getattr(model_class, field) >= value['gte'])
                    if 'lte' in value:
                        query = query.filter(getattr(model_class, field) <= value['lte'])
                    if 'gt' in value:
                        query = query.filter(getattr(model_class, field) > value['gt'])
                    if 'lt' in value:
                        query = query.filter(getattr(model_class, field) < value['lt'])
                else:
                    query = query.filter(getattr(model_class, field) == value)

        return query

    def _log_audit(self, operation: OperationType, entity_id: Optional[str],
                   old_data: Optional[Dict[str, Any]], new_data: Optional[Dict[str, Any]],
                   user_id: Optional[str], ip_address: Optional[str], user_agent: Optional[str]):
        """Log audit information"""
        if self.audit_logger:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                entity_type=self.entity_name,
                entity_id=entity_id or '',
                operation=operation,
                user_id=user_id,
                timestamp=datetime.now(),
                old_data=old_data,
                new_data=new_data,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.audit_logger.log(audit_log)

    def bulk_create(self, data_list: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Bulk create entities"""
        try:
            created_entities = []
            errors = []

            for i, data in enumerate(data_list):
                result = self.create(data, user_id)
                if result['success']:
                    created_entities.append(result['data'])
                else:
                    errors.append({
                        'index': i,
                        'data': data,
                        'errors': result.get('errors', [result.get('error', 'Unknown error')])
                    })

            return {
                'success': len(errors) == 0,
                'created_count': len(created_entities),
                'error_count': len(errors),
                'created_entities': created_entities,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error in bulk create for {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def bulk_update(self, updates: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Bulk update entities"""
        try:
            updated_entities = []
            errors = []

            for update in updates:
                entity_id = update.pop('id')
                result = self.update(entity_id, update, user_id)
                if result['success']:
                    updated_entities.append(result['data'])
                else:
                    errors.append({
                        'id': entity_id,
                        'errors': result.get('errors', [result.get('error', 'Unknown error')])
                    })

            return {
                'success': len(errors) == 0,
                'updated_count': len(updated_entities),
                'error_count': len(errors),
                'updated_entities': updated_entities,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error in bulk update for {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def bulk_delete(self, entity_ids: List[str], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Bulk delete entities"""
        try:
            deleted_count = 0
            errors = []

            for entity_id in entity_ids:
                result = self.delete(entity_id, user_id)
                if result['success']:
                    deleted_count += 1
                else:
                    errors.append({
                        'id': entity_id,
                        'error': result.get('error', 'Unknown error')
                    })

            return {
                'success': len(errors) == 0,
                'deleted_count': deleted_count,
                'error_count': len(errors),
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error in bulk delete for {self.entity_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
