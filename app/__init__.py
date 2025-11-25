"""
app/__init__.py
Flask application factory
"""

from flask import Flask
from flask_cors import CORS
import logging
import os


def create_app(config_name="production"):
    """Application factory pattern"""
    app = Flask(__name__)
    CORS(app)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Register blueprints
    from app.api.routes import api_bp
    from app.web.dashboard import web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    return app
