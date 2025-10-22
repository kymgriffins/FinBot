from flask import Blueprint, jsonify
import logging

from src.services.provider_registry import AVAILABLE_PROVIDERS, get_adapter

logger = logging.getLogger(__name__)
providers_bp = Blueprint('providers', __name__)


@providers_bp.route('/')
def list_providers():
    return jsonify({
        'status': 'success',
        'providers': AVAILABLE_PROVIDERS
    })


@providers_bp.route('/status')
def providers_status():
    statuses = {}
    for p in AVAILABLE_PROVIDERS:
        try:
            adapter = get_adapter(p)
            statuses[p] = {
                'available': bool(adapter and adapter.is_available()),
                'name': getattr(adapter, 'name', p)
            }
        except Exception as e:
            logger.exception(f"Error checking provider {p}: {e}")
            statuses[p] = {'available': False, 'name': p}

    return jsonify({'status': 'success', 'providers': statuses})
