"""
MongoDB connection management (Motor async driver).

Provides a single lazily-created `AsyncIOMotorClient` for the whole
process, a `get_db()` accessor used throughout the backend, and an
`ensure_indexes()` helper that creates the indexes described in the
project spec (unique lemma, multikey forms.form, english_aliases).
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    """Return the process-wide Motor client, creating it on first use."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return the configured database handle, creating it on first use."""
    global _db
    if _db is None:
        _db = get_client()[settings.db_name]
    return _db


async def ensure_indexes() -> None:
    """Create all indexes required by the data model. Safe to call repeatedly."""
    db = get_db()
    await db.words.create_index("lemma", unique=True)
    await db.words.create_index("forms.form")
    await db.words.create_index("english_aliases")
    await db.words.create_index("category")
    await db.rules.create_index("id", unique=True)
    await db.generation_logs.create_index("timestamp")


async def close_client() -> None:
    """Close the Motor client (used on app shutdown and in test teardown)."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
