#!/usr/bin/env python3
"""
Production WSGI entry point for FinBot
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment variables for production
os.environ.setdefault('FLASK_ENV', 'production')

from app import create_app

# Create the Flask application
application = create_app()

# Create alias for Gunicorn compatibility
app = application

if __name__ == "__main__":
    # This is for development only
    application.run(host='0.0.0.0', port=5000, debug=False)