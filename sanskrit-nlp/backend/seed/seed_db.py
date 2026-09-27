"""
Idempotent seeding script.

Loads backend/seed/vocabulary.json and upserts every entry into the
`words` collection by `lemma`, then seeds the `rules` collection from the
rule definitions in modules/rules.py. Safe to run multiple times: existing
lemmas are replaced in place, nothing is duplicated.

Usage:
    python -m seed.seed_db
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import close_client, ensure_indexes, get_db  # noqa: E402
from modules.rules import RULES  # noqa: E402

VOCAB_PATH = Path(__file__).resolve().parent / "vocabulary.json"


async def seed_words() -> int:
    """Upsert every vocabulary entry by lemma. Returns the number seeded."""
    db = get_db()
    with open(VOCAB_PATH, encoding="utf-8") as f:
        words = json.load(f)

    count = 0
    for word in words:
        await db.words.update_one(
            {"lemma": word["lemma"]},
            {"$set": word},
            upsert=True,
        )
        count += 1
    return count


async def seed_rules() -> int:
    """Upsert the rule catalog (id, name, description, active) for display."""
    db = get_db()
    count = 0
    for rule in RULES:
        await db.rules.update_one(
            {"id": rule.id},
            {"$set": {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "active": True,
            }},
            upsert=True,
        )
        count += 1
    return count


async def main() -> None:
    """Run indexing then seed words and rules, printing a short summary."""
    await ensure_indexes()
    n_words = await seed_words()
    n_rules = await seed_rules()
    print(f"Seeded {n_words} vocabulary entries and {n_rules} rules.")
    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
