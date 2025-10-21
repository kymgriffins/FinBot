import os
from flask import Flask
from dotenv import load_dotenv

# Defer all implementation to the application factory in src

load_dotenv()

def create_app():
    from src import create_app as _create_app
    return _create_app()

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)