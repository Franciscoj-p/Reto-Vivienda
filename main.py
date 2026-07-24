"""
Punto de entrada de la API.

Ejecutar:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from app.api.routes import app

__all__ = ["app"]
