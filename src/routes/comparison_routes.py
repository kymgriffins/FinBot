from flask import Blueprint, jsonify, request, render_template
import logging

logger = logging.getLogger(__name__)
comparison_bp = Blueprint('comparison', __name__)

@comparison_bp.route('/')
def comparison_dashboard():
    """Data Comparison Dashboard"""
    return render_template('data_comparison.html')

@comparison_bp.route('/cache-info')
def get_cache_info():
    """Get cache statistics"""
    try:
        # This would normally read from your cache system
        # For now, return mock data
        return jsonify({
            "status": "success",
            "cache_info": {
                "total_items": 0,
                "total_size_kb": 0,
                "oldest_item": None,
                "newest_item": None
            }
        })
    except Exception as e:
        logger.error(f"Cache info error: {e}")
        return jsonify({"error": "Failed to get cache info"}), 500

@comparison_bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all cached data"""
    try:
        # This would clear your cache storage
        # For now, return success
        return jsonify({
            "status": "success",
            "message": "Cache cleared successfully"
        })
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        return jsonify({"error": "Failed to clear cache"}), 500