"""
TicketWar Worker – Asynchronous Order Processor Daemon

This long-running process:
  1. Blocks on Redis list `order_queue`  (BLPOP).
  2. For each order payload it:
     a. Generates sequential seat numbers.
     b. Acquires a Redis distributed lock per seat (NX PX 10000).
     c. Opens an ACID transaction in PostgreSQL:
        - INSERT into `orders`           (payment_status = 'paid')
        - INSERT into `tickets`          (one row per seat)
        - UPDATE `ticket_categories`     (decrement available_quota)
        - INSERT into `audit_logs`
     d. Releases the distributed locks.
     e. Sets `order_status:{invoice}` = "completed"  (TTL 10 min).
  3. On any failure: rolls back DB, restores Redis quota, logs the error.

Usage:
    python worker.py
"""

import json
import logging
import os
import signal
import sys
import time
import uuid

import psycopg2
from psycopg2 import pool
import redis

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ticketwar.worker")

# ---------------------------------------------------------------------------
#  Configuration (from environment / .env)
# ---------------------------------------------------------------------------

POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_USER     = os.getenv("POSTGRES_USER", "ticketwar")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ticketwar_secret")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "ticketwar_db")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

QUEUE_KEY          = "order_queue"
BLPOP_TIMEOUT      = 5          # seconds; 0 = block forever
LOCK_TTL_MS        = 10_000     # distributed lock duration
ORDER_STATUS_TTL   = 600        # 10 minutes

# ---------------------------------------------------------------------------
#  Globals
# ---------------------------------------------------------------------------

_db_pool: pool.ThreadedConnectionPool | None = None
_redis: redis.Redis | None = None
_running: bool = True


# ---------------------------------------------------------------------------
#  Bootstrap
# ---------------------------------------------------------------------------

def connect_with_retry() -> None:
    """Initialise DB pool and Redis client, retrying until both are up."""
    global _db_pool, _redis

    for attempt in range(1, 31):              # up to ~30 s
        try:
            if _db_pool is None:
                _db_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=5,
                    host=POSTGRES_HOST,
                    port=POSTGRES_PORT,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD,
                    dbname=POSTGRES_DB,
                )
                logger.info("✅ PostgreSQL pool ready")

            if _redis is None:
                _redis = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=0,
                    decode_responses=True,
                )
                _redis.ping()
                logger.info("✅ Redis connected")

            return                              # both OK

        except Exception as exc:
            logger.warning(
                "⏳ Connection attempt %d/30 failed: %s – retrying in 1 s …",
                attempt, exc,
            )
            time.sleep(1)

    logger.critical("❌ Could not connect after 30 attempts – exiting")
    sys.exit(1)


# ---------------------------------------------------------------------------
#  Seat Number Generation
# ---------------------------------------------------------------------------

def _generate_seat_numbers(category_name: str, category_id: int, quantity: int) -> list[str]:
    """Generate `quantity` sequential seat numbers using a Redis counter.

    Pattern:  CAT1-001, CAT1-002 …  or  VIP-001, VIP-002 …
    The counter `seat_counter:{category_id}` is atomically incremented.
    """
    prefix = category_name.replace(" ", "").upper()
    seats: list[str] = []
    for _ in range(quantity):
        seq = _redis.incr(f"seat_counter:{category_id}")
        seats.append(f"{prefix}-{seq:03d}")
    return seats


# ---------------------------------------------------------------------------
#  Distributed Lock Helpers
# ---------------------------------------------------------------------------

def _acquire_seat_locks(seats: list[str]) -> dict[str, str]:
    """Acquire a Redis distributed lock for each seat.

    Returns a mapping {seat_number: lock_token} for acquired locks.
    Raises RuntimeError if any lock cannot be acquired.
    """
    acquired: dict[str, str] = {}
    try:
        for seat in seats:
            token = str(uuid.uuid4())
            key   = f"lock:seat:{seat}"
            ok    = _redis.set(key, token, nx=True, px=LOCK_TTL_MS)
            if not ok:
                raise RuntimeError(f"Seat {seat} already locked")
            acquired[seat] = token
    except Exception:
        # Release anything we already acquired
        _release_seat_locks(acquired)
        raise
    return acquired


