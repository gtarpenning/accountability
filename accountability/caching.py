"""
Caching decorator that stores function results in SQLite.
Usage:
    @cache
    def expensive_function(x, y):
        # Result will be cached based on x, y arguments
        return x + y

    @cache(timeout=3600)  # Cache expires after 1 hour
    def get_stock_price(symbol):
        # API calls are perfect for caching
        return api.get_price(symbol)
"""

import json
import sqlite3
import time
import functools
import hashlib
from typing import Any, Callable
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetryableDatabase:
    """Database connection with retry logic for handling concurrent access."""

    MAX_RETRIES = 5
    RETRY_DELAY = 0.1  # seconds

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        for attempt in range(self.MAX_RETRIES):
            try:
                self.conn = sqlite3.connect(self.db_path, timeout=20.0)
                self.conn.execute("PRAGMA busy_timeout = 10000")
                return self.conn
            except sqlite3.OperationalError as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(
                        "Failed to connect to database after %d attempts: %s",
                        self.MAX_RETRIES,
                        e,
                    )
                    raise
                logger.warning(
                    "Database connection attempt %d failed, retrying...",
                    attempt + 1,
                )
                time.sleep(self.RETRY_DELAY * (2**attempt))
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()


def get_table_name(func_name: str) -> str:
    """Generate a safe table name from function name."""
    # Create a deterministic but safe table name
    return f"cache_{hashlib.md5(func_name.encode()).hexdigest()}"


def create_cache_table(conn: sqlite3.Connection, table_name: str) -> None:
    """Create a cache table for a specific function if it doesn't exist."""
    cur = conn.cursor()
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            args_hash TEXT PRIMARY KEY,
            args_pickle BLOB,
            result_pickle BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            timeout_at TIMESTAMP,
            last_accessed TIMESTAMP
        )
    """
    )
    conn.commit()


def _serialize_for_cache(obj: Any) -> Any:
    """Helper function to serialize objects for caching."""
    if isinstance(obj, datetime):
        return {"__datetime__": obj.isoformat()}
    return obj


def _deserialize_from_cache(obj: Any) -> Any:
    """Helper function to deserialize objects from cache."""
    if isinstance(obj, dict) and "__datetime__" in obj:
        return datetime.fromisoformat(obj["__datetime__"])
    return obj


def cache_result(table_name: str, ttl_seconds: int = 3600):
    """
    Decorator that caches function results in SQLite with retry logic.

    Args:
        table_name: Name of the table to store cache results
        ttl_seconds: Time to live for cached results in seconds
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            try:
                with RetryableDatabase("cache.db") as conn:
                    conn.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            key TEXT PRIMARY KEY,
                            value TEXT,
                            timestamp FLOAT
                        )
                    """
                    )

                    cursor = conn.execute(
                        f"SELECT value, timestamp FROM {table_name} WHERE key = ?",
                        (cache_key,),
                    )
                    result = cursor.fetchone()

                    current_time = time.time()
                    if result and (current_time - result[1]) < ttl_seconds:
                        return json.loads(
                            result[0], object_hook=_deserialize_from_cache
                        )

                    # If no valid cache, compute new value
                    new_value = func(*args, **kwargs)

                    # Store in cache with retry logic
                    for attempt in range(RetryableDatabase.MAX_RETRIES):
                        try:
                            serialized_value = json.dumps(
                                new_value, default=_serialize_for_cache
                            )
                            conn.execute(
                                f"""
                                INSERT OR REPLACE INTO {table_name}
                                (key, value, timestamp) VALUES (?, ?, ?)
                                """,
                                (cache_key, serialized_value, current_time),
                            )
                            conn.commit()
                            break
                        except sqlite3.OperationalError as e:
                            if attempt == RetryableDatabase.MAX_RETRIES - 1:
                                logger.error(
                                    "Failed to write to cache after %d attempts: %s",
                                    RetryableDatabase.MAX_RETRIES,
                                    e,
                                )
                                raise
                            logger.warning(
                                "Cache write attempt %d failed, retrying...",
                                attempt + 1,
                            )
                            time.sleep(RetryableDatabase.RETRY_DELAY * (2**attempt))

                    return new_value

            except sqlite3.Error as e:
                logger.error("Cache error: %s", e)
                return func(*args, **kwargs)

        return wrapper

    return decorator
