"""
TicketWar API – Auth Routes

POST /api/v1/auth/register
POST /api/v1/auth/login
"""

import bcrypt
from flask import Blueprint, request, jsonify

from app.extensions import get_db_connection, release_db
from app.auth import encode_token

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


# ------------------------------------------------------------------
#  POST /api/v1/auth/register
# ------------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account.

    Body JSON:
        username  (str, required)
        email     (str, required)
        password  (str, required)
        role      (str, optional – default "customer")
    """
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    role     = data.get("role", "customer").strip()

    # --- validation ---
    if not username or not email or not password:
        return jsonify({"error": "username, email, dan password wajib diisi"}), 400

    if role not in ("customer", "eo", "admin"):
        return jsonify({"error": "Role tidak valid"}), 400

    # --- hash password ---
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()

        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, email, role, created_at
            """,
            (username, email, password_hash, role),
        )
        row = cur.fetchone()
        conn.commit()

        return jsonify({
            "message": "Registrasi berhasil",
            "user": {
                "id":         row[0],
                "username":   row[1],
                "email":      row[2],
                "role":       row[3],
                "created_at": row[4].isoformat(),
            },
        }), 201

    except Exception as exc:
        if conn:
            conn.rollback()

        # Duplicate key (unique violation) → 23505
        err_code = getattr(exc, "pgcode", None)
        if err_code == "23505":
            return jsonify({"error": "Username atau email sudah terdaftar"}), 409

        return jsonify({"error": str(exc)}), 500

    finally:
        release_db(conn)


# ------------------------------------------------------------------
#  POST /api/v1/auth/login
# ------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT.

    Body JSON:
        username  (str, required)
        password  (str, required)
    """
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username dan password wajib diisi"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()

        cur.execute(
            "SELECT id, username, email, password_hash, role, is_active FROM users WHERE username = %s",
            (username,),
        )
        row = cur.fetchone()

        if row is None:
            return jsonify({"error": "Username atau password salah"}), 401

        user_id, db_username, email, password_hash, role, is_active = row

        if not is_active:
            return jsonify({"error": "Akun dinonaktifkan"}), 403

        if not bcrypt.checkpw(password.encode(), password_hash.encode()):
            return jsonify({"error": "Username atau password salah"}), 401

        token = encode_token(user_id, db_username, role)

        return jsonify({
            "message": "Login berhasil",
            "token":   token,
            "user": {
                "id":       user_id,
                "username": db_username,
                "email":    email,
                "role":     role,
            },
        }), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    finally:
        release_db(conn)
