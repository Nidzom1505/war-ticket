"""
TicketWar API – Configuration from environment variables.
"""

import os


class Config:
    """Reads all settings from .env / environment."""

    # -- PostgreSQL --
    POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_USER     = os.getenv("POSTGRES_USER", "ticketwar")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "ticketwar_secret")
    POSTGRES_DB       = os.getenv("POSTGRES_DB", "ticketwar_db")

    # -- Redis --
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    # -- JWT --
    JWT_SECRET_KEY      = os.getenv("JWT_SECRET_KEY", "change-me")
    JWT_ALGORITHM       = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
