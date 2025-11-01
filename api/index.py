import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for production
os.environ.setdefault('FLASK_ENV', 'production')

from app import create_app

# Create the Flask application
app = create_app()

# Export the app for Vercel
# Vercel will automatically detect and use this Flask app
