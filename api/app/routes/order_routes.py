"""
TicketWar API – Order Routes (War Tiket)

POST /api/v1/orders/reserve                – fast ingestion (JWT customer)
GET  /api/v1/orders/status/<invoice>       – polling order status
"""

import json
import time
import random
import string

from flask import Blueprint, request, jsonify

from app.auth       import jwt_required
from app.extensions import get_db_connection, release_db, redis_client

order_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


# ------------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------------

def _generate_invoice() -> str:
    """Generate a unique invoice number:  INV-<epoch_ms>-<random4>"""
    ts   = int(time.time() * 1000)
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"INV-{ts}-{rand}"


# ------------------------------------------------------------------
#  POST /api/v1/orders/reserve
# ------------------------------------------------------------------
@order_bp.route("/reserve", methods=["POST"])
@jwt_required(roles=["customer"])
def reserve_ticket(*, current_user: dict):
    """Fast-ingestion endpoint for the ticket war.

    Body JSON:
        category_id  (int, required)
        quantity     (int, optional – default 1)

    Flow:
        1. DECRBY quota:{category_id} by `quantity` in Redis.
        2. If the resulting value < 0 → rollback (INCRBY) and return 400.
        3. Otherwise generate an invoice, push to `order_queue`, return 202.
    """
    data = request.get_json(silent=True) or {}

    category_id = data.get("category_id")
    quantity    = data.get("quantity", 1)

    # --- validation ---
    if category_id is None:
        return jsonify({"error": "category_id wajib diisi"}), 400

    try:
        category_id = int(category_id)
        quantity    = int(quantity)
    except (TypeError, ValueError):
        return jsonify({"error": "category_id dan quantity harus berupa angka"}), 400

    if quantity < 1:
        return jsonify({"error": "quantity minimal 1"}), 400

    quota_key = f"quota:{category_id}"

    # --- check quota key exists ---
    if not redis_client.exists(quota_key):
        return jsonify({"error": "Kategori tiket tidak ditemukan"}), 404

    # --- atomic decrement ---
    remaining = redis_client.decrby(quota_key, quantity)

    if remaining < 0:
        # Rollback – add the quantity back
        redis_client.incrby(quota_key, quantity)
        return jsonify({"error": "Tiket habis (sold out)"}), 400

    # --- enqueue order ---
    invoice_number = _generate_invoice()

    order_payload = {
        "invoice_number": invoice_number,
        "user_id":        current_user["user_id"],
        "username":       current_user["username"],
        "category_id":    category_id,
        "quantity":       quantity,
        "ip_address":     request.remote_addr,
    }

    # Mark temporary status in Redis so polling can return immediately
    redis_client.set(
        f"order_status:{invoice_number}",
        "queued",
        ex=600,   # TTL 10 minutes
    )

    # Push to FIFO queue (RPUSH = tail; worker does BLPOP = head)
    redis_client.rpush("order_queue", json.dumps(order_payload))

    return jsonify({
        "message":        "Pesanan diterima, sedang diproses",
        "invoice_number": invoice_number,
        "quantity":       quantity,
    }), 202


# ------------------------------------------------------------------
#  GET /api/v1/orders/status/<invoice_number>
# ------------------------------------------------------------------
@order_bp.route("/status/<invoice_number>", methods=["GET"])
@jwt_required
def order_status(invoice_number: str, *, current_user: dict):
    """Poll the processing status of an order.

    Resolution order:
        1. Check PostgreSQL `orders` table first (definitive source).
        2. Fall back to Redis temporary key `order_status:{invoice}`.
        3. If neither exists → 404.
    """
    # --- 1. check DB ---
    conn = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()

        cur.execute(
            """
            SELECT o.id, o.invoice_number, o.quantity,
                   o.total_amount, o.payment_status, o.created_at,
                   tc.category_name, tc.price
              FROM orders o
              JOIN ticket_categories tc ON tc.id = o.category_id
             WHERE o.invoice_number = %s
               AND (o.user_id = %s OR %s IN ('admin', 'eo'))
            """,
            (invoice_number, current_user["user_id"], current_user.get("role")),
        )
        row = cur.fetchone()

        if row:
            # Fetch associated tickets if order is paid
            tickets = []
            if row[4] == "paid":
                cur.execute(
                    """
                    SELECT seat_number, ticket_code, is_used
                      FROM tickets
                     WHERE order_id = %s AND is_deleted = FALSE
                     ORDER BY id
                    """,
                    (row[0],),
                )
                tickets = [
                    {"seat_number": t[0], "ticket_code": t[1], "is_used": t[2]}
                    for t in cur.fetchall()
                ]

            return jsonify({
                "invoice_number": row[1],
                "quantity":       row[2],
                "total_amount":   float(row[3]),
                "payment_status": row[4],
                "created_at":     row[5].isoformat(),
                "category_name":  row[6],
                "price":          float(row[7]),
                "tickets":        tickets,
            }), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        release_db(conn)

    # --- 2. check Redis temporary status ---
    redis_status = redis_client.get(f"order_status:{invoice_number}")
    if redis_status:
        return jsonify({
            "invoice_number": invoice_number,
            "payment_status": redis_status,      # "queued" or "processing"
        }), 200

    # --- 3. not found ---
    return jsonify({"error": "Invoice tidak ditemukan"}), 404
