import os
import logging
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def create_app():
    """Application factory pattern"""
    # Absolute path to templates
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, 'templates')

    print(f"🔍 Looking for templates in: {template_path}")
    print(f"📁 Directory exists: {os.path.exists(template_path)}")

    if os.path.exists(template_path):
        templates = os.listdir(template_path)
        print(f"📄 Available templates: {templates}")
    else:
        print("❌ Templates directory not found!")
        # Create templates directory if it doesn't exist
        os.makedirs(template_path, exist_ok=True)
        print("✅ Created templates directory")

    app = Flask(__name__, template_folder=template_path)

    # Register blueprints
    from src.routes.web import web_bp
    from src.routes.api import api_bp
    from src.routes.data import data_bp
    from src.routes.telegram import telegram_bp
    from src.routes.daily import daily_bp
    from src.routes.fmp_routes import fmp_bp
    from src.routes.yfinance_routes import yfinance_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(telegram_bp, url_prefix='/api/telegram')
    app.register_blueprint(daily_bp, url_prefix='/api/daily')
    app.register_blueprint(fmp_bp, url_prefix='/api/fmp')
    app.register_blueprint(yfinance_bp, url_prefix='/api/yfinance')

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)