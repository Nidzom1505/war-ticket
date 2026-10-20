"""
TicketWar API – JWT authentication helpers.

Provides:
    encode_token(payload) – create a signed JWT string
    decode_token(token)   – verify & return claims dict
    jwt_required(f)       – decorator that injects `current_user` into kwargs
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify

from app.config import Config


# ---------------------------------------------------------------------------
#  Token encode / decode
# ---------------------------------------------------------------------------

def encode_token(user_id: int, username: str, role: str) -> str:
    """Create a JWT with standard claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id":  user_id,
        "username": username,
        "role":     role,
        "iat":      now,
        "exp":      now + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.  Raises jwt.* exceptions on failure."""
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
#  Flask decorator
# ---------------------------------------------------------------------------

def jwt_required(f=None, *, roles: list[str] | None = None):
    """
    Decorator that enforces a valid JWT in the Authorization header.

    Usage:
        @jwt_required                           # any authenticated user
        @jwt_required(roles=["customer"])        # only customers
        @jwt_required(roles=["eo", "admin"])     # EO or admin
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Token tidak ditemukan"}), 401

            token = auth_header.split(" ", 1)[1]

            try:
                claims = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token sudah kedaluwarsa"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Token tidak valid"}), 401

            # Optional role check
            if roles and claims.get("role") not in roles:
                return jsonify({"error": "Akses ditolak"}), 403

            kwargs["current_user"] = claims
            return fn(*args, **kwargs)
        return wrapper

    # Support both @jwt_required and @jwt_required(roles=[...])
    if f is not None:
        return decorator(f)
    return decorator
