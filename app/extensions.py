"""Shared Flask extensions initialized here to avoid circular imports."""

from flask_sqlalchemy import SQLAlchemy

# Single SQLAlchemy instance bound to the Flask app inside create_app()
db = SQLAlchemy()
