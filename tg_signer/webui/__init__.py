"""Web UI for tg-signer."""

from .app import create_app
from .settings import WebUISettings

__all__ = ["create_app", "WebUISettings"]
