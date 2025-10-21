from flask import Blueprint, jsonify
from datetime import datetime

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })


