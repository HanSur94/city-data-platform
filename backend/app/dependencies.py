"""Shared FastAPI dependencies.

Centralises get_current_town() so routers can import it without
creating a circular dependency through main.py.
"""
from app.config import Town

_current_town: Town | None = None


def set_current_town(town: Town) -> None:
    """Called once by main.py lifespan on startup."""
    global _current_town
    _current_town = town


def get_current_town() -> Town:
    """FastAPI dependency: returns the currently loaded town."""
    if _current_town is None:
        raise RuntimeError("Town not loaded — lifespan not started")
    return _current_town
