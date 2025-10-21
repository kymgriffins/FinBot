import logging
import os
from flask import Flask


def create_app() -> Flask:
    """Application factory for FinBot."""
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'), static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Register blueprints
    from .routes.web import web_bp
    from .routes.api import api_bp
    from .routes.data import data_bp
    from .routes.telegram import telegram_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(data_bp, url_prefix='/data')
    app.register_blueprint(telegram_bp, url_prefix='/telegram')

    return app


