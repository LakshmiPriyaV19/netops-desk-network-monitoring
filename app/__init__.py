"""Flask Application Factory for NetOps Desk."""

import os
import click
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from app.config import CONFIG_BY_NAME
from app.extensions import db


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application instance.

    Args:
        config_name: Environment key ('development', 'testing', 'production').
                     Defaults to FLASK_ENV or 'development'.
    """
    app = Flask(__name__)

    env_name = config_name or os.getenv("FLASK_ENV", "development")
    config_cls = CONFIG_BY_NAME.get(env_name, CONFIG_BY_NAME["development"])
    app.config.from_object(config_cls)

    # Initialize SQLAlchemy with this application
    db.init_app(app)

    # Import models so SQLAlchemy metadata registers all tables
    from app import models  # noqa: F401

    # Register web and REST API blueprints
    from app.routes.web import web_bp
    from app.routes.api_devices import devices_bp
    from app.routes.api_incidents import incidents_bp
    from app.routes.api_dashboard import dashboard_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(dashboard_bp)

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "status": "ok",
            "service": "NetOps Desk",
            "environment": env_name,
        }), 200

    # Consistent JSON error responses for API routes
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        if request.path.startswith("/api/"):
            return jsonify({
                "error": exc.name,
                "message": exc.description,
                "status_code": exc.code,
            }), exc.code
        return exc

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables from SQLAlchemy models."""
        db.create_all()
        click.echo("Database tables initialized successfully.")

    @app.cli.command("seed-db")
    def seed_db_command():
        """Populate sample network devices and incidents."""
        from app.services.seeder import seed_demo_data

        db.create_all()
        res = seed_demo_data()
        click.echo(
            f"Seeded {res['devices_created']} devices and {res['incidents_created']} incidents."
        )

    # Start periodic simulated monitoring thread when enabled
    from app.services.monitoring import start_monitoring_scheduler

    start_monitoring_scheduler(app)

    return app
