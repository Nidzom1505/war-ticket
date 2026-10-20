"""
TicketWar API – Route blueprints (barrel file).

Registers every blueprint on the Flask app instance.
"""

from flask import Flask


def register_routes(app: Flask) -> None:
    from app.routes.auth_routes    import auth_bp
    from app.routes.concert_routes import concert_bp
    from app.routes.order_routes   import order_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(concert_bp)
    app.register_blueprint(order_bp)
