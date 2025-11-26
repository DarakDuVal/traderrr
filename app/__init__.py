"""
app/__init__.py
Flask application factory with Flasgger OpenAPI support
"""

from flask import Flask
from flask_cors import CORS
from flasgger import Flasgger
import logging
import os


def create_app(config_name="production"):
    """
    Application factory pattern

    Creates and configures Flask app with:
    - CORS support
    - Flasgger for OpenAPI 3.0/Swagger
    - JWT authentication
    - API blueprints for routes
    """
    app = Flask(__name__)

    # Enable CORS for all API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Configure Flask
    app.config["JSON_SORT_KEYS"] = False

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Initialize JWT authentication
    from app.api.auth import init_jwt

    init_jwt(app)

    # Initialize Flasgger for OpenAPI documentation and Swagger UI
    flasgger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs",
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs",
        "info": {
            "title": "Traderrr Trading System API",
            "version": "1.0.0",
            "description": (
                "Professional algorithmic trading system with automated signal generation, "
                "portfolio optimization, and risk management. "
                "All endpoints require API key authentication."
            ),
            "contact": {"email": "support@traderrr.com"},
        },
        "schemes": ["http", "https"],
    }

    flasgger = Flasgger(app, config=swagger_config)

    # Register API blueprint with routes
    from app.api.routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # Register web blueprints (non-API routes)
    try:
        from app.web.dashboard import web_bp

        app.register_blueprint(web_bp)
    except ImportError:
        app.logger.warning("Web dashboard not available")

    return app
