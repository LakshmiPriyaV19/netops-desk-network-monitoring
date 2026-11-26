"""Web routes serving the NetOps Desk HTML dashboard."""

from flask import Blueprint, render_template

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def dashboard():
    """Render the single-page responsive NetOps Desk operations dashboard."""
    return render_template("index.html")