def _release_seat_locks(locks: dict[str, str]) -> None:
    """Release distributed locks, only if we still own them (CAS via Lua)."""
    # Lua script: delete key only if value matches our token
    lua = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """
    for seat, token in locks.items():
        try:
            _redis.eval(lua, 1, f"lock:seat:{seat}", token)
        except Exception as exc:
            logger.warning("⚠️  Failed to release lock for %s: %s", seat, exc)


# ---------------------------------------------------------------------------
#  Order Processing (core transaction)
# ---------------------------------------------------------------------------

def process_order(payload: dict) -> None:
    """Process a single order payload from the queue.

    Steps:
        1. Fetch category metadata (price, name).
        2. Generate seat numbers.
        3. Acquire distributed seat locks.
        4. ACID transaction in PostgreSQL.
        5. Update Redis order status → "completed".
        6. Release locks.

    On failure → rollback DB, restore Redis quota, mark status "failed".
    """
    invoice_number = payload["invoice_number"]
    user_id        = payload["user_id"]
    category_id    = payload["category_id"]
    quantity       = payload["quantity"]
    ip_address     = payload.get("ip_address", "unknown")

    conn  = None
    locks = {}

    try:
        # -- mark processing --
        _redis.set(f"order_status:{invoice_number}", "processing", ex=ORDER_STATUS_TTL)

        conn = _db_pool.getconn()
        cur  = conn.cursor()

        # 1. Fetch category info
        cur.execute(
            "SELECT category_name, price FROM ticket_categories WHERE id = %s",
            (category_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Category {category_id} not found in DB")

        category_name, price = row[0], row[1]
        total_amount = float(price) * quantity

        # 2. Generate seats
        seats = _generate_seat_numbers(category_name, category_id, quantity)

        # 3. Acquire distributed locks
        locks = _acquire_seat_locks(seats)

        # 4. ACID transaction -----------------------------------------------
        # 4a. Insert order
        cur.execute(
            """
            INSERT INTO orders
                (invoice_number, user_id, category_id, quantity, total_amount, payment_status)
            VALUES (%s, %s, %s, %s, %s, 'paid')
            RETURNING id
            """,
            (invoice_number, user_id, category_id, quantity, total_amount),
        )
        order_id = cur.fetchone()[0]

        # 4b. Insert tickets (one per seat)
        for seat in seats:
            ticket_code = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO tickets (order_id, seat_number, ticket_code)
                VALUES (%s, %s, %s)
                """,
                (order_id, seat, ticket_code),
            )

        # 4c. Decrement available_quota in DB
        cur.execute(
            """
            UPDATE ticket_categories
               SET available_quota = available_quota - %s
             WHERE id = %s AND available_quota >= %s
            RETURNING available_quota
            """,
            (quantity, category_id, quantity),
        )
        updated = cur.fetchone()
        if updated is None:
            raise RuntimeError("DB quota insufficient – potential oversell")

        # 4d. Audit log
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, table_name, record_id, ip_address)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, "order_paid", "orders", order_id, ip_address),
        )

        # 4e. Commit
        conn.commit()
        # -------------------------------------------------------------------

        # 5. Mark completed in Redis
        _redis.set(f"order_status:{invoice_number}", "completed", ex=ORDER_STATUS_TTL)

        logger.info(
            "✅ Order %s processed – %d ticket(s) → seats %s",
            invoice_number, quantity, ", ".join(seats),
        )

    except Exception as exc:
        logger.error("❌ Order %s FAILED: %s", invoice_number, exc)

        # Rollback DB
        if conn:
            conn.rollback()

        # Restore Redis quota
        try:
            _redis.incrby(f"quota:{category_id}", quantity)
            logger.info("↩️  Restored %d quota for category %d", quantity, category_id)
        except Exception as redis_exc:
            logger.error("❌ Could not restore Redis quota: %s", redis_exc)

        # Mark failed
        try:
            _redis.set(f"order_status:{invoice_number}", "failed", ex=ORDER_STATUS_TTL)
        except Exception:
            pass

    finally:
        # 6. Release seat locks
        if locks:
            _release_seat_locks(locks)

        # Return connection to pool
        if conn:
            _db_pool.putconn(conn)


# ---------------------------------------------------------------------------
#  Main Loop
# ---------------------------------------------------------------------------

def main_loop() -> None:
    """Block on the Redis queue and process orders one-by-one."""
    logger.info("🚀 Worker listening on queue '%s' …", QUEUE_KEY)

    while _running:
        try:
            result = _redis.blpop(QUEUE_KEY, timeout=BLPOP_TIMEOUT)

            if result is None:
                continue  # timeout – loop back and check _running

            _key, raw = result

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.error("⚠️  Invalid JSON in queue: %s – %s", raw, exc)
                continue

            # Validate required fields
            required = ("invoice_number", "user_id", "category_id", "quantity")
            if not all(k in payload for k in required):
                logger.error("⚠️  Incomplete payload, skipping: %s", payload)
                continue

            process_order(payload)

        except redis.ConnectionError as exc:
            logger.error("🔌 Redis connection lost: %s – reconnecting in 3 s …", exc)
            time.sleep(3)
            try:
                _redis.ping()
            except Exception:
                pass  # will retry on next loop

        except Exception as exc:
            logger.error("💥 Unexpected error in main loop: %s", exc, exc_info=True)
            time.sleep(1)


# ---------------------------------------------------------------------------
#  Graceful Shutdown
# ---------------------------------------------------------------------------

def _shutdown(signum, _frame):
    global _running
    logger.info("🛑 Received signal %s – shutting down …", signum)
    _running = False


# ---------------------------------------------------------------------------
#  Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("=" * 52)
    logger.info("  TicketWar Worker starting up")
    logger.info("=" * 52)

    connect_with_retry()
    main_loop()

    # Cleanup
    if _db_pool:
        _db_pool.closeall()
    if _redis:
        _redis.close()

    logger.info("👋 Worker stopped")
