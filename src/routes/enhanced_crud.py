"""
Enhanced CRUD Routes for Gr8 Agent
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import logging
from ..controllers.trade_controller import TradeController
from ..utils.csv_importer import CSVImporter
from ..adapters.yfinance_adapter import YFinanceAdapter
from ..adapters.alpha_vantage_adapter import AlphaVantageAdapter
from ..validators.multi_source_validator import MultiSourceValidator, ConsensusMethod

logger = logging.getLogger(__name__)

enhanced_crud_bp = Blueprint('enhanced_crud', __name__)

# Initialize controllers and services
def get_trade_controller():
    """Get trade controller instance"""
    from ..database import get_db_session
    db_session = get_db_session()
    return TradeController(db_session)

def get_csv_importer():
    """Get CSV importer instance"""
    return CSVImporter()

def get_multi_source_validator():
    """Get multi-source validator instance"""
    adapters = [
        YFinanceAdapter(),
        AlphaVantageAdapter(api_key=current_app.config.get('ALPHA_VANTAGE_API_KEY'))
    ]
    return MultiSourceValidator(adapters, ConsensusMethod.WEIGHTED_AVERAGE)

# ========== TRADE JOURNAL ROUTES ==========

@enhanced_crud_bp.route('/trades', methods=['POST'])
def create_trade():
    """Create a new trade with enhanced validation"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID')
        
        trade_controller = get_trade_controller()
        result = trade_controller.create_trade(data, user_id)
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/<trade_id>', methods=['GET'])
def get_trade(trade_id):
    """Get trade by ID"""
    try:
        user_id = request.headers.get('X-User-ID')
        trade_controller = get_trade_controller()
        result = trade_controller.read(trade_id, user_id)
        
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        logger.error(f"Error getting trade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/<trade_id>', methods=['PUT'])
def update_trade(trade_id):
    """Update trade"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID')
        
        trade_controller = get_trade_controller()
        result = trade_controller.update(trade_id, data, user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error updating trade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/<trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    """Delete trade"""
    try:
        user_id = request.headers.get('X-User-ID')
        trade_controller = get_trade_controller()
        result = trade_controller.delete(trade_id, user_id)
        
        return jsonify(result), 200 if result['success'] else 404
        
    except Exception as e:
        logger.error(f"Error deleting trade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades', methods=['GET'])
def list_trades():
    """List trades with filtering and pagination"""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Build filters
        filters = {}
        if request.args.get('symbol'):
            filters['symbol'] = request.args.get('symbol')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('trade_type'):
            filters['trade_type'] = request.args.get('trade_type')
        if request.args.get('start_date'):
            filters['entry_time'] = {'gte': request.args.get('start_date')}
        if request.args.get('end_date'):
            if 'entry_time' not in filters:
                filters['entry_time'] = {}
            filters['entry_time']['lte'] = request.args.get('end_date')
        
        user_id = request.headers.get('X-User-ID')
        trade_controller = get_trade_controller()
        
        from ..controllers.base_controller import PaginationParams
        pagination = PaginationParams(page=page, per_page=per_page)
        
        result = trade_controller.list(filters=filters, pagination=pagination, user_id=user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error listing trades: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/<trade_id>/close', methods=['POST'])
def close_trade(trade_id):
    """Close an open trade"""
    try:
        data = request.get_json()
        user_id = request.headers.get('X-User-ID')
        
        exit_price = data.get('exit_price')
        exit_time = data.get('exit_time')
        fees = data.get('fees')
        
        if not exit_price:
            return jsonify({
                'success': False,
                'error': 'exit_price is required'
            }), 400
        
        trade_controller = get_trade_controller()
        result = trade_controller.close_trade(trade_id, exit_price, exit_time, fees, user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/statistics', methods=['GET'])
def get_trade_statistics():
    """Get comprehensive trade statistics"""
    try:
        # Build filters
        filters = {}
        if request.args.get('symbol'):
            filters['symbol'] = request.args.get('symbol')
        if request.args.get('start_date'):
            filters['entry_time'] = {'gte': request.args.get('start_date')}
        if request.args.get('end_date'):
            if 'entry_time' not in filters:
                filters['entry_time'] = {}
            filters['entry_time']['lte'] = request.args.get('end_date')
        
        user_id = request.headers.get('X-User-ID')
        trade_controller = get_trade_controller()
        result = trade_controller.get_trade_statistics(filters, user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error getting trade statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== CSV IMPORT ROUTES ==========

@enhanced_crud_bp.route('/import/csv', methods=['POST'])
def import_csv():
    """Import trades from CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Save file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            file.save(tmp_file.name)
            
            try:
                csv_importer = get_csv_importer()
                user_id = request.headers.get('X-User-ID')
                
                result = csv_importer.import_trades(tmp_file.name, user_id)
                
                if result['success'] and result['imported_count'] > 0:
                    # Bulk create trades
                    trade_controller = get_trade_controller()
                    bulk_result = trade_controller.bulk_create(result['trades'], user_id)
                    
                    result['bulk_create_result'] = bulk_result
                
                return jsonify(result), 200 if result['success'] else 400
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_file.name)
        
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/import/csv/validate', methods=['POST'])
def validate_csv():
    """Validate CSV file structure"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Save file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
            file.save(tmp_file.name)
            
            try:
                csv_importer = get_csv_importer()
                result = csv_importer.validate_csv_structure(tmp_file.name)
                
                return jsonify(result), 200
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_file.name)
        
    except Exception as e:
        logger.error(f"Error validating CSV: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/import/csv/sample', methods=['GET'])
def get_sample_csv():
    """Get sample CSV template"""
    try:
        csv_importer = get_csv_importer()
        sample_csv = csv_importer.get_sample_csv()
        
        return sample_csv, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=sample_trades.csv'
        }
        
    except Exception as e:
        logger.error(f"Error getting sample CSV: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== BULK OPERATIONS ==========

@enhanced_crud_bp.route('/trades/bulk', methods=['POST'])
def bulk_create_trades():
    """Bulk create trades"""
    try:
        data = request.get_json()
        trades = data.get('trades', [])
        user_id = request.headers.get('X-User-ID')
        
        if not trades:
            return jsonify({
                'success': False,
                'error': 'No trades provided'
            }), 400
        
        trade_controller = get_trade_controller()
        result = trade_controller.bulk_create(trades, user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error in bulk create: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/bulk', methods=['PUT'])
def bulk_update_trades():
    """Bulk update trades"""
    try:
        data = request.get_json()
        updates = data.get('updates', [])
        user_id = request.headers.get('X-User-ID')
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No updates provided'
            }), 400
        
        trade_controller = get_trade_controller()
        result = trade_controller.bulk_update(updates, user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_crud_bp.route('/trades/bulk', methods=['DELETE'])
def bulk_delete_trades():
    """Bulk delete trades"""
    try:
        data = request.get_json()
        trade_ids = data.get('trade_ids', [])
        user_id = request.headers.get('X-User-ID')
        
        if not trade_ids:
            return jsonify({
                'success': False,
                'error': 'No trade IDs provided'
            }), 400
        
        trade_controller = get_trade_controller()
        result = trade_controller.bulk_delete(trade_ids, user_id)
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== HEALTH CHECK ==========

@enhanced_crud_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for enhanced CRUD system"""
    try:
        # Test database connection
        trade_controller = get_trade_controller()
        
        # Test CSV importer
        csv_importer = get_csv_importer()
        
        # Test multi-source validator
        validator = get_multi_source_validator()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'trade_controller': 'ok',
                'csv_importer': 'ok',
                'multi_source_validator': 'ok'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
