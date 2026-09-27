"""
Shared pytest fixtures.

Forces TESTING=true (so config.py points at a `_test`-suffixed database)
before any backend module is imported, seeds that database with the real
seed vocabulary and rules before the test session runs, and drops it
afterwards so tests never touch the development/production database.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "sanskrit_nlp")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from db import close_client, ensure_indexes, get_client, get_db  # noqa: E402

VOCAB_PATH = BACKEND_DIR / "seed" / "vocabulary.json"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seeded_test_db():
    """Seed the test database once per test session, then drop it."""
    db = get_db()
    await ensure_indexes()

    with open(VOCAB_PATH, encoding="utf-8") as f:
        words = json.load(f)
    for word in words:
        await db.words.update_one({"lemma": word["lemma"]}, {"$set": word}, upsert=True)

    yield db

    client = get_client()
    await client.drop_database(db.name)
    await close_client()


@pytest.fixture
def anyio_backend():
    return "asyncio"
