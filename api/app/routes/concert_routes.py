"""
TicketWar API – Concert Routes

GET /api/v1/concerts          – list concerts + ticket categories
                                (initialises Redis quota on first hit)
"""

from flask import Blueprint, jsonify

from app.extensions import get_db_connection, release_db, redis_client

concert_bp = Blueprint("concerts", __name__, url_prefix="/api/v1/concerts")


def _sync_quota_to_redis(categories: list[dict]) -> None:
    """Populate Redis quota keys for every category that isn't cached yet.

    Key pattern:  quota:{category_id}
    Value:        available_quota (integer)
    """
    for cat in categories:
        key = f"quota:{cat['id']}"
        # SETNX → only write if the key does NOT exist yet
        if not redis_client.exists(key):
            redis_client.set(key, cat["available_quota"])


@concert_bp.route("", methods=["GET"])
@concert_bp.route("/", methods=["GET"])
def list_concerts():
    """Return all published concerts with their ticket categories.

    On the **first call** after Redis is empty, each category's
    `available_quota` is seeded into Redis key `quota:{category_id}`
    so that the war-ticket ingestion flow can use atomic DECRBY.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor()

        # -- concerts --
        cur.execute(
            """
            SELECT id, organizer_id, title, artist, venue,
                   concert_date, status
              FROM concerts
             WHERE status = 'published'
             ORDER BY concert_date
            """
        )
        concert_rows = cur.fetchall()

        if not concert_rows:
            return jsonify({"concerts": []}), 200

        concert_ids = [r[0] for r in concert_rows]

        # -- categories for those concerts --
        cur.execute(
            """
            SELECT id, concert_id, category_name, price,
                   total_quota, available_quota
              FROM ticket_categories
             WHERE concert_id = ANY(%s)
             ORDER BY concert_id, id
            """,
            (concert_ids,),
        )
        cat_rows = cur.fetchall()

        # Build a lookup: concert_id → [category_dict, …]
        cat_map: dict[int, list[dict]] = {}
        all_categories: list[dict] = []
        for r in cat_rows:
            cat = {
                "id":              r[0],
                "concert_id":     r[1],
                "category_name":  r[2],
                "price":          float(r[3]),
                "total_quota":    r[4],
                "available_quota": r[5],
            }
            cat_map.setdefault(r[1], []).append(cat)
            all_categories.append(cat)

        # Sync quota to Redis (idempotent – SETNX)
        _sync_quota_to_redis(all_categories)

        # Enrich each category with live Redis quota
        for cat in all_categories:
            live = redis_client.get(f"quota:{cat['id']}")
            if live is not None:
                cat["available_quota"] = int(live)

        # Assemble response
        concerts = []
        for r in concert_rows:
            concerts.append({
                "id":            r[0],
                "organizer_id":  r[1],
                "title":         r[2],
                "artist":        r[3],
                "venue":         r[4],
                "concert_date":  r[5].isoformat(),
                "status":        r[6],
                "categories":    cat_map.get(r[0], []),
            })

        return jsonify({"concerts": concerts}), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    finally:
        release_db(conn)
