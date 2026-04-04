"""FastAPI application bootstrap for the web service layer."""

from .app import create_api_app

__all__ = ["create_api_app"]
