"""
TicketWar API – Shared infrastructure singletons.

Provides:
    get_db_connection()  – checkout a psycopg2 connection from the pool
    release_db(conn)     – return it
    redis_client         – ready-to-use redis.Redis instance
    init_extensions()    – call once at app startup
    close_extensions()   – call on teardown
"""

import psycopg2
from psycopg2 import pool
import redis

from app.config import Config

# ---------------------------------------------------------------------------
#  Module-level singletons (initialised lazily via init_extensions)
# ---------------------------------------------------------------------------

_db_pool: pool.ThreadedConnectionPool | None = None
redis_client: redis.Redis | None = None


# ---------------------------------------------------------------------------
#  Public helpers
# ---------------------------------------------------------------------------

def init_extensions() -> None:
    """Create the DB connection pool and Redis client."""
    global _db_pool, redis_client

    _db_pool = pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT,
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        dbname=Config.POSTGRES_DB,
    )

    redis_client = redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=0,
        decode_responses=True,          # always return str, not bytes
    )


def get_db_connection():
    """Checkout a connection from the pool."""
    if _db_pool is None:
        raise RuntimeError("Extensions not initialised – call init_extensions() first.")
    return _db_pool.getconn()


def release_db(conn) -> None:
    """Return a connection back to the pool."""
    if _db_pool is not None and conn is not None:
        _db_pool.putconn(conn)


def close_extensions() -> None:
    """Gracefully shut down pool & Redis."""
    global _db_pool, redis_client
    if _db_pool:
        _db_pool.closeall()
        _db_pool = None
    if redis_client:
        redis_client.close()
        redis_client = None
