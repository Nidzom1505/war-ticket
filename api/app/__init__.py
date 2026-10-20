"""
TicketWar API – Flask Application Factory.
"""

from flask import Flask
from flask_cors import CORS

from app.extensions import init_extensions, close_extensions
from app.routes import register_routes


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config.from_mapping(
        JSON_SORT_KEYS=False,
    )

    # CORS – allow frontend origin through Nginx
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialise DB pool + Redis client
    init_extensions()

    # Register all route blueprints
    register_routes(app)

    # Health check
    @app.route("/api/health")
    def health():
        return {"status": "ok"}, 200

    # Graceful shutdown
    @app.teardown_appcontext
    def _teardown(exc):
        pass  # pool connections returned per-request in routes

    return app
