# Vercel entrypoint: the Python runtime serves the ASGI `app` exported here.
from app.main import app

__all__ = ["app"]
