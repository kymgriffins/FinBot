"""
Enhanced Trade Journal Controller for Gr8 Agent
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from decimal import Decimal
from ..controllers.base_controller import BaseController, ValidationResult, ValidationError, OperationType
from ..models.trade_journal import TradeJournal
from ..utils.calculations import calculate_pnl, calculate_risk_metrics

logger = logging.getLogger(__name__)

class TradeController(BaseController):
    """Enhanced trade journal controller with advanced features"""
    
    def __init__(self, db_session, audit_logger=None):
        super().__init__(db_session, audit_logger)
        self.entity_name = 'trade'
    
    def _get_model_class(self):
        return TradeJournal
    
    def _validate_data(self, data: Dict[str, Any], operation: OperationType) -> ValidationResult:
        """Validate trade data"""
        errors = []
        warnings = []
        
        # Required fields for create
        if operation == OperationType.CREATE:
            required_fields = ['symbol', 'trade_type', 'entry_price', 'position_size']
            for field in required_fields:
                if field not in data or data[field] is None:
                    errors.append(ValidationError(
                        field=field,
                        message=f"{field} is required",
                        code="REQUIRED_FIELD"
                    ))
        
        # Validate symbol
        if 'symbol' in data:
            symbol = data['symbol']
            if not isinstance(symbol, str) or len(symbol) < 1 or len(symbol) > 20:
                errors.append(ValidationError(
                    field='symbol',
                    message="Symbol must be a string between 1-20 characters",
                    code="INVALID_SYMBOL"
                ))
        
        # Validate trade type
        if 'trade_type' in data:
            trade_type = data['trade_type']
            if trade_type not in ['long', 'short']:
                errors.append(ValidationError(
                    field='trade_type',
                    message="Trade type must be 'long' or 'short'",
                    code="INVALID_TRADE_TYPE"
                ))
        
        # Validate prices
        for price_field in ['entry_price', 'exit_price']:
            if price_field in data and data[price_field] is not None:
                try:
                    price = float(data[price_field])
                    if price <= 0:
                        errors.append(ValidationError(
                            field=price_field,
                            message=f"{price_field} must be greater than 0",
                            code="INVALID_PRICE"
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field=price_field,
                        message=f"{price_field} must be a valid number",
                        code="INVALID_PRICE_FORMAT"
                    ))
        
        # Validate position size
        if 'position_size' in data:
            try:
                size = float(data['position_size'])
                if size <= 0:
                    errors.append(ValidationError(
                        field='position_size',
                        message="Position size must be greater than 0",
                        code="INVALID_POSITION_SIZE"
                    ))
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field='position_size',
                    message="Position size must be a valid number",
                    code="INVALID_POSITION_SIZE_FORMAT"
                ))
        
        # Validate dates
        for date_field in ['entry_time', 'exit_time']:
            if date_field in data and data[date_field] is not None:
                try:
                    if isinstance(data[date_field], str):
                        datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
                except ValueError:
                    errors.append(ValidationError(
                        field=date_field,
                        message=f"{date_field} must be a valid ISO datetime",
                        code="INVALID_DATETIME"
                    ))
        
        # Validate fees
        if 'fees' in data and data['fees'] is not None:
            try:
                fees = float(data['fees'])
                if fees < 0:
                    warnings.append("Fees should not be negative")
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field='fees',
                    message="Fees must be a valid number",
                    code="INVALID_FEES_FORMAT"
                ))
        
        # Business logic validations
        if operation == OperationType.CREATE or operation == OperationType.UPDATE:
            # Check if exit_time is after entry_time
            if 'entry_time' in data and 'exit_time' in data:
                if data['entry_time'] and data['exit_time']:
                    try:
                        entry_time = datetime.fromisoformat(data['entry_time'].replace('Z', '+00:00'))
                        exit_time = datetime.fromisoformat(data['exit_time'].replace('Z', '+00:00'))
                        if exit_time <= entry_time:
                            errors.append(ValidationError(
                                field='exit_time',
                                message="Exit time must be after entry time",
                                code="INVALID_TIME_ORDER"
                            ))
                    except (ValueError, TypeError):
                        pass  # Already handled above
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _serialize_entity(self, entity) -> Dict[str, Any]:
        """Serialize trade entity"""
        return {
            'id': entity.id,
            'symbol': entity.symbol,
            'trade_type': entity.trade_type,
            'entry_price': float(entity.entry_price) if entity.entry_price else None,
            'exit_price': float(entity.exit_price) if entity.exit_price else None,
            'position_size': float(entity.position_size) if entity.position_size else None,
            'entry_time': entity.entry_time.isoformat() if entity.entry_time else None,
            'exit_time': entity.exit_time.isoformat() if entity.exit_time else None,
            'pnl': float(entity.pnl) if entity.pnl else None,
            'fees': float(entity.fees) if entity.fees else None,
            'notes': entity.notes,
            'strategy_id': entity.strategy_id,
            'portfolio_id': entity.portfolio_id,
            'status': entity.status,
            'risk_metrics': entity.risk_metrics,
            'created_at': entity.created_at.isoformat() if entity.created_at else None,
            'updated_at': entity.updated_at.isoformat() if entity.updated_at else None
        }
    
    def create_trade(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new trade with automatic calculations"""
        try:
            # Set default values
            data.setdefault('status', 'open')
            data.setdefault('entry_time', datetime.now().isoformat())
            data.setdefault('fees', 0.0)
            
            # Create the trade
            result = self.create(data, user_id)
            
            if result['success']:
                # Calculate initial risk metrics
                trade_data = result['data']
                risk_metrics = self._calculate_risk_metrics(trade_data)
                
                # Update with risk metrics
                self.update(trade_data['id'], {'risk_metrics': risk_metrics}, user_id)
                trade_data['risk_metrics'] = risk_metrics
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close_trade(self, trade_id: str, exit_price: float, exit_time: Optional[datetime] = None,
                   fees: Optional[float] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Close an open trade"""
        try:
            # Get current trade
            trade_result = self.read(trade_id, user_id)
            if not trade_result['success']:
                return trade_result
            
            trade_data = trade_result['data']
            
            if trade_data['status'] != 'open':
                return {
                    'success': False,
                    'error': 'Trade is not open'
                }
            
            # Calculate P&L
            pnl = calculate_pnl(
                trade_type=trade_data['trade_type'],
                entry_price=trade_data['entry_price'],
                exit_price=exit_price,
                position_size=trade_data['position_size'],
                fees=fees or trade_data.get('fees', 0)
            )
            
            # Update trade
            update_data = {
                'exit_price': exit_price,
                'exit_time': (exit_time or datetime.now()).isoformat(),
                'pnl': pnl,
                'status': 'closed'
            }
            
            if fees is not None:
                update_data['fees'] = fees
            
            result = self.update(trade_id, update_data, user_id)
            
            if result['success']:
                # Recalculate risk metrics
                updated_trade = result['data']
                risk_metrics = self._calculate_risk_metrics(updated_trade)
                self.update(trade_id, {'risk_metrics': risk_metrics}, user_id)
                updated_trade['risk_metrics'] = risk_metrics
                result['data'] = updated_trade
            
            return result
            
        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_trade_statistics(self, filters: Optional[Dict[str, Any]] = None,
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive trade statistics"""
        try:
            # Get all trades
            trades_result = self.list(filters=filters, user_id=user_id)
            if not trades_result['success']:
                return trades_result
            
            trades = trades_result['data']
            
            if not trades:
                return {
                    'success': True,
                    'statistics': {
                        'total_trades': 0,
                        'open_trades': 0,
                        'closed_trades': 0,
                        'total_pnl': 0.0,
                        'win_rate': 0.0,
                        'profit_factor': 0.0,
                        'avg_win': 0.0,
                        'avg_loss': 0.0,
                        'max_drawdown': 0.0,
                        'sharpe_ratio': 0.0
                    }
                }
            
            # Calculate statistics
            closed_trades = [t for t in trades if t['status'] == 'closed' and t['pnl'] is not None]
            open_trades = [t for t in trades if t['status'] == 'open']
            
            total_trades = len(trades)
            closed_count = len(closed_trades)
            open_count = len(open_trades)
            
            if closed_count == 0:
                return {
                    'success': True,
                    'statistics': {
                        'total_trades': total_trades,
                        'open_trades': open_count,
                        'closed_trades': closed_count,
                        'total_pnl': 0.0,
                        'win_rate': 0.0,
                        'profit_factor': 0.0,
                        'avg_win': 0.0,
                        'avg_loss': 0.0,
                        'max_drawdown': 0.0,
                        'sharpe_ratio': 0.0
                    }
                }
            
            # Calculate P&L metrics
            pnls = [t['pnl'] for t in closed_trades]
            total_pnl = sum(pnls)
            
            winning_trades = [pnl for pnl in pnls if pnl > 0]
            losing_trades = [pnl for pnl in pnls if pnl < 0]
            
            win_rate = len(winning_trades) / closed_count if closed_count > 0 else 0
            
            avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
            
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum(losing_trades)) if losing_trades else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Calculate drawdown
            cumulative_pnl = []
            running_total = 0
            for pnl in pnls:
                running_total += pnl
                cumulative_pnl.append(running_total)
            
            peak = cumulative_pnl[0]
            max_drawdown = 0
            for value in cumulative_pnl:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Calculate Sharpe ratio (simplified)
            if len(pnls) > 1:
                mean_return = sum(pnls) / len(pnls)
                variance = sum((pnl - mean_return) ** 2 for pnl in pnls) / (len(pnls) - 1)
                std_dev = variance ** 0.5
                sharpe_ratio = mean_return / std_dev if std_dev > 0 else 0
            else:
                sharpe_ratio = 0
            
            return {
                'success': True,
                'statistics': {
                    'total_trades': total_trades,
                    'open_trades': open_count,
                    'closed_trades': closed_count,
                    'total_pnl': round(total_pnl, 2),
                    'win_rate': round(win_rate * 100, 2),
                    'profit_factor': round(profit_factor, 2),
                    'avg_win': round(avg_win, 2),
                    'avg_loss': round(avg_loss, 2),
                    'max_drawdown': round(max_drawdown, 2),
                    'sharpe_ratio': round(sharpe_ratio, 2),
                    'gross_profit': round(gross_profit, 2),
                    'gross_loss': round(gross_loss, 2),
                    'winning_trades': len(winning_trades),
                    'losing_trades': len(losing_trades)
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_trades_by_symbol(self, symbol: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all trades for a specific symbol"""
        return self.list(filters={'symbol': symbol}, user_id=user_id)
    
    def get_trades_by_date_range(self, start_date: datetime, end_date: datetime,
                               user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get trades within a date range"""
        filters = {
            'entry_time': {
                'gte': start_date.isoformat(),
                'lte': end_date.isoformat()
            }
        }
        return self.list(filters=filters, user_id=user_id)
    
    def get_open_trades(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all open trades"""
        return self.list(filters={'status': 'open'}, user_id=user_id)
    
    def _calculate_risk_metrics(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics for a trade"""
        try:
            if not trade_data.get('entry_price') or not trade_data.get('position_size'):
                return {}
            
            entry_price = float(trade_data['entry_price'])
            position_size = float(trade_data['position_size'])
            trade_type = trade_data['trade_type']
            
            # Calculate position value
            position_value = entry_price * position_size
            
            # Calculate risk per share (simplified)
            risk_per_share = entry_price * 0.02  # 2% risk assumption
            
            # Calculate stop loss levels (simplified)
            if trade_type == 'long':
                stop_loss = entry_price * 0.98  # 2% below entry
                take_profit = entry_price * 1.06  # 6% above entry
            else:
                stop_loss = entry_price * 1.02  # 2% above entry
                take_profit = entry_price * 0.94  # 6% below entry
            
            return {
                'position_value': round(position_value, 2),
                'risk_per_share': round(risk_per_share, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'risk_reward_ratio': 3.0,  # 1:3 risk-reward
                'position_size_pct': 0.0,  # Would need portfolio value
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
