import os
import sys
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Import configuration
try:
    from config import config
except ImportError:
    # Fallback configuration if config.py doesn't exist
    config = {'default': type('Config', (), {
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key'),
        'DEBUG': os.environ.get('FLASK_ENV') == 'development',
        'CORS_ORIGINS': ['*']
    })()}

def setup_logging(environment: str = 'development'):
    """Setup logging configuration"""
    log_level = logging.DEBUG if environment == 'development' else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('finbot.log') if environment == 'production' else logging.NullHandler()
        ]
    )

    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def create_app(environment: str = None):
    """Enhanced application factory pattern"""
    # Determine environment
    env = environment or os.getenv('FLASK_ENV', 'development')

    # Setup logging
    setup_logging(env)
    logger = logging.getLogger(__name__)

    # Create Flask app
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Configure app
    config_name = env if env in config else 'default'
    app.config.from_object(config[config_name])

    # Additional configuration
    app.config.update({
        'JSON_SORT_KEYS': False,
        'JSONIFY_PRETTYPRINT_REGULAR': env == 'development'
    })

    # Enable CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    register_blueprints(app, logger)

    # Register middleware
    register_middleware(app)

    logger.info(f"🚀 FinBot v2.0.0 started in {env} mode")
    return app

def register_error_handlers(app):
    """Register error handlers"""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests, please try again later',
            'status_code': 429
        }), 429

def register_blueprints(app, logger):
    """Register all blueprints"""
    try:
        # Core web routes
        from src.routes.web import web_bp
        app.register_blueprint(web_bp)
        logger.info("[OK] Web routes registered")

        # API routes
        from src.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        logger.info("[OK] API routes registered")

        # Data routes
        from src.routes.data import data_bp
        app.register_blueprint(data_bp, url_prefix='/api/data')
        logger.info("[OK] Data routes registered")

        # Analysis routes
        from src.routes.weekly_analysis import weekly_analysis_bp
        app.register_blueprint(weekly_analysis_bp, url_prefix='/api/weekly-analysis')
        logger.info("[OK] Weekly analysis routes registered")

        from src.routes.ai_weekly import ai_weekly_bp
        app.register_blueprint(ai_weekly_bp, url_prefix='/ai-weekly')
        logger.info("[OK] AI weekly routes registered")

        # Data source routes
        from src.routes.yfinance_routes import yfinance_bp
        app.register_blueprint(yfinance_bp, url_prefix='/api/yfinance')
        logger.info("[OK] YFinance routes registered")

        from src.routes.fmp_routes import fmp_bp
        app.register_blueprint(fmp_bp, url_prefix='/api/fmp')
        logger.info("[OK] FMP routes registered")

        # Utility routes
        from src.routes.comparison_routes import comparison_bp
        app.register_blueprint(comparison_bp, url_prefix='/api/comparison')
        logger.info("✅ Comparison routes registered")

        from src.routes.daily import daily_bp
        app.register_blueprint(daily_bp, url_prefix='/api/daily')
        logger.info("✅ Daily analysis routes registered")

        # ========== ICT TRADING ROUTES ==========
        try:
            from src.routes.ict_routes import ict_trading_bp
            app.register_blueprint(ict_trading_bp, url_prefix='/api/ict')
            logger.info("✅ ICT Trading routes registered")
        except ImportError as e:
            logger.warning(f"⚠️ ICT Trading routes not available: {e}")

        # Optional routes (may not exist)
        try:
            from src.routes.telegram import telegram_bp
            app.register_blueprint(telegram_bp, url_prefix='/api/telegram')
            logger.info("✅ Telegram routes registered")
        except ImportError:
            logger.warning("⚠️ Telegram routes not available")

    except ImportError as e:
        logger.error(f"❌ Failed to import routes: {e}")
        raise

def register_middleware(app):
    """Register middleware functions"""

    @app.before_request
    def before_request():
        """Log request information"""
        if app.debug:
            logger = logging.getLogger(__name__)
            logger.debug(f"Request: {request.method} {request.path}")

    @app.after_request
    def after_request(response):
        """Add security headers"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)