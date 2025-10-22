"""
Data Validation Routes for Gr8 Agent
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import logging
from ..adapters.yfinance_adapter import YFinanceAdapter
from ..adapters.alpha_vantage_adapter import AlphaVantageAdapter
from ..validators.multi_source_validator import MultiSourceValidator, ConsensusMethod

logger = logging.getLogger(__name__)

data_validation_bp = Blueprint('data_validation', __name__)

def get_multi_source_validator():
    """Get multi-source validator instance"""
    adapters = []
    
    # Add YFinance adapter
    adapters.append(YFinanceAdapter())
    
    # Add Alpha Vantage adapter if API key is available
    alpha_vantage_key = current_app.config.get('ALPHA_VANTAGE_API_KEY')
    if alpha_vantage_key:
        adapters.append(AlphaVantageAdapter(api_key=alpha_vantage_key))
    
    return MultiSourceValidator(adapters, ConsensusMethod.WEIGHTED_AVERAGE)

@data_validation_bp.route('/validate/<symbol>', methods=['GET'])
def validate_symbol_data(symbol):
    """Validate data for a specific symbol across multiple sources"""
    try:
        # Get query parameters
        days_back = int(request.args.get('days', 30))
        interval = request.args.get('interval', '1d')
        consensus_method = request.args.get('method', 'weighted_average')
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get validator
        validator = get_multi_source_validator()
        
        # Set consensus method
        if consensus_method == 'majority':
            validator.consensus_method = ConsensusMethod.MAJORITY
        elif consensus_method == 'highest_quality':
            validator.consensus_method = ConsensusMethod.HIGHEST_QUALITY
        elif consensus_method == 'median':
            validator.consensus_method = ConsensusMethod.MEDIAN
        else:
            validator.consensus_method = ConsensusMethod.WEIGHTED_AVERAGE
        
        # Get consensus data
        result = validator.get_consensus_data(symbol, start_date, end_date, interval)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'interval': interval,
            'consensus_method': consensus_method,
            'data_points': len(result.consensus_data),
            'confidence_score': result.confidence_score,
            'source_agreement': result.source_agreement,
            'anomalies': result.anomalies,
            'metadata': result.metadata,
            'sample_data': result.consensus_data.head(5).to_dict('records') if not result.consensus_data.empty else []
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating symbol data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_validation_bp.route('/sources', methods=['GET'])
def get_data_sources():
    """Get information about available data sources"""
    try:
        validator = get_multi_source_validator()
        
        sources = []
        for adapter in validator.adapters:
            source_info = adapter.source_info
            sources.append({
                'name': source_info.name,
                'reliability_score': source_info.reliability_score,
                'rate_limit': source_info.rate_limit,
                'cost_per_request': source_info.cost_per_request,
                'supported_intervals': source_info.supported_intervals,
                'data_delay': source_info.data_delay,
                'is_available': adapter.is_available(),
                'last_updated': source_info.last_updated.isoformat()
            })
        
        return jsonify({
            'success': True,
            'sources': sources,
            'total_sources': len(sources)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting data sources: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_validation_bp.route('/test/<symbol>', methods=['GET'])
def test_data_sources(symbol):
    """Test data sources for a specific symbol"""
    try:
        # Get query parameters
        days_back = int(request.args.get('days', 7))
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        validator = get_multi_source_validator()
        
        results = []
        for adapter in validator.adapters:
            try:
                # Test data fetch
                data = adapter.fetch_data(symbol, start_date, end_date)
                validation_result = adapter.validate_data(data)
                
                results.append({
                    'source': adapter.__class__.__name__,
                    'source_info': {
                        'name': adapter.source_info.name,
                        'reliability_score': adapter.source_info.reliability_score
                    },
                    'data_points': len(data),
                    'validation': {
                        'is_valid': validation_result.is_valid,
                        'quality_score': validation_result.quality_score,
                        'quality_level': validation_result.quality_level.value,
                        'errors': validation_result.errors,
                        'warnings': validation_result.warnings
                    },
                    'sample_data': data.head(3).to_dict('records') if not data.empty else [],
                    'is_available': adapter.is_available()
                })
                
            except Exception as e:
                results.append({
                    'source': adapter.__class__.__name__,
                    'error': str(e),
                    'is_available': False
                })
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error testing data sources: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_validation_bp.route('/consensus/<symbol>', methods=['GET'])
def get_consensus_data(symbol):
    """Get consensus data for a symbol"""
    try:
        # Get query parameters
        days_back = int(request.args.get('days', 30))
        interval = request.args.get('interval', '1d')
        include_raw_data = request.args.get('include_raw', 'false').lower() == 'true'
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        validator = get_multi_source_validator()
        result = validator.get_consensus_data(symbol, start_date, end_date, interval)
        
        response_data = {
            'success': True,
            'symbol': symbol,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'interval': interval,
            'consensus_data': result.consensus_data.to_dict('records') if not result.consensus_data.empty else [],
            'confidence_score': result.confidence_score,
            'source_agreement': result.source_agreement,
            'anomalies': result.anomalies,
            'metadata': result.metadata
        }
        
        if include_raw_data:
            # Include raw data from individual sources
            raw_data = {}
            for adapter in validator.adapters:
                try:
                    data = adapter.fetch_data(symbol, start_date, end_date, interval)
                    raw_data[adapter.__class__.__name__] = data.to_dict('records') if not data.empty else []
                except Exception as e:
                    raw_data[adapter.__class__.__name__] = {'error': str(e)}
            
            response_data['raw_data'] = raw_data
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting consensus data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_validation_bp.route('/anomalies/<symbol>', methods=['GET'])
def detect_anomalies(symbol):
    """Detect anomalies in data for a symbol"""
    try:
        # Get query parameters
        days_back = int(request.args.get('days', 30))
        interval = request.args.get('interval', '1d')
        threshold = float(request.args.get('threshold', 0.1))  # 10% deviation threshold
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        validator = get_multi_source_validator()
        validator.anomaly_threshold = threshold
        
        result = validator.get_consensus_data(symbol, start_date, end_date, interval)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'interval': interval,
            'anomaly_threshold': threshold,
            'anomalies': result.anomalies,
            'total_anomalies': len(result.anomalies),
            'confidence_score': result.confidence_score,
            'source_agreement': result.source_agreement
        }), 200
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_validation_bp.route('/quality/<symbol>', methods=['GET'])
def assess_data_quality(symbol):
    """Assess data quality for a symbol"""
    try:
        # Get query parameters
        days_back = int(request.args.get('days', 30))
        interval = request.args.get('interval', '1d')
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        validator = get_multi_source_validator()
        
        quality_assessments = []
        for adapter in validator.adapters:
            try:
                data = adapter.fetch_data(symbol, start_date, end_date, interval)
                validation_result = adapter.validate_data(data)
                
                quality_assessments.append({
                    'source': adapter.__class__.__name__,
                    'source_name': adapter.source_info.name,
                    'reliability_score': adapter.source_info.reliability_score,
                    'data_points': len(data),
                    'quality_score': validation_result.quality_score,
                    'quality_level': validation_result.quality_level.value,
                    'is_valid': validation_result.is_valid,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings,
                    'metadata': validation_result.metadata
                })
                
            except Exception as e:
                quality_assessments.append({
                    'source': adapter.__class__.__name__,
                    'error': str(e),
                    'quality_score': 0.0,
                    'quality_level': 'unknown',
                    'is_valid': False
                })
        
        # Calculate overall quality score
        valid_assessments = [a for a in quality_assessments if 'error' not in a]
        if valid_assessments:
            overall_quality = sum(a['quality_score'] for a in valid_assessments) / len(valid_assessments)
        else:
            overall_quality = 0.0
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'interval': interval,
            'overall_quality_score': round(overall_quality, 3),
            'quality_level': 'excellent' if overall_quality >= 0.9 else 'good' if overall_quality >= 0.7 else 'fair' if overall_quality >= 0.5 else 'poor',
            'assessments': quality_assessments,
            'total_sources': len(quality_assessments),
            'valid_sources': len(valid_assessments)
        }), 200
        
    except Exception as e:
        logger.error(f"Error assessing data quality: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@data_validation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for data validation system"""
    try:
        validator = get_multi_source_validator()
        
        # Test each adapter
        adapter_status = []
        for adapter in validator.adapters:
            try:
                is_available = adapter.is_available()
                adapter_status.append({
                    'name': adapter.__class__.__name__,
                    'source_name': adapter.source_info.name,
                    'is_available': is_available,
                    'reliability_score': adapter.source_info.reliability_score
                })
            except Exception as e:
                adapter_status.append({
                    'name': adapter.__class__.__name__,
                    'is_available': False,
                    'error': str(e)
                })
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'adapters': adapter_status,
            'total_adapters': len(adapter_status),
            'available_adapters': len([a for a in adapter_status if a.get('is_available', False)])
        }), 200
        
    except Exception as e:
        logger.error(f"Data validation health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
