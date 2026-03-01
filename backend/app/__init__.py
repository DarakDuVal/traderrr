"""
app/__init__.py
FastAPI application factory
"""

from app.main import create_app, app

__all__ = ["create_app", "app"]
