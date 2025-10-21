from flask import Blueprint, render_template, request, jsonify
import os
import logging

web_bp = Blueprint('web', __name__)
logger = logging.getLogger(__name__)

@web_bp.route('/')
def dashboard():
    """Main dashboard with overview of all features"""
    symbols = os.getenv('SYMBOLS', 'SPY,QQQ,AAPL,MSFT,TSLA').split(',')
    return render_template('dashboard.html', symbols=symbols)

@web_bp.route('/docs')
@web_bp.route('/documentation')
def api_docs():
    """Comprehensive API documentation"""
    return render_template('docs.html')

@web_bp.route('/weekly-analysis')
def weekly_analysis():
    """Traditional weekly analysis dashboard"""
    symbols = os.getenv('SYMBOLS', 'SPY,QQQ,AAPL,MSFT,TSLA').split(',')
    return render_template('weekly_analysis.html', symbols=symbols)

@web_bp.route('/ai-weekly')
def ai_weekly():
    """AI-powered weekly analysis dashboard"""
    symbols = os.getenv('SYMBOLS', 'SPY,QQQ,AAPL,MSFT,TSLA').split(',')
    return render_template('ai_weekly_dashboard.html', symbols=symbols)

@web_bp.route('/health')
def health_check():
    """Application health check"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'features': [
            'AI Weekly Analysis',
            'Traditional Weekly Analysis',
            'YFinance Integration',
            'FMP Integration',
            'Data Comparison',
            'Real-time Analytics'
        ],
        'endpoints': {
            'dashboard': '/',
            'ai_weekly': '/ai-weekly',
            'weekly_analysis': '/weekly-analysis',
            'docs': '/docs',
            'health': '/health'
        }
    })

@web_bp.route('/status')
def system_status():
    """Detailed system status"""
    try:
        # Check if all required modules are available
        import pandas as pd
        import numpy as np
        import yfinance as yf

        return jsonify({
            'status': 'operational',
            'components': {
                'pandas': '✅ Available',
                'numpy': '✅ Available',
                'yfinance': '✅ Available',
                'flask': '✅ Available'
            },
            'environment': {
                'python_version': os.sys.version,
                'working_directory': os.getcwd()
            }
        })
    except ImportError as e:
        return jsonify({
            'status': 'degraded',
            'error': f'Missing dependency: {str(e)}'
        }), 500